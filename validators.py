import html
import sqlite3

def validate_user_text(text):
    """
    Проверяет пользовательский ввод на безопасность и соответствие правилам ТЗ.
    Устраняет XSS-уязвимости и проверяет длину текста.
    """
    if not text:
        return False, "Описание проблемы не может быть пустым."

    cleaned_text = text.strip()

    if len(cleaned_text) < 5:
        return False, "Описание проблемы слишком короткое. Напишите подробнее (минимум 5 символов)."

    if len(cleaned_text) > 1000:
        return False, "Описание проблемы слишком длинное (максимум 1000 символов)."

    # Экранирование опасных тегов для защиты от XSS
    safe_text = html.escape(cleaned_text)

    return True, safe_text


def check_duplicate(db_path, location_id, text):
    """
    Проверяет наличие активных дубликатов заявок в конкретной локации.
    Ищет нерешенные тикеты (статус отличный от 'Выполнено'/'Решена') 
    в таблице Tickets, где описание частично или полностью совпадает.
    """
    if not location_id:
        return False, ""

    cleaned_text = text.strip().lower()
    
    # Выделяем первые значимые слова для поиска похожих инцидентов
    words = [w for w in cleaned_text.split() if len(w) > 3]
    if not words:
        search_pattern = f"%{cleaned_text}%"
    else:
        # Ищем по ключевому первому слову (например, 'проектор', 'розетка', 'стул')
        search_pattern = f"%{words[0]}%"

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Точный запрос к вашей таблице Tickets (с учетом регистра и структуры полей)
        query = """
            SELECT id, public_number FROM Tickets 
            WHERE location_id = ? 
              AND status NOT IN ('Выполнено', 'Решена') 
              AND LOWER(description) LIKE ?
            LIMIT 1
        """
        cursor.execute(query, (location_id, search_pattern))
        duplicate = cursor.fetchone()
        conn.close()
        
        if duplicate:
            return True, f"Заявка на похожую проблему в этом помещении уже зарегистрирована под номером {duplicate['public_number']}. Техническая служба уже занимается данным вопросом."
        
        return False, ""
    except Exception:
        # Если база еще не создана или заблокирована во время параллельного запроса,
        # пропускаем валидацию дубликатов во избежание критической остановки бэкенда
        return False, ""


if __name__ == "__main__":
    # Тестирование базового валидатора текста
    print("Проверка на None:", validate_user_text(None))                 
    print("Проверка на пустоту:", validate_user_text(" "))                  
    print("Проверка на короткий текст:", validate_user_text(" abc "))              
    print("Проверка на корректный текст:", validate_user_text(" Принтер сломался ")) 
    print("Проверка на XSS-атаку:", validate_user_text("<script>alert('hack')</script>"))