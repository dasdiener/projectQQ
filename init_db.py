import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # 1. Таблица локаций (помещений)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building TEXT NOT NULL,
            floor TEXT,
            room TEXT NOT NULL,
            zone_name TEXT,
            qr_key TEXT UNIQUE NOT NULL
        )
    ''')

    # 2. Таблица категорий неисправностей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        )
    ''')

    # 3. Таблица заявок (Tickets)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            public_number TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category_id INTEGER,
            location_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Новая',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            assignee_id INTEGER,
            tracking_token_hash TEXT NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            FOREIGN KEY (location_id) REFERENCES locations(id)
        )
    ''')

    # Наполняем базу тестовыми данными для демонстрации (Раздел 6.4 ТЗ требует 3-5 локаций)
    cursor.executemany('''
        INSERT OR IGNORE INTO locations (building, floor, room, zone_name, qr_key)
        VALUES (?, ?, ?, ?, ?)
    ''', [
        ('Главный корпус', '2', '214', 'Кабинет информатики', 'qr_room_214'),
        ('Главный корпус', '3', '305', 'Лаборатория физики', 'qr_room_305'),
        ('Корпус Б', '1', '101', 'Актовый зал', 'qr_zone_act'),
    ])

    # Наполняем базовыми категориями
    cursor.executemany('''
        INSERT OR IGNORE INTO categories (name, description)
        VALUES (?, ?)
    ''', [
        ('Оборудование', 'Проблемы с проекторами, ПК, принтерами'),
        ('Мебель', 'Сломанные стулья, парты, двери'),
        ('Электрика', 'Не работают розетки, искрение, свет'),
        ('Чистота', 'Требуется уборка помещения')
    ])

    conn.commit()
    conn.close()
    print("База данных успешно инициализирована и заполнена тестовыми данными!")

if __name__ == '__main__':
    init_db()
