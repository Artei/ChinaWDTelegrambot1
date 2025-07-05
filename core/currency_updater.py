import aiohttp
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation

async def fetch_currency_rates():
    """
    Получает актуальные курсы валют (CNY, EUR) с сайта ЦБ РФ.
    Возвращает кортеж (cny_rate, eur_rate) или (None, None) в случае ошибки.
    """
    url = "https://www.cbr.ru/scripts/XML_daily.asp"
    cny_rate = None
    eur_rate = None

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()  # Проверка на ошибки HTTP (4xx, 5xx)
                xml_text = await response.text()
                
                root = ET.fromstring(xml_text)
                
                # Ищем валюты по их кодам: R01375 для CNY, R01239 для EUR
                cny_element = root.find(".//Valute[CharCode='CNY']")
                eur_element = root.find(".//Valute[CharCode='EUR']")
                
                if cny_element is not None:
                    value_str = cny_element.find('Value').text.replace(',', '.')
                    # Курс юаня часто дается за 10 единиц, нужно разделить
                    nominal_str = cny_element.find('Nominal').text
                    cny_rate = Decimal(value_str) / Decimal(nominal_str)

                if eur_element is not None:
                    value_str = eur_element.find('Value').text.replace(',', '.')
                    eur_rate = Decimal(value_str)

                # Возвращаем курсы, округленные до 4 знаков после запятой для точности
                return (
                    float(cny_rate.quantize(Decimal("0.0001"))) if cny_rate else None,
                    float(eur_rate.quantize(Decimal("0.0001"))) if eur_rate else None
                )

    except (aiohttp.ClientError, ET.ParseError, InvalidOperation, AttributeError) as e:
        # Логирование ошибки было бы здесь очень кстати
        print(f"Ошибка при получении курсов валют: {e}")
        return None, None 