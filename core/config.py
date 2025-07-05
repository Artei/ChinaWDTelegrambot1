from dataclasses import dataclass, field
from typing import Dict
import os

def get_trusted_channel_id():
    """Безопасно читает и преобразует TRUSTED_CHANNEL_ID из переменных окружения."""
    val = os.getenv("TRUSTED_CHANNEL_ID")
    if val and val.strip():
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0  # Возвращаем 0, если значение некорректно
    return 0

@dataclass
class BotConfig:
    """Хранит базовые настройки бота и ID ролей."""
    token: str = os.getenv("BOT_TOKEN")
    admin_ids: list[int] = field(default_factory=lambda: [int(admin_id) for admin_id in os.getenv("ADMIN_IDS", "").split(",") if admin_id])
    trusted_channel_id: int = field(default_factory=get_trusted_channel_id)


@dataclass
class CurrencyRates:
    """Хранит курсы валют."""
    cny_to_rub: float = 10.91  # Курс юаня к рублю
    eur_to_rub: float = 92.67 # Курс евро к рублю

@dataclass
class Fees:
    """Хранит комиссии и сборы."""
    bank_commission_percent: float = 0.02  # 2% комиссия банка за перевод
    # Далее идут фиксированные суммы в рублях
    company_commission_rub: float = 50000.0   # Фиксированная комиссия компании в рублях
    china_expenses_rub: float = 150000.0  # Фиксированные расходы в Китае в рублях

# --- Новые классы для таможенных ставок ---

@dataclass
class DutyRates:
    """Ставки таможенных пошлин в евро за 1 см³."""
    # Словарь: {max_volume: rate}
    age_0_3_years: Dict[int, float] = field(default_factory=lambda: {
        # Для авто до 3 лет используется % от стоимости, но не менее €/см³
        # Процентная ставка (0.48) и минимальная ставка (2.5)
        # Эти значения пока оставим в логике, но в будущем можно вынести
    })
    age_3_5_years: Dict[int, float] = field(default_factory=lambda: {
        1000: 1.5,
        1500: 1.7,
        1800: 2.5,
        2300: 2.7,
        3000: 3.0,
        99999: 3.6  # Условный максимум
    })
    age_older_5_years: Dict[int, float] = field(default_factory=lambda: {
        1000: 3.0,
        1500: 3.2,
        1800: 3.5,
        2300: 4.8,
        3000: 5.0,
        99999: 5.7 # Условный максимум
    })

@dataclass
class RecyclingFeeRates:
    """Ставки утилизационного сбора для физлиц в рублях."""
    under_3_years: float = 3400.0
    over_3_years: float = 5200.0

@dataclass
class CustomsFees:
    """Объединяет все таможенные сборы."""
    base_customs_fee_rub: float = 4269.0 # Фиксированный таможенный сбор
    duty: DutyRates = field(default_factory=DutyRates)
    recycling: RecyclingFeeRates = field(default_factory=RecyclingFeeRates)

@dataclass
class Settings:
    """Объединяет все настройки."""
    bot: BotConfig = field(default_factory=BotConfig)
    rates: CurrencyRates = field(default_factory=CurrencyRates)
    fees: Fees = field(default_factory=Fees)
    customs: CustomsFees = field(default_factory=CustomsFees)

# Создаем единый объект с настройками, который будем использовать в расчетах
# В будущем эти значения будут подгружаться из базы данных или админки
settings = Settings()

# Пример использования:
# from core.config import settings
# print(settings.rates.cny_to_rub)
# print(settings.fees.company_commission_rub) 