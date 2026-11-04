def validate_user_text(text):
    if not text:
        return False, "Описание проблемы не может быть пустым."

    cleaned_text = text.strip()

    if len(cleaned_text) < 5:
        return False, "Описание проблемы слишком короткое. Напишите подробнее (минимум 5 символов)."

    return True, cleaned_text


if __name__ == "__main__":
    # Проверка на None / пустоту
    print(validate_user_text(None))                 
    print(validate_user_text(" "))                  
    
    
    print(validate_user_text(" abc "))              
    
    print(validate_user_text(" Принтер сломался ")) 