-- Включаем поддержку Foreign Keys (Обязательно для Модуля D по ТЗ!)
PRAGMA foreign_keys = ON;

-- 1. Таблица пользователей и сотрудников
CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    login TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL,          -- 'admin', 'staff'
    password_hash TEXT NOT NULL
);

-- 2. Справочник категорий
CREATE TABLE IF NOT EXISTS Categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT
);

-- 3. Локации и привязки QR-кодов
CREATE TABLE IF NOT EXISTS Locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    building TEXT NOT NULL,
    floor TEXT NOT NULL,
    room TEXT NOT NULL,
    zone_name TEXT,
    qr_key TEXT UNIQUE NOT NULL  -- Тот самый токен из QR-кода
);

-- 4. Основная таблица заявок (Tickets)
CREATE TABLE IF NOT EXISTS Tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    public_number TEXT UNIQUE NOT NULL, -- Случайный красивый номер для заявителя
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category_id INTEGER,
    location_id INTEGER,
    status TEXT DEFAULT 'Новая',         -- По жизненному циклу из ТЗ
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    assignee_id INTEGER,
    tracking_token_hash TEXT NOT NULL,   -- Безопасный хеш ссылки отслеживания
    FOREIGN KEY (category_id) REFERENCES Categories(id),
    FOREIGN KEY (location_id) REFERENCES Locations(id),
    FOREIGN KEY (assignee_id) REFERENCES Users(id)
);

-- 5. Комментарии к заявкам
CREATE TABLE IF NOT EXISTS Comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    body TEXT NOT NULL,
    visibility TEXT DEFAULT 'public',    -- 'public' или 'internal' по ТЗ
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES Tickets(id),
    FOREIGN KEY (author_id) REFERENCES Users(id)
);

-- 6. История изменений статусов (Для Модуля C и критериев оценки жюри)
CREATE TABLE IF NOT EXISTS TicketHistory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    actor_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    note TEXT,                           -- Причина отклонения или закрытия
    FOREIGN KEY (ticket_id) REFERENCES Tickets(id),
    FOREIGN KEY (actor_id) REFERENCES Users(id)
);

-- =====================================================================
-- НАПОЛНЕНИЕ ДЕМО-ДАННЫМИ ДЛЯ ДЕМОНСТРАЦИИ НА ЗАЩИТЕ (Раздел 6.4 и 16)
-- =====================================================================

-- Забиваем обязательные категории
INSERT OR IGNORE INTO Categories (id, name, description) VALUES 
(1, 'Оборудование и ИТ', 'Проблемы с проекторами, компьютерами, принтерами'),
(2, 'Имущество и мебель', 'Сломанные парты, стулья, двери, ручки окон'),
(3, 'Электрика и освещение', 'Не работают розетки, мигают или перегорели лампы'),
(4, 'Хозяйственные вопросы', 'Требуется уборка, проблемы с отоплением или водой');

-- Забиваем обязательные тестовые локации (Кабинет 214 из сценария защиты!)
INSERT OR IGNORE INTO Locations (id, building, floor, room, zone_name, qr_key) VALUES 
(1, 'Главный корпус', '2', '214', 'Кабинет информатики (Защита)', 'qr_room_214_demo'),
(2, 'Лабораторный корпус', '3', '305', 'Лаборатория системного администрирования', 'qr_lab_305_secure'),
(3, 'Главный корпус', '1', 'Холл', 'Общая зона у входа', 'qr_hall_main');

-- Создаем демо-сотрудника для проверки авторизации (Пароль захеширован)
-- Логин: staff_demo / Пароль: По ТЗ должен быть хэш, для демо используем условный хэш
INSERT OR IGNORE INTO Users (id, name, login, role, password_hash) VALUES 
(1, 'Иван Ответственный (УПК)', 'staff_demo', 'staff', 'pbkdf2:sha256:250000$demo_hash_value');