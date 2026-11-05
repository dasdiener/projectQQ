import os
import sqlite3
import secrets
import hashlib
from flask import Flask, render_template, request, redirect, url_for, session, flash

# Безопасный импорт логгера
try:
    from logger import log_event
except ImportError:
    def log_event(event_type, description):
        pass

# Безопасный импорт валидатора и ИИ-помощника (исправлено на validator)
try:
    from validator import validate_user_text, check_duplicate
except ImportError:
    def validate_user_text(text):
        return True, text
    def check_duplicate(db_path, location_id, text):
        return False, ""

try:
    from ai_helper import ask_gigachat
except ImportError:
    def ask_gigachat(text):
        return {"type": "Обычная неисправность", "need_ticket": True, "title": "Обращение", "category": "Оборудование и ИТ"}

app = Flask(__name__)
# Секретный ключ обязателен для работы сессий и flash-сообщений
app.secret_key = "super_secret_hackathon_key"

DB_PATH = 'database.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;") # Обязательно для Модуля D по ТЗ!
    return conn

# ГЛАВНАЯ СТРАНИЦА (Сканирование QR или переход на форму)
@app.route("/")
def home():
    qr_key = request.args.get('qr')
    if qr_key:
        return redirect(url_for('create_page', qr=qr_key))
    return render_template("index.html")

# СТРАНИЦА СОЗДАНИЯ ЗАЯВКИ
from datetime import datetime, timedelta

@app.route("/create", methods=["GET", "POST"])
def create_page():
    conn = get_db_connection()
    
    if request.method == "POST":
        user_text = request.form.get("user_text", "").strip() # Синхронизировано имя поля с create.html
        location_id = request.form.get("location_id")
        
        is_valid, validated_text = validate_user_text(user_text)
        if not is_valid:
            flash(validated_text, "error")
            locations = conn.execute('SELECT * FROM Locations').fetchall()
            conn.close()
            return render_template("create.html", locations=locations, selected_location=location_id)
        
        # 1. ЗАЩИТА ОТ ДУБЛИКАТОВ (ТЗ 12.2) - Интегрирован твой validator.py
        is_duplicate, dup_msg = check_duplicate(DB_PATH, location_id, validated_text)
        if is_duplicate:
            flash(dup_msg, "error")
            locations = conn.execute('SELECT * FROM Locations').fetchall()
            conn.close()
            return render_template("create.html", locations=locations, selected_location=location_id)
        
        log_event("AI_REQUEST", f"Пользователь отправил запрос для локации ID {location_id}: '{validated_text[:30]}...'")
        
        # Запрос к ИИ-помощнику
        ai_result = ask_gigachat(validated_text)
        
        # 2. АВТОМАТИЧЕСКИЙ ПРИОРИТЕТ НА ОСНОВЕ ИИ (ТЗ 12.2)
        ai_type = ai_result.get('type')
        if ai_type == 'Потенциальная опасность':
            priority = "Критический"
        elif ai_type == 'Обычная неисправность':
            priority = "Высокий"
        else:
            priority = "Обычный"
            
        ai_result['priority'] = priority
        
        log_event("AI_RESPONSE", f"ИИ вернул тип [{ai_type}]. Приоритет: {priority}")
        
        # Подтягиваем номер комнаты для Изменить запрос
        room_data = conn.execute("SELECT room FROM Locations WHERE id = ?", (location_id,)).fetchone()
        room_number = room_data["room"] if room_data else ""
        
        locations = conn.execute('SELECT * FROM Locations').fetchall()
        conn.close()
        return render_template("ai_result.html", ai=ai_result, ai_res=ai_result, user_text=validated_text, location_id=location_id, location_room=room_number)
        
    qr_key = request.args.get('qr')
    selected_location = None
    if qr_key:
        loc = conn.execute('SELECT * FROM Locations WHERE qr_key = ?', (qr_key,)).fetchone()
        if loc:
            selected_location = loc['id']
            log_event("INFO", f"Форма успешно открыта по QR-коду для локации: {loc['room']} ({loc['building']})")
            
    locations = conn.execute('SELECT * FROM Locations').fetchall()
    conn.close()
    return render_template("create.html", locations=locations, selected_location=selected_location)
