from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
import logging

from core.calculator_logic import calculate_total_cost, format_result_for_user
from core.config import settings
import keyboards as kb

router = Router()

# --- Состояния для машины состояний (FSM) ---

class CarCalculationStates(StatesGroup):
    """Состояния для диалога расчета стоимости авто."""
    waiting_for_car_price_cny = State()
    waiting_for_year = State()
    waiting_for_fuel_type = State()
    waiting_for_engine_volume = State()

# --- Клавиатуры ---

def get_fuel_type_keyboard() -> InlineKeyboardMarkup:
    """Возвращает Inline-клавиатуру для выбора типа топлива."""
    buttons = [
        [
            InlineKeyboardButton(text="Бензин", callback_data="fuel_type:Бензин"),
            InlineKeyboardButton(text="Дизель", callback_data="fuel_type:Дизель")
        ],
        [
            InlineKeyboardButton(text="Гибрид", callback_data="fuel_type:Гибрид"),
            InlineKeyboardButton(text="Электро", callback_data="fuel_type:Электро")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_keyboard(placeholder: str | None = None) -> types.ReplyKeyboardMarkup:
    """Возвращает клавиатуру с кнопкой отмены и подсказкой в поле ввода."""
    return types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder=placeholder
    )

# --- Обработчики калькулятора ---

@router.message(F.text == "🚗 Калькулятор")
@router.callback_query(F.data == "main_menu:calculator")
async def start_calculation(message: types.Message | types.CallbackQuery, state: FSMContext):
    """Начинает процесс расчета стоимости автомобиля."""
    # Определяем, что пришло: сообщение или колбэк
    if isinstance(message, types.CallbackQuery):
        msg = message.message
        await message.answer() # Закрываем "часики" на кнопке
    else:
        msg = message

    await state.clear()  # Очищаем предыдущее состояние на случай, если оно было
    # Сразу устанавливаем плательщика по умолчанию
    await state.update_data(payer_type='Физическое лицо')
    await msg.answer(
        "Вы начали расчет стоимости автомобиля из Китая. Укажите стоимость авто в Китае (юани)",
        reply_markup=get_cancel_keyboard(placeholder="Введите стоимость в юанях (CNY)...")
    )
    await state.set_state(CarCalculationStates.waiting_for_car_price_cny)

@router.message(F.text == "❌ Отмена")
async def cancel_calculation(message: types.Message, state: FSMContext):
    """Отменяет текущий процесс расчета в любом состоянии."""
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    is_admin = message.from_user.id in settings.bot.admin_ids
    await message.answer(
        "Расчет отменен.",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await message.answer(
        "Вы вернулись в главное меню.",
        reply_markup=kb.get_main_inline_keyboard(is_admin)
    )

@router.message(CarCalculationStates.waiting_for_car_price_cny)
async def process_car_price(message: types.Message, state: FSMContext):
    """Обрабатывает стоимость авто и запрашивает год выпуска."""
    try:
        price = float(message.text.replace(',', '.').strip())
        if price <= 0:
            raise ValueError("Стоимость должна быть положительной.")
        await state.update_data(car_price_cny=price)
        await message.answer(
            "Стоимость принята. Теперь нужен год выпуска.",
            reply_markup=get_cancel_keyboard(placeholder="Введите год выпуска (например, 2023)...")
        )
        await state.set_state(CarCalculationStates.waiting_for_year)
    except (ValueError, TypeError):
        await message.answer("Пожалуйста, введите корректную стоимость (положительное число).")

@router.message(CarCalculationStates.waiting_for_year)
async def process_year(message: types.Message, state: FSMContext):
    """Обрабатывает год выпуска и запрашивает тип топлива."""
    try:
        year = int(message.text.strip())
        # Простое ограничение для валидации
        if not (1980 < year < 2026):
            raise ValueError("Некорректный год.")
        await state.update_data(year=year)
        # Тип кузова устанавливаем по умолчанию
        await state.update_data(car_body_type='Легковой')
        await message.answer(
            "Выберите тип топлива:",
            reply_markup=get_fuel_type_keyboard()
        )
        await state.set_state(CarCalculationStates.waiting_for_fuel_type)
    except (ValueError, TypeError):
        await message.answer("Пожалуйста, введите корректный год (целое число, например, 2022).")

@router.callback_query(CarCalculationStates.waiting_for_fuel_type, F.data.startswith("fuel_type:"))
async def process_fuel_type(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает тип топлива и запрашивает объем двигателя."""
    fuel_type = callback.data.split(":")[1]
    await state.update_data(fuel_type=fuel_type)

    # Удаляем клавиатуру у предыдущего сообщения
    await callback.message.edit_reply_markup(reply_markup=None)

    # Для электромобилей не нужен объем двигателя
    if fuel_type == "Электро":
        await state.update_data(engine_volume=0) # Ставим 0, чтобы не было ошибок в расчетах
        await state.update_data(engine_power=0)  # Мощность не запрашиваем
        # Сразу переходим к расчету
        await process_and_calculate(callback.message, state)
    else:
        await callback.message.answer(
            f"Тип топлива: {fuel_type}. Теперь нужен объем двигателя.",
            reply_markup=get_cancel_keyboard(placeholder="Введите объем двигателя в см³...")
        )
        await state.set_state(CarCalculationStates.waiting_for_engine_volume)
    await callback.answer() # Отвечаем на колбэк, чтобы убрать "часики" на кнопке

async def process_and_calculate(message: types.Message, state: FSMContext):
    """Общая функция для выполнения расчета и отправки результата."""
    user_data = await state.get_data()
    await state.clear()

    # Сообщаем пользователю, что начали расчет
    calculating_msg = await message.answer("⏳ Выполняю расчет...", reply_markup=ReplyKeyboardRemove())

    try:
        result = calculate_total_cost(user_data=user_data, settings=settings)
        response_text = format_result_for_user(result)
        is_admin = message.from_user.id in settings.bot.admin_ids
        await message.answer(
            response_text,
            parse_mode="HTML",
            reply_markup=kb.get_main_inline_keyboard(is_admin)
        )
    except Exception as e:
        logging.error(f"Ошибка в расчете: {e}", exc_info=True)
        is_admin = message.from_user.id in settings.bot.admin_ids
        await message.answer(
            "Извините, при расчете произошла ошибка. Попробуйте позже или свяжитесь с поддержкой.",
            reply_markup=kb.get_main_inline_keyboard(is_admin)
        )
    finally:
        await calculating_msg.delete()


@router.message(CarCalculationStates.waiting_for_engine_volume)
async def process_engine_volume_and_calculate(message: types.Message, state: FSMContext):
    """Обрабатывает объем двигателя и запускает расчет."""
    try:
        volume = int(message.text.strip())
        if volume <= 0:
            raise ValueError("Объем должен быть положительным.")
        await state.update_data(engine_volume=volume)
        await state.update_data(engine_power=0)  # Мощность не запрашиваем
        
        # Запускаем расчет
        await process_and_calculate(message, state)

    except (ValueError, TypeError):
        await message.answer("Пожалуйста, введите корректный объем (целое положительное число).")