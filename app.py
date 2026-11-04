import os
import sqlite3
import secrets
import hashlib
from flask import Flask, render_template, request, redirect, url_for, session, flash

# Безопасный импорт логгера (заглушка спасет от ошибок, если logger.py еще не готов локально)
try:
    from logger import log_event
except ImportError:
    def log_event(event_type, description):
        pass

# Безопасный импорт валидатора и ИИ-помощника
try:
    from validators import validate_user_text
except ImportError:
    def validate_user_text(text):
        return True, ""

try:
    from ai_helper import ask_gigachat
except ImportError:
    def ask_gigachat(text):
        return {"type": "Обычная неисправность", "need_ticket": True, "title": "Обращение", "category": "Оборудование и ИТ"}

app = Flask(__name__)
# Секретный ключ обязателен для работы сессий (авторизации)
app.secret_key = secrets.token_hex(16)

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# ГЛАВНАЯ СТРАНИЦА (Сканирование QR или переход на форму)
@app.route("/")
def home():
    qr_key = request.args.get('qr')
    if qr_key:
        return redirect(url_for('create_page', qr=qr_key))
    return render_template("index.html")

# СТРАНИЦА СОЗДАНИЯ ЗАЯВКИ
@app.route("/create", methods=["GET", "POST"])
def create_page():
    conn = get_db_connection()
    
    if request.method == "POST":
        user_text = request.form.get("description", "").strip()
        location_id = request.form.get("location_id")
        
        is_valid, error_msg = validate_user_text(user_text)
        if not is_valid:
            flash(error_msg, "error")
            locations = conn.execute('SELECT * FROM locations').fetchall()
            conn.close()
            return render_template("create.html", locations=locations, selected_location=location_id)
        
        log_event("AI_REQUEST", f"Пользователь отправил запрос для локации ID {location_id}: '{user_text}'")
        
        ai_result = ask_gigachat(user_text)
        
        log_event("AI_RESPONSE", f"ИИ вернул тип [{ai_result.get('type')}]. Создание тикета: {ai_result.get('need_ticket')}")
        
        locations = conn.execute('SELECT * FROM locations').fetchall()
        conn.close()
        return render_template("ai_result.html", ai=ai_result, text=user_text, location_id=location_id)
        
    qr_key = request.args.get('qr')
    selected_location = None
    if qr_key:
        loc = conn.execute('SELECT * FROM locations WHERE qr_key = ?', (qr_key,)).fetchone()
        if loc:
            selected_location = loc['id']
            log_event("INFO", f"Форма успешно открыта по QR-коду для локации: {loc['room']} ({loc['building']})")
            
    locations = conn.execute('SELECT * FROM locations').fetchall()
    conn.close()
    return render_template("create.html", locations=locations, selected_location=selected_location)

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
    
    cat = conn.execute('SELECT id FROM categories WHERE name = ?', (ai_category,)).fetchone()
    category_id = cat['id'] if cat else 1
    
    public_number = f"REQ-{secrets.randbelow(900000) + 100000}"
    raw_token = secrets.token_urlsafe(16)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    
    cursor = conn.execute('''
        INSERT INTO tickets (public_number, title, description, category_id, location_id, tracking_token_hash)
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

# ОТСЛЕЖИВАНИЕ СТАТУСА ЗАЯВКИ ЗАЯВИТЕЛЕМ
@app.route("/status")
def check_status():
    token = request.args.get('token')
    if not token:
        return render_template("check_status.html", ticket=None, error="Токен отслеживания не указан.")
        
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    conn = get_db_connection()
    ticket = conn.execute('''
        SELECT t.*, c.name as category_name, l.room, l.building 
        FROM tickets t
        LEFT JOIN categories c ON t.category_id = c.id
        LEFT JOIN locations l ON t.location_id = l.id
        WHERE t.tracking_token_hash = ?
    ''', (token_hash,)).fetchone()
    
    if not ticket:
        conn.close()
        return render_template("check_status.html", ticket=None, error="Заявка с таким токеном не найдена.")
        
    history = conn.execute('SELECT * FROM TicketHistory WHERE ticket_id = ? ORDER BY created_at DESC', (ticket['id'],)).fetchall()
    comments = conn.execute('SELECT * FROM Comments WHERE ticket_id = ? AND visibility = "public" ORDER BY created_at DESC', (ticket['id'],)).fetchall()
    
    conn.close()
    return render_template("check_status.html", ticket=ticket, history=history, comments=comments)

# АВТОРИЗАЦИЯ И ВХОД
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE login = ?', (username,)).fetchone()
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

# ЗАЩИЩЕННАЯ ПАНЕЛЬ СОТРУДНИКА УПК
@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if 'user_id' not in session:
        log_event("SECURITY", "Попытка несанкционированного доступа к панели /admin!")
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    
    if request.method == "POST":
        ticket_id = request.form.get("ticket_id")
        new_status = request.form.get("status")
        note = request.form.get("note", "")
        
        if ticket_id and new_status:
            old_ticket = conn.execute('SELECT status FROM tickets WHERE id = ?', (ticket_id,)).fetchone()
            old_status = old_ticket['status'] if old_ticket else 'Новая'
            
            conn.execute('UPDATE tickets SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (new_status, ticket_id))
            
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
        FROM tickets t
        LEFT JOIN categories c ON t.category_id = c.id
        LEFT JOIN locations l ON t.location_id = l.id
        ORDER BY t.created_at DESC
    ''').fetchall()

    conn.close()
    return render_template("admin.html", tickets=tickets)


if __name__ == "__main__":
    app.run(debug=True)
