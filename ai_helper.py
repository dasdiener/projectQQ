import os
import requests
import uuid
from dotenv import load_dotenv

load_dotenv()

# Инструкция для ИИ (Системный промпт), закладывающая логику из ТЗ
SYSTEM_PROMPT = """Ты — Цифровой помощник колледжа. Твоя задача — классифицировать обращение пользователя и строго следовать правилам:
1. Если это ИНФОРМАЦИОННЫЙ ВОПРОС (например, "Как подключить ноутбук к проектору?"), дай краткую безопасную инструкцию.
2. Если это ОБЫЧНАЯ НЕИСПРАВНОСТЬ ("Сломалась ручка", "Не работает проектор"), предложи оформить заявку и выдели категорию.
3. Если это ПОТЕНЦИАЛЬНАЯ ОПАСНОСТЬ ("Искрит розетка", "Запах гари"), КАТЕГОРИЧЕСКИ запрети самостоятельный ремонт. Напиши: "НЕ ПРИБЛИЖАЙТЕСЬ и не трогайте оборудование! Срочно сообщите сотруднику колледжа."
4. Если НЕИЗВЕСТНЫЙ ВОПРОС, честно ответь, что информации недостаточно.
Не выдумывай сроки ремонта, контакты и правила. Ответ возвращай в формате JSON:
{
  "type": "question|ticket|danger|unknown",
  "ai_answer": "текст ответа для пользователя",
  "suggested_category": "Оборудование/Мебель/Электрика/Чистота (или null)"
}"""

def get_giga_token():
    """Получение временного токена доступа GigaChat"""
    url = "https://sberbank.ru"
    headers = {
        'Authorization': f'Bearer {os.getenv("GIGACHAT_CREDENTIALS")}',
        'RqUID': str(uuid.uuid4()),
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {'scope': 'GIGACHAT_API_PERS'}
    # Внимание: для работы с сертификатами Минцифры может потребоваться verify=False в условиях хакатона
    response = requests.post(url, headers=headers, data=data, verify=False)
    return response.json().get('access_token')

def analyze_message(user_text):
    """Отправка текста в GigaChat и получение классификации"""
    token = get_giga_token()
    if not token:
        return {"type": "unknown", "ai_answer": "Ошибка связи с ИИ-помощником.", "suggested_category": None}

    url = "https://sberbank.ru"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ],
        "temperature": 0.3 # Низкая температура для более точных и менее "творческих" ответов
    }

    try:
        response = requests.post(url, headers=headers, json=payload, verify=False)
        # Здесь будет логика обработки ответа и извлечения JSON
        ai_response_text = response.json()['choices'][0]['message']['content']
        return ai_response_text # В MVP можно доработать парсинг строки в JSON
    except Exception as e:
        return {"type": "unknown", "ai_answer": f"Ошибка обработки: {str(e)}", "suggested_category": None}
