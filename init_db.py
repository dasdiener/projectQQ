import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # 1. Таблица кабинетов (Locations)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building TEXT NOT NULL,
            room TEXT NOT NULL,
            qr_key TEXT UNIQUE NOT NULL
        )
    ''')

    # 2. Таблица заявок (Tickets)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            public_number TEXT UNIQUE NOT NULL,
            title TEXT,
            description TEXT NOT NULL,
            location_id INTEGER,
            status TEXT DEFAULT 'Новая',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tracking_token TEXT NOT NULL,
            FOREIGN KEY (location_id) REFERENCES locations(id)
        )
    ''')

    # 3. Таблица Базы Знаний для ИИ (KnowledgeBase)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_base (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL
        )
    ''')

    # Заполним тестовые локации (для QR-кодов по ТЗ)
    cursor.executemany('''
        INSERT OR IGNORE INTO locations (building, room, qr_key) VALUES (?, ?, ?)
    ''', [
        ('Главный', '214', 'room_214'),
        ('Лабораторный', '305', 'room_305'),
        ('Главный', 'Актовый зал', 'room_hall')
    ])

    # Заполним базу знаний ИИ базовыми инструкциями из ТЗ
    cursor.executemany('''
        INSERT OR IGNORE INTO knowledge_base (question, answer) VALUES (?, ?)
    ''', [
        ('проектор', 'Чтобы подключить ноутбук к проектору, проверьте кабель HDMI, включите проектор пультом и нажмите Win+P на ноутбуке, выбрав "Повторяющийся".'),
        ('принтер', 'Если принтер не печатает, проверьте плотность закрытия лотка, наличие бумаги и отсутствие замятий. Перезагрузите принтер.'),
        ('статус', 'Проверить статус заявки можно на главной странице в разделе "Проверить обращение", введя ваш секретный защитный код.')
    ])

    conn.commit()
    conn.close()
    print("База данных успешно создана и заполнена тестовыми данными!")

if __name__ == '__main__':
    init_db()
