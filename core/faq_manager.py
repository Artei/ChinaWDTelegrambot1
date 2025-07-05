import json
import os

FAQ_FILE = 'faq.json'

def load_faq_data():
    """Загружает данные из faq.json"""
    if not os.path.exists(FAQ_FILE):
        return {}
    try:
        with open(FAQ_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError):
        # В случае ошибки чтения файла (например, он пустой или поврежден)
        # возвращаем пустой словарь, чтобы избежать падения бота.
        return {}

def save_faq_data(data):
    """Сохраняет данные в faq.json"""
    with open(FAQ_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4) 