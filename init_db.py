import os
import sqlite3

def initialize_database():
    db_filename = 'database.db'
    schema_filename = 'schema.sql'
    
    print(f"Начало инициализации базы данных...")

    # Если старая база существует, удаляем её для полной чистоты структуры
    if os.path.exists(db_filename):
        try:
            os.remove(db_filename)
            print(f" Сброшен старый файл базы данных '{db_filename}'")
        except Exception as e:
            print(f"❌ Не удалось удалить старый файл базы: {e}")
            return

    if not os.path.exists(schema_filename):
        print(f"❌ Критическая ошибка: Файл схемы '{schema_filename}' не найден в корне проекта!")
        return

    try:
        # Подключаемся и создаем новый файл
        conn = sqlite3.connect(db_filename)
        
        # Читаем инструкции SQL из schema.sql
        with open(schema_filename, 'r', encoding='utf-8') as f:
            schema_script = f.read()
            
        # Выполняем весь SQL скрипт
        conn.executescript(schema_script)
        conn.commit()
        conn.close()
        
        print(f"🔥 УСПЕХ: Файл '{db_filename}' успешно создан!")
        print(f" Все 8 таблиц по ТЗ инициализированы.")
        print(f" Загружен демонстрационный кабинет 214 для защиты.")
        print(f" Создан тестовый аккаунт сотрудника (Логин: admin / Пароль: admin).")
        
    except Exception as e:
        print(f"❌ Критическая ошибка при сборке базы данных: {e}")

if __name__ == "__main__":
    initialize_database()