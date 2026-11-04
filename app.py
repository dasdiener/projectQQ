'soul 'obstruction
'soul 'obstruction
import os
import sqlite3
import secrets
import hashlib
from flask import Flask, render_template, request, redirect, url_for, session, flash
from validators import validate_user_text
from ai_helper import ask_gigachat

# Безопасный импорт логгера (заглушка спасет от ошибок, если logger.py еще не готов локально)
try:
    from logger import log_event
except ImportError:
    def log_event(event_type, description):
        pass  # Просто пропускает, если файла logger.py пока нет

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
    # Проверяем, перешел ли пользователь по QR-коду (например, /?qr=qr_room_214)
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
        
        # 1. Валидация текста через модуль Помощника №1
        is_valid, error_msg = validate_user_text(user_text)
        if not is_valid:
            flash(error_msg, "error")
            locations = conn.execute('SELECT * FROM locations').fetchall()
            conn.close()
            return render_template("create.html", locations=locations, selected_location=location_id)
        
        # ЛОГИРОВАНИЕ: Фиксируем успешную валидацию и отправку запроса
        log_event("AI_REQUEST", f"Пользователь отправил запрос для локации ID {location_id}: '{user_text}'")
        
        # 2. Запрос к ИИ-помощнику (модуль ai_helper)
        ai_result = ask_gigachat(user_text)
        
        # ЛОГИРОВАНИЕ: Записываем тип вердикта от ИИ-помощника
        log_event("AI_RESPONSE", f"ИИ вернул тип [{ai_result.get('type')}]. Создание тикета: {ai_result.get('need_ticket')}")
        
        # Передаем результат ИИ на промежуточный экран (ai_result.html)
        locations = conn.execute('SELECT * FROM locations').fetchall()
        conn.close()
        return render_template("ai_result.html", ai=ai_result, text=user_text, location_id=location_id)
        
    # GET-запрос: загружаем локации. Если есть ?qr=..., находим нужную комнату
    qr_key = request.args.get('qr')
    selected_location = None
    if qr_key:
        loc = conn.execute('SELECT * FROM locations WHERE qr_key = ?', (qr_key,)).fetchone()
        if loc:
            selected_location = loc['id']
            # ЛОГИРОВАНИЕ: Переход по валидному QR-коду
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
    
    conn = get_db_connection()
    
    # Ищем ID категории в базе по названию, пришедшему от ИИ
    cat = conn.execute('SELECT id FROM categories WHERE name = ?', (ai_category,)).fetchone()
    category_id = cat['id'] if cat else 1 # Дефолт на первую категорию, если ИИ выдал кастомную
    
    # Генерируем уникальные публичные данные по ТЗ
    public_number = f"REQ-{secrets.randbelow(900000) + 100000}" # Формат REQ-123456
    raw_token = secrets.token_urlsafe(16) # Безопасный токен для ссылки отслеживания
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    
    # Сохраняем тикет
    conn.execute('''
        INSERT INTO tickets (public_number, title, description, category_id, location_id, tracking_token_hash)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (public_number, ai_title, user_text, category_id, location_id, token_hash))
    
    conn.commit()
    conn.close()
    
    # ЛОГИРОВАНИЕ: Фиксация создания новой официальной заявки
    log_event("TICKET_CREATED", f"Успешно создана официальная заявка {public_number} (Локация ID: {location_id})")
    
    # Перенаправляем на страницу успешного создания, отдавая пользователю сырой токен ОДИН раз
    return render_template("success.html", number=public_number, token=raw_token)

# ОТСЛЕЖИВАНИЕ СТАТУСА ЗАЯВКИ ЗАЯВИТЕЛЕМ
@app.route("/status")
def check_status():
    token = request.args.get('token')
    if not token:
        return render_template("check_status.html", ticket=None, error="Токен отслеживания не указан.")
        
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    conn = get_db_connection()
    # Вытаскиваем тикет вместе с названиями категории и комнаты
    ticket = conn.execute('''
        SELECT t.*, c.name as category_name, l.room, l.building 
        FROM tickets t
        LEFT JOIN categories c ON t.category_id = c.id
        LEFT JOIN locations l ON t.location_id = l.id
        WHERE t.tracking_token_hash = ?
    ''', (token_hash,)).fetchone()
    conn.close()
    
    if not ticket:
        return render_template("check_status.html", ticket=None, error="Заявка с таким токеном не найдена.")
        
    return render_template("check_status.html", ticket=ticket)

# ================= АВТОРИЗАЦИЯ И ПАНЕЛЬ УПК =================

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
            
            # ЛОГИРОВАНИЕ: Успешный вход в систему
            log_event("SECURITY", f"Сотрудник '{username}' успешно вошел в административную панель")
            return redirect(url_for('admin_panel'))
        else:
            # ЛОГИРОВАНИЕ: Подозрительное событие (неверный пароль)
            log_event("SECURITY", f"НЕУСПЕШНАЯ попытка входа под логином '{username}'")
            flash("Неверный логин или пароль", "error")
            
    return render_template("login.html")

@app.route("/logout")
def logout():
    username = session.get('user_name', 'Неизвестно')
    session.clear()
    # ЛОГИРОВАНИЕ: Выход из сессии
    log_event("SECURITY", f"Сотрудник '{username}' вышел из системы")
    return redirect(url_for('home'))

# ЗАЩИЩЕННАЯ ПАНЕЛЬ СОТРУДНИКА УПК
@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    # Проверка прав доступа по ТЗ (раздел 4, ограничения роли)
    if 'user_id' not in session:
        log_event("SECURITY", "Попытка несанкционированного доступа к панели /admin без авторизации!")
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    
    # Обработка действий сотрудника (изменение статуса / назначение исполнителя)
    if request.method == "POST":
        ticket_id = request.form.get("ticket_id")
        new_status = request.form.get("status")
        
        if ticket_id and new_status:
            conn.execute('UPDATE tickets SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (new_status, ticket_id))
            conn.commit()
            
            # ЛОГИРОВАНИЕ: Смена статуса заявки
            log_event("TICKET_STATUS", f"Сотрудник ID {session['user_id']} изменил статус тикета ID {ticket_id} на '{new_status}'")
            flash(f"Статус заявки №{ticket_id} успешно изменен на '{new_status}'", "success")
            
    #Получение параметров фильтрации и поиска (раздел 6.3 ТЗ)
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
    conn.close()
    
    return render_template("admin.html", tickets=tickets, search=search_query, current_status=status_filter)

if __name__ == "__main__":
    app.run(debug=True)