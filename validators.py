import html

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

    # Безопасность прежде всего: превращаем опасные теги типа <script> в безопасный текст &lt;script&gt;
    safe_text = html.escape(cleaned_text)

    return True, safe_text


if __name__ == "__main__":
    # Тестирование валидатора для проверки логики
    print("Проверка на None:", validate_user_text(None))                 
    print("Проверка на пустоту:", validate_user_text(" "))                  
    print("Проверка на короткий текст:", validate_user_text(" abc "))              
    print("Проверка на корректный текст:", validate_user_text(" Принтер сломался ")) 
    print("Проверка на XSS-атаку:", validate_user_text("<script>alert('hack')</script>"))