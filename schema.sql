-- Включаем поддержку Foreign Keys (Обязательно для Модуля D по ТЗ!)
PRAGMA foreign_keys = ON;

-- 1. Таблица пользователей, сотрудников и системных аккаунтов
CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    login TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL,          -- 'admin', 'staff', 'system'
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
    qr_key TEXT UNIQUE NOT NULL  -- Токен из QR-кода
);

-- 4. Основная таблица заявок (Tickets)
CREATE TABLE IF NOT EXISTS Tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    public_number TEXT UNIQUE NOT NULL, -- Номер REQ-XXXXXX для заявителя
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category_id INTEGER,
    location_id INTEGER,
    status TEXT DEFAULT 'Новая',         
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    assignee_id INTEGER,
    tracking_token_hash TEXT NOT NULL,   -- Хеш ссылки отслеживания
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
    visibility TEXT DEFAULT 'public',    -- 'public' или 'internal'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES Tickets(id),
    FOREIGN KEY (author_id) REFERENCES Users(id)
);

-- 6. История изменений статусов
CREATE TABLE IF NOT EXISTS TicketHistory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    actor_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    note TEXT,                           -- Причина изменения/отклонения
    FOREIGN KEY (ticket_id) REFERENCES Tickets(id),
    FOREIGN KEY (actor_id) REFERENCES Users(id)
);

-- 7. Метаданные вложений (Требование сущностей раздела 10 ТЗ!)
CREATE TABLE IF NOT EXISTS Attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    storage_key TEXT NOT NULL,
    file_type TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES Tickets(id)
);

-- 8. База знаний для ИИ (Требование сущностей раздела 10 ТЗ!)
CREATE TABLE IF NOT EXISTS KnowledgeBase (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category TEXT NOT NULL,
    source TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
-- =====================================================================
-- НАПОЛНЕНИЕ ДЕМО-ДАННЫМИ ДЛЯ ДЕМОНСТРАЦИИ НА ЗАЩИТЕ (Раздел 6.4 и 16)
-- =====================================================================

-- 1. Забиваем обязательные системные учетные записи и демо-сотрудников
-- ID 1 выделен под СИСТЕМУ для автоматических логов истории без конфликтов Foreign Key
INSERT OR IGNORE INTO Users (id, name, login, role, password_hash) VALUES 
(1, 'Автоматическая Система', 'system_core', 'system', 'system_no_password');

-- Демо-сотрудник для входа в панель УПК (Пароль: admin - подходит под проверку в app.py)
INSERT OR IGNORE INTO Users (id, name, login, role, password_hash) VALUES 
(2, 'Иван Ответственный (УПК)', 'admin', 'staff', 'admin');


-- 2. Забиваем обязательные категории обращений из ТЗ
INSERT OR IGNORE INTO Categories (id, name, description) VALUES 
(1, 'Оборудование и ИТ', 'Проблемы с проекторами, компьютерами, принтерами'),
(2, 'Имущество и мебель', 'Сломанные парты, стулья, двери, ручки окон'),
(3, 'Электрика и освещение', 'Не работают розетки, мигают или перегорели лампы'),
(4, 'Хозяйственные вопросы', 'Требуется уборка, проблемы с отоплением или водой');


-- 3. Забиваем обязательные тестовые локации (Кабинет 214 для сценария защиты!)
INSERT OR IGNORE INTO Locations (id, building, floor, room, zone_name, qr_key) VALUES 
(1, 'Главный корпус', '2', '214', 'Кабинет информатики (Защита)', 'room_214'),
(2, 'Лабораторный корпус', '3', '305', 'Лаборатория системного администрирования', 'room_305'),
(3, 'Главный корпус', '1', 'Холл', 'Общая зона у входа', 'hall_main');


-- 4. Первичное наполнение Базы Знаний ИИ из текста официальной инструкции
INSERT OR IGNORE INTO KnowledgeBase (id, question, answer, category, source) VALUES 
(1, 'Как подключить ноутбук к проектору', 'Порядок действий: 1. Проверить кабели. 2. Подключить HDMI/VGA. 3. Включить проектор кнопкой. 4. На Windows нажать Win+P и выбрать Дублировать. Саморемонт запрещен!', 'Оборудование и ИТ', 'Инструкция по проекторам'),
(2, 'Первичная проверка принтера если он не печатает', 'Порядок действий: 1. Проверить питание и экран. 2. Проверить бумагу в лотке. 3. Убедиться в правильности выбора принтера на ПК. Не разбирать картридж!', 'Оборудование и ИТ', 'Инструкция по принтерам');