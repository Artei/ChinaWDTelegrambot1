import datetime
from dataclasses import dataclass, field
from .config import Settings

@dataclass
class CustomsResult:
    """Хранит детализированный результат таможенных платежей."""
    duty_rub: float = 0.0
    customs_fee_rub: float = 0.0
    recycling_fee_rub: float = 0.0
    total_customs_rub: float = 0.0

@dataclass
class CalculationResult:
    """Хранит детализированный результат расчета."""
    car_price_rub: float = 0.0
    bank_commission_rub: float = 0.0
    company_commission_rub: float = 0.0
    china_expenses_rub: float = 0.0
    customs: CustomsResult = field(default_factory=CustomsResult)
    total_cost_rub: float = 0.0
    # ... здесь будут поля для таможенных платежей

def _calculate_customs_for_individual(user_data: dict, settings: Settings) -> CustomsResult:
    """
    Рассчитывает таможенные платежи для физического лица.
    ВНИМАНИЕ: Ставки являются примерными и должны обновляться в конфиге!
    """
    customs_result = CustomsResult()
    current_year = datetime.datetime.now().year
    car_age = current_year - user_data['year']
    engine_volume = user_data['engine_volume']
    engine_power = user_data.get('engine_power', 0)
    car_price_eur = (user_data['car_price_cny'] * settings.rates.cny_to_rub) / settings.rates.eur_to_rub

    # --- 1. Расчет пошлины ---
    duty_eur = 0.0
    duty_rate_map = {}
    if car_age < 3:
        # Для авто до 3 лет: % от стоимости, но не менее €/см3
        # TODO: Вынести 0.48 и 2.5 в конфиг
        duty_from_price = car_price_eur * 0.48
        duty_from_volume = 2.5 * engine_volume
        duty_eur = max(duty_from_price, duty_from_volume)
    else:
        if 3 <= car_age <= 5:
            duty_rate_map = settings.customs.duty.age_3_5_years
        else: # Старше 5 лет
            duty_rate_map = settings.customs.duty.age_older_5_years
        
        # Находим подходящую ставку из словаря
        # ИСПРАВЛЕНИЕ: Преобразуем ключ (max_volume) в int для корректного сравнения
        for max_volume_str, rate in sorted(duty_rate_map.items(), key=lambda item: int(item[0])):
            if engine_volume <= int(max_volume_str):
                duty_eur = rate * engine_volume
                break
    
    customs_result.duty_rub = duty_eur * settings.rates.eur_to_rub

    # --- 2. Таможенный сбор ---
    customs_result.customs_fee_rub = settings.customs.base_customs_fee_rub
    
    # --- 3. Утилизационный сбор (базовые ставки для физлиц) ---
    if car_age <= 3:
        customs_result.recycling_fee_rub = settings.customs.recycling.under_3_years
    else:
        customs_result.recycling_fee_rub = settings.customs.recycling.over_3_years
        
    # --- 4. Итого таможенные платежи ---
    customs_result.total_customs_rub = (
        customs_result.duty_rub +
        customs_result.customs_fee_rub +
        customs_result.recycling_fee_rub
    )
    
    return customs_result

def calculate_total_cost(user_data: dict, settings: Settings) -> CalculationResult:
    """
    Выполняет расчет итоговой стоимости автомобиля.
    
    :param user_data: Словарь с данными, собранными от пользователя.
    :param settings: Объект с текущими настройками (курсы, комиссии).
    :return: Объект с детализированным результатом расчета.
    """
    result = CalculationResult()
    
    # 1. Стоимость авто в рублях
    result.car_price_rub = user_data['car_price_cny'] * settings.rates.cny_to_rub
    
    # 2. Комиссия банка
    result.bank_commission_rub = result.car_price_rub * settings.fees.bank_commission_percent
    
    # 3. Комиссия компании (теперь фиксированная)
    result.company_commission_rub = settings.fees.company_commission_rub
    
    # 4. Расходы в Китае (теперь фиксированные)
    result.china_expenses_rub = settings.fees.china_expenses_rub
    
    # 5. Расчет таможенных платежей
    if user_data['payer_type'] == 'Физическое лицо':
        result.customs = _calculate_customs_for_individual(user_data, settings)
    else:
        # TODO: Добавить логику для юридических лиц
        pass

    # 6. Расчет итоговой суммы
    result.total_cost_rub = (
        result.car_price_rub +
        result.bank_commission_rub +
        result.company_commission_rub +
        result.china_expenses_rub +
        result.customs.total_customs_rub # Добавляем таможню
    )
    
    return result

def format_result_for_user(result: CalculationResult) -> str:
    """Форматирует результат расчета в красивое сообщение для пользователя."""
    
    def format_rub(value: float) -> str:
        """Вспомогательная функция для форматирования чисел с пробелом и знаком рубля."""
        return f"{value:,.0f}".replace(',', ' ')

    customs_details = (
        f"— Таможенная пошлина: {format_rub(result.customs.duty_rub)} ₽\n"
        f"— Таможенный сбор: {format_rub(result.customs.customs_fee_rub)} ₽\n"
        f"— Утилизационный сбор: {format_rub(result.customs.recycling_fee_rub)} ₽\n"
        f"<b>Итого таможня:</b> {format_rub(result.customs.total_customs_rub)} ₽"
    )

    text = (
        "✅ Расчет готов!\n\n"
        "<b>Платежи по инвойсу:</b>\n"
        f"— Стоимость авто: {format_rub(result.car_price_rub)} ₽\n"
        f"— Комиссия банка: {format_rub(result.bank_commission_rub)} ₽\n"
        f"— Комиссия компании: {format_rub(result.company_commission_rub)} ₽\n"
        f"— Расходы в Китае: {format_rub(result.china_expenses_rub)} ₽\n\n"
        "<b>Таможенные платежи:</b>\n"
        f"{customs_details}\n\n"
        f"<b>ИТОГОВАЯ СТОИМОСТЬ:</b> {format_rub(result.total_cost_rub)} ₽\n\n"
        "🚧 <i>Расчет поможет вам ориентироваться в ценах, но не забывайте об актуальности курсов валют на день покупки. "
        "Уточнить таможенные платежи можете на сайте <a href=\"https://www.tks.ru/auto/calc/\">tks.ru</a></i>"
    )
    return text