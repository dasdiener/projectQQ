import os
import datetime

# Путь к файлу логов системы — исправлено на __file__
LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), "system_events.log")

def log_event(event_type, message):
    """
    Универсальная функция сквозного журналирования для хакатона.
    Записывает события в файл system_events.log с отметкой времени.
    
    Категории event_type по ТЗ:
    - TICKET_CREATED : успешное создание новой заявки
    - STATUS_CHANGED : ручная смена статуса в панели администратора
    - AI_PROCESSING  : логи классификации текста ИИ-помощником
    - SECURITY_ALERT : перехват опасных триггеров или ошибки валидации
    - DATABASE_ERROR : сбои при работе с SQLite
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{event_type}] {message}\n"
    
    try:
        # Режим 'a' (append) создает файл, если его нет, и дописывает строки в конец
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as log_file:
            log_file.write(log_entry)
        
        # Дублируем лог в консоль сервера Flask для оперативной отладки
        print(log_entry.strip())
    except Exception as e:
        print(f"[CRITICAL ERROR] Не удалось записать лог в файл: {e}")

def get_latest_logs(limit=50):
    """
    Вспомогательная функция для возможного вывода логов прямо в интерфейс админки
    """
    if not os.path.exists(LOG_FILE_PATH):
        return []
    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as log_file:
            lines = log_file.readlines()
            return [line.strip() for line in lines[-limit:]]
    except Exception:
        return []

# Исправлено на правильные системные переменные __name__ == "__main__"
if __name__ == "__main__":
    # Тест автономной работы логгера
    print("Запуск теста журналирования...")
    log_event("SYSTEM_START", "Модуль logger.py успешно инициализирован локально")
    log_event("TICKET_CREATED", "Успешно создана демо-заявка REQ-777888 для Кабинета 214")