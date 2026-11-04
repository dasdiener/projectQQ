import os
import json
import requests
import urllib3

# Отключаем предупреждения о проверке SSL-сертификатов (актуально для локальной разработки с GigaChat)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Конфигурация API GigaChat
# Рекомендуется настроить переменные окружения на ПК команды:
# set GIGACHAT_CREDENTIALS="ваш_авторизационный_токен_из_личного_кабинета"
GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS", "YOUR_GIGACHAT_CREDENTIALS_HERE")
GIGACHAT_AUTH_URL = "https://sberbank.ru"
GIGACHAT_API_URL = "https://sberbank.ru"

def get_giga_token():
    """Получает временный токен доступа (Access Token) для GigaChat API."""
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'Authorization': f'Bearer {GIGACHAT_CREDENTIALS}'
    }
    payload = {'scope': 'GIGACHAT_API_PERS'}
    
    try:
        # verify=False используется, так как у Минцифры свои SSL-сертификаты
        response = requests.post(GIGACHAT_AUTH_URL, headers=headers, data=payload, verify=False, timeout=10)
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        print(f"[AI Error] Ошибка авторизации в GigaChat: {e}")
        return None

def ask_gigachat(user_text):
    """
    Анализирует текст обращения пользователя согласно ТЗ хакатона.
    Возвращает словарь (dict) со строго заданной структурой.
    """
    # Дефолтный безопасный ответ на случай падения сети или ошибки API
    fallback_response = {
        "status": "success",
        "type": "unknown",
        "category": "Общее",
        "title": "Новое обращение",
        "ai_answer": "Извините, не удалось обработать запрос автоматически. Пожалуйста, обратитесь к сотруднику УПК или создайте заявку вручную.",
        "need_ticket": True
    }
    
    token = get_giga_token()
    if not token:
        return fallback_response

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    # Жесткий системный промт, описывающий логику ТЗ, категории и структуру JSON
    system_prompt = (
        "Ты — ИИ-помощник колледжа, модуль первичной классификации и обработки обращений. "
        "Твоя задача — проанализировать текст пользователя и вернуть ответ СТРОГО в формате JSON. "
        "В твоем ответе не должно быть никакого текста вокруг JSON, никаких Markdown-оберток (типа ```json), только сырой валидный JSON-объект.\n\n"
        
        "Правила классификации типов сообщений (поле 'type'):\n"
        "1. 'info' (Информационный вопрос): Пользователь спрашивает 'Как...', 'Где...', 'Что делать...'. Выдай короткую инструкцию.\n"
        "2. 'repair' (Обычная неисправность): Что-то сломалось, не работает, загрязнилось. Предложи создать заявку.\n"
        "3. 'danger' (Потенциальная опасность): Искры, дым, запах гари, оголенный провод, прорыв горячей воды. "
        "ЗАПРЕТИ ремонт, прикажи отойти, не трогать приборы и немедленно сообщить администрации!\n"
        "4. 'insufficient' (Недостаточно данных): Слишком короткий или непонятный текст (например, 'У меня проблема'). Задай уточняющий вопрос.\n"
        "5. 'unknown' (Неизвестный вопрос): Вопрос не по теме колледжа или базы знаний. Честно скажи, что информации недостаточно.\n\n"
        
        "Доступные категории (поле 'category'): 'Оборудование', 'Мебель', 'Электрика', 'Инфраструктура/Интернет', 'Уборка', 'Общее'.\n\n"
        
        "Правило для поля 'need_ticket': true, если требуется ремонт, выезд сотрудника или уточнение информации. false — только для чистых инфо-ответов.\n\n"
        
        "Формат JSON, который ты обязан вернуть:\n"
        "{\n"
        "  \"type\": \"info|repair|danger|insufficient|unknown\",\n"
        "  \"category\": \"Название категории\",\n"
        "  \"title\": \"Краткий лаконичный заголовок проблемы (до 5-7 слов)\",\n"
        "  \"ai_answer\": \"Твой текстовый ответ пользователю по правилам ТЗ\",\n"
        "  \"need_ticket\": true|false\n"
        "}"
    )

    data = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        "temperature": 0.1,  # Низкая температура для стабильности структуры
        "stream": False
    }

    try:
        response = requests.post(GIGACHAT_API_URL, headers=headers, json=data, verify=False, timeout=15)
        response.raise_for_status()
        
        raw_content = response.json()['choices'][0]['message']['content'].strip()
        
        # Очистка от возможных markdown-тегов, если модель проигнорировала системный запрет
        if raw_content.startswith("```"):
            raw_content = raw_content.strip("`").replace("json", "", 1).strip()
            
        result_json = json.loads(raw_content)
        return result_json

    except (requests.RequestException, KeyError, json.JSONDecodeError) as e:
        print(f"[AI Error] Не удалось разобрать ответ от GigaChat: {e}")
        return fallback_response