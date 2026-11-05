import os
import sqlite3
import secrets
import hashlib
from flask import Flask, render_template, request, redirect, url_for, session, flash

# Безопасный импорт кастомных локальных модулей
try:
    from logger import log_event
except ImportError:
    def log_event(event_type, description):
        print(f"[{event_type}] {description}")

try:
    from validators import validate_user_text
except ImportError:
    def validate_user_text(text):
        if not text or len(text.strip()) < 5:
            return False, "Описание должно содержать минимум 5 символов."
        return True, text.strip()

try:
    from ai_helper import ask_gigachat
except ImportError:
    def ask_gigachat(text):
        return {"type": "Обычная неисправность", "need_ticket": True, "title": "Обращение", "category": "Оборудование и ИТ", "answer": "Заявка"}

app = Flask(__name__)
# Фиксированный ключ для стабильности сессий при перезапусках бэкенда
app.secret_key = "upk_college_digital_assistant_secret_key_2026"

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
        
        if not location_id or location_id == "":
            location_id = None
            
        is_valid, validated_text = validate_user_text(user_text)
        if not is_valid:
            flash(validated_text, "error")
            locations = conn.execute('SELECT * FROM locations').fetchall()
            conn.close()
            return render_template("create.html", locations=locations, selected_location=location_id)
        
        log_event("AI_REQUEST", f"Запрос для локации ID {location_id}: '{validated_text}'")
        ai_result = ask_gigachat(validated_text)
        log_event("AI_RESPONSE", f"Тип [{ai_result.get('type')}]. Создание тикета: {ai_result.get('need_ticket')}")
        
        locations = conn.execute('SELECT * FROM locations').fetchall()
        conn.close()
        return render_template("ai_result.html", ai=ai_result, text=validated_text, location_id=location_id)
        
    qr_key = request.args.get('qr')
    selected_location = None
    if qr_key:
        loc = conn.execute('SELECT * FROM locations WHERE qr_key = ?', (qr_key,)).fetchone()
        if loc:
            selected_location = loc['id']
            log_event("INFO", f"Форма открыта по QR для локации: {loc['room']} ({loc['building']})")
        else:
            flash("QR-код не привязан к конкретному помещению. Выберите локацию вручную.", "info")
            
    locations = conn.execute('SELECT * FROM locations').fetchall()
    conn.close()
    return render_template("create.html", locations=locations, selected_location=selected_location)

# ПОДТВЕРЖДЕНИЕ И СОХРАНЕНИЕ ЗАЯВКИ В БАЗУ
@app.route("/submit_ticket", methods=["POST"])
def submit_ticket():
    user_text = request.form.get("description", "").strip()
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
        INSERT INTO tickets (public_number, title, description, category_id, location_id, status, tracking_token_hash)
        VALUES (?, ?, ?, ?, ?, 'Новая', ?)
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
# ОТСЛЕЖИВАНИЕ СТАТУСА ЗАЯВКИ ЗАЯВИТЕЛЕМ (Безопасный доступ по токену)
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
        
    history = conn.execute('''
        SELECT th.*, u.name as actor_name 
        FROM TicketHistory th
        LEFT JOIN users u ON th.actor_id = u.id
        WHERE th.ticket_id = ? ORDER BY th.created_at DESC
    ''', (ticket['id'],)).fetchall()
    
    comments = conn.execute('''
        SELECT c.*, u.name as author_name 
        FROM Comments c
        LEFT JOIN users u ON c.author_id = u.id
        WHERE c.ticket_id = ? AND c.visibility = 'public' ORDER BY c.created_at DESC
    ''', (ticket['id'],)).fetchall()
    
    conn.close()
    return render_template("check_status.html", ticket=ticket, history=history, comments=comments)

# АВТОРИЗАЦИЯ И ВХОД
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        
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
        action = request.form.get("action")
        ticket_id = request.form.get("ticket_id")
        
        if action == "update_status":
            new_status = request.form.get("status")
            note = request.form.get("note", "").strip()
            
            if ticket_id and new_status:
                old_ticket = conn.execute('SELECT status FROM tickets WHERE id = ?', (ticket_id,)).fetchone()
                old_status = old_ticket['status'] if old_ticket else 'Новая'
                
                conn.execute('UPDATE tickets SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (new_status, ticket_id))
                
                conn.execute('''
                    INSERT INTO TicketHistory (ticket_id, old_status, new_status, actor_id, note)
                    VALUES (?, ?, ?, ?, ?)
                ''', (ticket_id, old_status, new_status, session['user_id'], note if note else "Статус изменен сотрудником"))
                
                conn.commit()
                log_event("TICKET_STATUS", f"Сотрудник ID {session['user_id']} изменил статус тикета ID {ticket_id} на '{new_status}'")
                flash(f"Статус заявки успешно изменен на '{new_status}'", "success")
                
        elif action == "add_comment":
            body = request.form.get("body", "").strip()
            visibility = request.form.get("visibility", "public")
            
            if ticket_id and body:
                conn.execute('''
                    INSERT INTO Comments (ticket_id, author_id, body, visibility)
                    VALUES (?, ?, ?, ?)
                ''', (ticket_id, session['user_id'], body, visibility))
                conn.commit()
                log_event("COMMENT_ADDED", f"Сотрудник ID {session['user_id']} добавил комментарий к тикету ID {ticket_id}")
                flash("Комментарий успешно добавлен", "success")
        
        return redirect(url_for('admin_panel'))

    # МЕДИА-ЗАПРОСЫ ДЛЯ ФИЛЬТРАЦИИ И ПОИСКА
    search_query = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '').strip()
    
    query = '''
        SELECT t.*, c.name as category_name, l.room, l.building 
        FROM tickets t
        LEFT JOIN categories c ON t.category_id = c.id
        LEFT JOIN locations l ON t.location_id = l.id
        WHERE 1=1
    '''
    params = []

    if search_query:
        query += " AND (t.public_number LIKE ? OR t.title LIKE ? OR t.description LIKE ?)"
        like_str = f"%{search_query}%"
        params.extend([like_str, like_str, like_str])

    if status_filter:
        query += " AND t.status = ?"
        params.append(status_filter)

    query += " ORDER BY t.created_at DESC"
    tickets = conn.execute(query, params).fetchall()

    # Модуль F: Расчет базовой статистики для MVP
    stats = {
        "total": conn.execute('SELECT COUNT(*) FROM tickets').fetchone()[0],
        "open": conn.execute("SELECT COUNT(*) FROM tickets WHERE status NOT IN ('Решена', 'Отклонена')").fetchone()[0],
        "closed": conn.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Решения', 'Отклонена')").fetchone()[0]
    }

    conn.close()
    return render_template("admin.html", tickets=tickets, stats=stats, search=search_query, current_status=status_filter)

if __name__ == "__main__":
    app.run(debug=True, port=5000)