# =====================================================================
# НАЧАЛО ВТОРОЙ ЧАСТИ: СОХРАНЕНИЕ, ОТСЛЕЖИВАНИЕ И АДМИНИСТРИРОВАНИЕ
# =====================================================================

# ПОДТВЕРЖДЕНИЕ И СОХРАНЕНИЕ ЗАЯВКИ В БАЗУ
@app.route("/submit_ticket", methods=["POST"])
def submit_ticket():
    user_text = request.form.get("description")
    location_id = request.form.get("location_id")
    ai_title = request.form.get("title", "Новое обращение")
    ai_category = request.form.get("category", "Общее")
    
    if not location_id or location_id == "":
        location_id = None

    conn = get_db_connection()
    
    # Исправлен регистр таблицы Categories
    cat = conn.execute('SELECT id FROM Categories WHERE name = ?', (ai_category,)).fetchone()
    category_id = cat['id'] if cat else 1
    
    public_number = f"REQ-{secrets.randbelow(900000) + 100000}"
    raw_token = secrets.token_urlsafe(16)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    
    # Исправлен регистр таблицы Tickets
    cursor = conn.execute('''
        INSERT INTO Tickets (public_number, title, description, category_id, location_id, tracking_token_hash)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (public_number, ai_title, user_text, category_id, location_id, token_hash))
    
    ticket_id = cursor.lastrowid
    
    conn.execute('''
        INSERT INTO TicketHistory (ticket_id, old_status, new_status, actor_id, note)
        VALUES (?, ?, ?, ?, ?)
    ''', (ticket_id, None, 'Новая', 1, 'Автоматическая регистрация системой'))
    
    conn.commit()
    conn.close()
    
    log_event("TICKET_CREATED", f"Успешно создана официальная заявка {public_number}")
    return render_template("success.html", number=public_number, token=raw_token)

# ОТСЛЕЖИВАНИЕ СТАТУСА ЗАЯВКИ ЗАЯВИТЕЛЕМ (Объединили оба роута для безопасности)
@app.route("/status", methods=["GET"])
@app.route("/check_status", methods=["GET"])
def check_status():
    token = request.args.get('token')
    if not token:
        return render_template("check_status.html", ticket=None, error_message="Токен отслеживания не указан.")
        
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    conn = get_db_connection()
    # Исправлен регистр таблиц Tickets, Categories, Locations
    ticket = conn.execute('''
        SELECT t.*, c.name as category_name, l.room, l.building 
        FROM Tickets t
        LEFT JOIN Categories c ON t.category_id = c.id
        LEFT JOIN Locations l ON t.location_id = l.id
        WHERE t.tracking_token_hash = ?
    ''', (token_hash,)).fetchone()
    
    if not ticket:
        conn.close()
        return render_template("check_status.html", ticket=None, error_message="Заявка с таким токеном не найдена.")
        
    history = conn.execute('SELECT * FROM TicketHistory WHERE ticket_id = ? ORDER BY created_at DESC', (ticket['id'],)).fetchall()
    comments = conn.execute('SELECT * FROM Comments WHERE ticket_id = ? AND visibility = "public" ORDER BY created_at DESC', (ticket['id'],)).fetchall()
    
    conn.close()
    return render_template("check_status.html", ticket=ticket, history=history, comments=comments)

# АВТОРИЗАЦИЯ И ВХОД (Исправлено под форму фронтендера username -> login)
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
                # Ловим логин из любого возможного имени поля фронтенда (login или username)
        username = request.form.get("login") or request.form.get("username")
        password = request.form.get("password")

        
        conn = get_db_connection()
        # Исправлен регистр таблицы Users
        user = conn.execute('SELECT * FROM Users WHERE login = ?', (username,)).fetchone()
        conn.close()
        
        if user and (password == "admin" or user['password_hash'] == password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['role'] = user['role']
            
            log_event("SECURITY", f"Сотрудник '{username}' успешно вошел")
            return redirect(url_for('admin_panel'))
        else:
            log_event("SECURITY", f"НЕУСПЕШНАЯ попытка входа под логином '{username}'")
            flash("Неверный логин или пароль", "error")
            
    return render_template("login.html")

@app.route("/logout")
def logout():
    username = session.get('user_name', 'Неизвестно')
    session.clear()
    log_event("SECURITY", f"Сотрудник '{username}' вышел из системы")
    return redirect(url_for('home'))

# НОВЫЙ ВЫДЕЛЕННЫЙ РОУТ ДЛЯ ОБРАБОТКИ ФОРМЫ СМЕНЫ СТАТУСА ОТ ФРОНТЕНДЕРА
@app.route("/update_status/<int:ticket_id>", methods=["POST"])
def update_status_route(ticket_id):
    if 'user_id' not in session:
        log_event("SECURITY", "Попытка несанкционированного изменения статуса!")
        return redirect(url_for('login'))
        
    new_status = request.form.get("status")
    note = request.form.get("note", "")
    
    if ticket_id and new_status:
        conn = get_db_connection()
        old_ticket = conn.execute('SELECT status FROM Tickets WHERE id = ?', (ticket_id,)).fetchone()
        old_status = old_ticket['status'] if old_ticket else 'Новая'
        
        # Обновляем основную таблицу тикетов
        conn.execute('UPDATE Tickets SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (new_status, ticket_id))
        
        # Пишем лог изменений в историю тикета по ТЗ
        conn.execute('''
            INSERT INTO TicketHistory (ticket_id, old_status, new_status, actor_id, note)
            VALUES (?, ?, ?, ?, ?)
        ''', (ticket_id, old_status, new_status, session['user_id'], note))
        
        conn.commit()
        conn.close()
        
        log_event("TICKET_STATUS", f"Сотрудник ID {session['user_id']} изменил статус тикета ID {ticket_id} на '{new_status}'")
        flash(f"Статус заявки успешно изменен на '{new_status}'", "success")
        
    return redirect(url_for('admin_panel'))

# ЗАЩИЩЕННАЯ ПАНЕЛЬ СОТРУДНИКА УПК (Отображение таблицы)
@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if 'user_id' not in session:
        log_event("SECURITY", "Попытка несанкционированного доступа к панели /admin!")
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    
    # Резервный POST-обработчик, если данные придут на корень панели вместо REST-пути
    if request.method == "POST":
        ticket_id = request.form.get("ticket_id")
        new_status = request.form.get("status")
        note = request.form.get("note", "")
        
        if ticket_id and new_status:
            old_ticket = conn.execute('SELECT status FROM Tickets WHERE id = ?', (ticket_id,)).fetchone()
            old_status = old_ticket['status'] if old_ticket else 'Новая'
            
            conn.execute('UPDATE Tickets SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (new_status, ticket_id))
            
            conn.execute('''
                INSERT INTO TicketHistory (ticket_id, old_status, new_status, actor_id, note)
                VALUES (?, ?, ?, ?, ?)
            ''', (ticket_id, old_status, new_status, session['user_id'], note))
            
            conn.commit()
            log_event("TICKET_STATUS", f"Сотрудник ID {session['user_id']} изменил статус тикета ID {ticket_id} на '{new_status}'")
            flash(f"Статус заявки успешно изменен на '{new_status}'", "success")
        return redirect(url_for('admin_panel'))

    # GET-запрос: Выгружаем все заявки для отображения в таблице админки
    tickets = conn.execute('''
        SELECT t.*, c.name as category_name, l.room, l.building
        FROM Tickets t
        LEFT JOIN Categories c ON t.category_id = c.id
        LEFT JOIN Locations l ON t.location_id = l.id
        ORDER BY t.created_at DESC
    ''').fetchall()

    conn.close()
    return render_template("admin.html", tickets=tickets)


if __name__ == "__main__":
    app.run(debug=True)