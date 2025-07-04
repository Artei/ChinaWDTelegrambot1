import json
import os
from dataclasses import asdict, is_dataclass
from typing import Any

from core.config import settings, Settings

SETTINGS_FILE = "settings.json"

def _update_dataclass_from_dict(dc_instance: Any, data: dict):
    """Рекурсивно обновляет поля вложенных датаклассов из словаря."""
    for key, value in data.items():
        if hasattr(dc_instance, key):
            field = getattr(dc_instance, key)
            if is_dataclass(field) and isinstance(value, dict):
                # Если поле - это другой датакласс, рекурсивно обновляем его
                _update_dataclass_from_dict(field, value)
            else:
                # Иначе просто устанавливаем значение
                setattr(dc_instance, key, value)

def save_settings():
    """Сохраняет текущие настройки в JSON-файл."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            # asdict рекурсивно преобразует датаклассы в словари
            json.dump(asdict(settings), f, ensure_ascii=False, indent=4)
        return True
    except (IOError, TypeError) as e:
        print(f"Ошибка при сохранении настроек: {e}")
        return False

def load_settings() -> Settings:
    """
    Загружает настройки из JSON-файла.
    Если файл не найден или поврежден, возвращает настройки по умолчанию.
    """
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Рекурсивно обновляем наш объект настроек данными из файла
            _update_dataclass_from_dict(settings, data)
            print("Настройки успешно загружены из файла.")
        except (IOError, json.JSONDecodeError) as e:
            print(f"Ошибка при загрузке настроек: {e}. Используются настройки по умолчанию.")
            # В случае ошибки просто используем `settings` по умолчанию
    else:
        print("Файл настроек не найден. Используются настройки по умолчанию.")
        # Если файла нет, создаем его с настройками по умолчанию
        save_settings()

    return settings 