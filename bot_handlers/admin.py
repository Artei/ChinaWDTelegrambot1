import uuid
import logging
from aiogram import Router, F, types
from aiogram.filters import Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.filters.command import Command

from core.config import settings
from core.faq_manager import load_faq_data, save_faq_data
from core.settings_manager import save_settings
import keyboards as kb

router = Router()
# УБИРАЕМ ГЛОБАЛЬНЫЙ ФИЛЬТР, ТАК КАК ОН МЕШАЕТ channel_post
# router.message.filter(AdminFilter())
# router.callback_query.filter(AdminFilter())


# --- FSM для изменения настроек ---
class AdminStates(StatesGroup):
    waiting_for_cny_rate = State()
    waiting_for_eur_rate = State()
    # Состояния для комиссий и сборов
    waiting_for_bank_commission = State()
    waiting_for_company_commission = State()
    waiting_for_china_expenses = State()
    # Состояния для таможенных пошлин
    waiting_for_duty_rates = State()
    # Состояния для утильсбора
    waiting_for_recycling_fee_under_3 = State()
    waiting_for_recycling_fee_over_3 = State()
    faq_add_question = State()
    faq_add_answer = State()


# --- Клавиатуры для админ-панели ---

def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню админ-панели."""
    buttons = [
        [InlineKeyboardButton(text="💰 Управление калькулятором", callback_data="admin_calculator_menu")],
        [InlineKeyboardButton(text="📝 Управление FAQ", callback_data="admin_faq_menu")],
        # [InlineKeyboardButton(text="📢 Рассылки", callback_data="admin_broadcast_menu")],
        # [InlineKeyboardButton(text="👥 Управление пользователями", callback_data="admin_users_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_calculator_settings_keyboard() -> InlineKeyboardMarkup:
    """Меню настроек калькулятора."""
    buttons = [
        [InlineKeyboardButton(text="Курсы валют", callback_data="admin_set_rates")],
        [InlineKeyboardButton(text="Комиссии и расходы", callback_data="admin_set_fees")],
        [InlineKeyboardButton(text="Таможенные пошлины", callback_data="admin_set_duties")],
        [InlineKeyboardButton(text="Утилизационный сбор", callback_data="admin_set_recycling_fee")],
        [InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin_main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_faq_management_keyboard() -> InlineKeyboardMarkup:
    """Меню управления FAQ."""
    buttons = [
        [InlineKeyboardButton(text="➕ Добавить вопрос", callback_data="faq_add")],
        [InlineKeyboardButton(text="➖ Удалить вопрос", callback_data="faq_delete_list")],
        [InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin_main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_faq_delete_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора FAQ для удаления."""
    faq_data = load_faq_data()
    buttons = []
    for key, data in faq_data.items():
        # Ограничиваем длину текста на кнопке
        question_text = data['question'][:50] + '...' if len(data['question']) > 50 else data['question']
        buttons.append([InlineKeyboardButton(
            text=question_text,
            callback_data=f"faq_delete_confirm_{key}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в меню FAQ", callback_data="admin_faq_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_duty_age_category_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора возрастной категории для редактирования пошлин."""
    buttons = [
        # TODO: Реализовать логику для категории "до 3 лет", она считается иначе
        # [InlineKeyboardButton(text="До 3 лет", callback_data="duty_age_0_3")],
        [InlineKeyboardButton(text="От 3 до 5 лет", callback_data="duty_age_3_5")],
        [InlineKeyboardButton(text="Старше 5 лет", callback_data="duty_age_older_5")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_calculator_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура отмены для админских FSM (инлайн)."""
    buttons = [
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel_action")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_back_and_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопками 'Назад' и 'Отмена'."""
    buttons = [
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_step_back"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel_action")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _get_calculator_settings_text() -> str:
    """Возвращает форматированный текст с текущими настройками калькулятора."""
    return (
        f"⚙️ <b>Настройки калькулятора</b>\n\n"
        f"Текущий курс: `1 ¥ = {settings.rates.cny_to_rub} ₽`\n"
        f"Текущий курс: `1 € = {settings.rates.eur_to_rub} ₽`\n\n"
        f"Комиссия банка: `{settings.fees.bank_commission_rub}`\n"
        f"Комиссия компании: `{settings.fees.company_commission_rub}`\n"
        f"Расходы в Китае: `{settings.fees.china_expenses_cny} ¥`\n"
        f"Таможенный сбор: `{settings.fees.customs_fee_rub} ₽`\n\n"
        "Выберите, что хотите настроить:"
    ).replace(",", " ")

# --- Обработчики админ-панели ---

@router.message(F.text == "🔧 Админ-панель", AdminFilter())
@router.callback_query(F.data == "main_menu:admin", AdminFilter())
async def show_admin_menu(message: types.Message | types.CallbackQuery):
    """Показывает главное меню админ-панели."""
    if isinstance(message, types.CallbackQuery):
        msg = message.message
        await message.answer()
    else:
        msg = message
    await msg.answer("Добро пожаловать в панель администратора!", reply_markup=get_admin_main_keyboard())

@router.callback_query(F.data == "admin_main_menu", AdminFilter())
async def back_to_admin_menu(callback: types.CallbackQuery):
    """Возвращает в главное меню админки."""
    await callback.message.edit_text("Добро пожаловать в панель администратора!", reply_markup=get_admin_main_keyboard())
    await callback.answer()

@router.callback_query(F.data == "admin_calculator_menu", AdminFilter())
async def show_calculator_settings(callback: types.CallbackQuery):
    """Показывает меню настроек калькулятора с текущими значениями."""
    text = _get_calculator_settings_text()
    await callback.message.edit_text(
        text,
        reply_markup=get_calculator_settings_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.in_({"admin_set_fees", "admin_set_recycling_fee"}), AdminFilter())
async def section_in_development(callback: types.CallbackQuery):
    """Заглушка для разделов в разработке."""
    await callback.answer("Этот раздел находится в разработке.", show_alert=True)


@router.callback_query(F.data == "admin_set_duties", AdminFilter())
async def show_duty_age_categories(callback: types.CallbackQuery):
    """Показывает меню выбора возрастной категории для пошлин."""
    await callback.message.edit_text(
        "Выберите возрастную категорию для редактирования таможенных пошлин:",
        reply_markup=get_duty_age_category_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_set_recycling_fee", AdminFilter())
async def start_setting_recycling_fee(callback: types.CallbackQuery, state: FSMContext):
    """Начинает диалог изменения утилизационного сбора."""
    await state.clear()
    await callback.message.edit_text(
        f"Текущий сбор для авто <b>младше 3 лет</b>: `{settings.customs.recycling.under_3_years} ₽`.\n\n"
        "Введите новое значение:",
        reply_markup=get_admin_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_recycling_fee_under_3)
    await callback.answer()

async def _ask_for_recycling_over_3(message: Message, state: FSMContext):
    """Запрашивает сбор для авто старше 3 лет."""
    await message.answer(
        f"Текущий сбор для авто <b>старше 3 лет</b>: `{settings.customs.recycling.over_3_years} ₽`.\n\n"
        "Введите новое значение:",
        reply_markup=get_admin_back_and_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_recycling_fee_over_3)

@router.message(AdminStates.waiting_for_recycling_fee_under_3, AdminFilter())
async def process_recycling_fee_under_3(message: Message, state: FSMContext):
    """Обрабатывает сбор для авто младше 3 лет и запрашивает для старше 3 лет."""
    try:
        fee = float(message.text.replace(',', '.').strip())
        if fee < 0:
            raise ValueError("Сбор не может быть отрицательным.")
        await state.update_data(under_3_years=fee)
        
        await _ask_for_recycling_over_3(message, state)

    except (ValueError, TypeError):
        await message.answer(
            "❌ Неверный формат. Пожалуйста, введите положительное число.",
            reply_markup=get_admin_cancel_keyboard()
        )


@router.message(AdminStates.waiting_for_recycling_fee_over_3, AdminFilter())
async def process_recycling_fee_over_3_and_save(message: Message, state: FSMContext):
    """Обрабатывает второй сбор, сохраняет оба и завершает диалог."""
    try:
        fee_over_3 = float(message.text.replace(',', '.').strip())
        if fee_over_3 < 0:
            raise ValueError("Сбор не может быть отрицательным.")

        data = await state.get_data()
        fee_under_3 = data['under_3_years']
        
        # Обновляем настройки в памяти
        settings.customs.recycling.under_3_years = fee_under_3
        settings.customs.recycling.over_3_years = fee_over_3
        
        save_settings()
        await state.clear()

        await message.answer("✅ <b>Ставки утилизационного сбора успешно обновлены!</b>", parse_mode="HTML")

        text = _get_calculator_settings_text()
        await message.answer(
            text,
            reply_markup=get_calculator_settings_keyboard(),
            parse_mode="HTML"
        )
        
    except (ValueError, TypeError):
        await message.answer(
            "❌ Неверный формат. Пожалуйста, введите положительное число.",
            reply_markup=get_admin_cancel_keyboard()
        )


@router.callback_query(F.data.startswith("duty_age_"), AdminFilter())
async def start_setting_duty_rates(callback: types.CallbackQuery, state: FSMContext):
    """Начинает диалог изменения ставок пошлин для выбранной категории."""
    age_category_key = callback.data.replace("duty_age_", "")
    
    # Получаем соответствующий словарь ставок из настроек
    duty_rates_dict = getattr(settings.customs.duty, age_category_key.replace("-", "_") + "_years", {})
    
    # Форматируем текущие ставки для вывода
    current_rates_str = "\n".join([f"`{vol}: {rate}`" for vol, rate in sorted(duty_rates_dict.items())])
    
    await state.update_data(age_category_key=age_category_key)
    await state.set_state(AdminStates.waiting_for_duty_rates)

    await callback.message.edit_text(
        f"<b>Редактирование пошлин для категории '{age_category_key.replace('_', ' ')}'</b>\n\n"
        f"Текущие ставки (объем до, € за см³):\n{current_rates_str}\n\n"
        "Введите новые ставки в формате `макс_объем:ставка_евро`.\n"
        "Каждая ставка с новой строки. Например:\n"
        "`1000:1.5`\n`1500:1.7`\n`99999:3.6`",
        reply_markup=get_admin_cancel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_duty_rates, AdminFilter())
async def process_duty_rates(message: Message, state: FSMContext):
    """Обрабатывает и сохраняет новые ставки пошлин."""
    new_rates_text = message.text
    data = await state.get_data()
    age_category_key = data.get("age_category_key")

    try:
        new_rates_dict = {}
        lines = new_rates_text.strip().split('\n')
        if not lines or not lines[0]:
            raise ValueError("Ввод не может быть пустым.")
            
        for line in lines:
            if ':' not in line:
                raise ValueError("Каждая строка должна содержать двоеточие.")
            vol_str, rate_str = line.split(':', 1)
            vol = int(vol_str.strip())
            rate = float(rate_str.strip().replace(',', '.'))
            if vol <= 0 or rate < 0:
                raise ValueError("Объем и ставка должны быть положительными.")
            new_rates_dict[vol] = rate
        
        # Обновляем соответствующий словарь в настройках
        age_attr_key = age_category_key.replace("-", "_") + "_years"
        setattr(settings.customs.duty, age_attr_key, new_rates_dict)
        
        save_settings()
        await state.clear()
        
        await message.answer("✅ <b>Ставки таможенных пошлин успешно обновлены!</b>", parse_mode="HTML")

        # Показываем обновленное меню настроек
        text = _get_calculator_settings_text()
        await message.answer(
            text,
            reply_markup=get_calculator_settings_keyboard(),
            parse_mode="HTML"
        )

    except (ValueError, TypeError) as e:
        await message.answer(
            f"❌ Ошибка формата: {e}\n\n"
            "Пожалуйста, используйте формат `макс_объем:ставка_евро`, каждая ставка с новой строки. Например:\n"
            "`1000:1.5`\n`1500:1.7`",
            reply_markup=get_admin_cancel_keyboard()
        )

@router.callback_query(F.data == "admin_step_back", AdminFilter())
async def admin_step_back_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает нажатие кнопки 'Назад' в диалогах."""
    current_state = await state.get_state()
    await callback.answer()

    # --- Диалог изменения курсов ---
    if current_state == AdminStates.waiting_for_eur_rate:
        await start_setting_rates(callback, state)

    # --- Диалог изменения комиссий ---
    elif current_state == AdminStates.waiting_for_company_commission:
        await start_setting_fees(callback, state)
    elif current_state == AdminStates.waiting_for_china_expenses:
        await _ask_for_company_commission(callback.message, state)

    # --- Диалог изменения утильсбора ---
    elif current_state == AdminStates.waiting_for_recycling_fee_over_3:
        await start_setting_recycling_fee(callback, state)
        
    # --- Диалог добавления FAQ ---
    elif current_state == AdminStates.faq_add_answer:
        await start_adding_faq(callback, state)


@router.callback_query(F.data == "admin_cancel_action", AdminFilter())
async def cancel_admin_action(callback: types.CallbackQuery, state: FSMContext):
    """Отменяет FSM в админке и возвращает в предыдущее меню."""
    current_state = await state.get_state()
    await state.clear()
    await callback.answer("Действие отменено.")

    # Простое перенаправление для возврата в нужное меню
    if current_state and 'faq' in current_state:
        faq_data = load_faq_data()
        count = len(faq_data)
        await callback.message.edit_text(
            f"Управление FAQ. Всего вопросов: {count}.\n\nВыберите действие:",
            reply_markup=get_faq_management_keyboard()
        )
    else:
        # Поведение по умолчанию: возврат в меню калькулятора
        text = _get_calculator_settings_text()
        await callback.message.edit_text(
            text,
            reply_markup=get_calculator_settings_keyboard(),
            parse_mode="HTML"
        )


# --- Логика изменения курсов валют ---

@router.callback_query(F.data == "admin_set_rates", AdminFilter())
async def start_setting_rates(callback: types.CallbackQuery, state: FSMContext):
    """Начинает диалог изменения курсов валют."""
    await state.clear()
    await callback.message.edit_text(
        "Введите новый курс юаня к рублю...",
        reply_markup=get_admin_cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_cny_rate)
    await callback.answer()

async def _ask_for_eur_rate(message: Message, state: FSMContext):
    """Отправляет запрос на ввод курса евро."""
    await message.answer(
        "Курс юаня принят. Введите новый курс евро к рублю...",
        reply_markup=get_admin_back_and_cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_eur_rate)

@router.message(AdminStates.waiting_for_cny_rate, AdminFilter())
async def process_cny_rate(message: Message, state: FSMContext):
    """Обрабатывает новый курс юаня и запрашивает курс евро."""
    try:
        new_rate = float(message.text.replace(',', '.').strip())
        if new_rate <= 0:
            raise ValueError("Курс должен быть положительным.")
        await state.update_data(cny_rate=new_rate)
        await _ask_for_eur_rate(message, state)
    except (ValueError, TypeError):
        await message.answer(
            "❌ Неверный формат. Пожалуйста, введите положительное число (например, `12.5`).",
            reply_markup=get_admin_cancel_keyboard()
        )

@router.message(AdminStates.waiting_for_eur_rate, AdminFilter())
async def process_eur_rate_and_save(message: Message, state: FSMContext):
    """Обрабатывает новый курс евро, сохраняет и показывает результат."""
    try:
        new_eur_rate = float(message.text.replace(',', '.').strip())
        if new_eur_rate <= 0:
            raise ValueError("Курс должен быть положительным.")

        data = await state.get_data()
        new_cny_rate = data.get('cny_rate')

        # Обновляем настройки в памяти
        settings.rates.cny_to_rub = new_cny_rate
        settings.rates.eur_to_rub = new_eur_rate
        
        # Сохраняем настройки в файл
        save_settings()

        await state.clear()
        
        await message.answer("✅ <b>Курсы валют успешно обновлены!</b>", parse_mode="HTML")

        # Показываем обновленное меню настроек (отправляем новым сообщением)
        text = _get_calculator_settings_text()
        await message.answer(
            text,
            reply_markup=get_calculator_settings_keyboard(),
            parse_mode="HTML"
        )

    except (ValueError, TypeError):
        await message.answer(
            "❌ Неверный формат. Пожалуйста, введите положительное число (например, `100.0`).",
            reply_markup=get_admin_cancel_keyboard()
        )

# --- Логика изменения комиссий и расходов ---

@router.callback_query(F.data == "admin_set_fees", AdminFilter())
async def start_setting_fees(callback: types.CallbackQuery, state: FSMContext):
    """Начинает диалог изменения комиссий."""
    await state.clear()
    # В качестве примера для ввода процента
    current_percent = settings.fees.bank_commission_percent * 100
    await callback.message.edit_text(
        f"Текущая комиссия банка: `{current_percent:.2f}%`.\n\n"
        f"Введите новую комиссию банка в процентах (например, `2.5`):",
        reply_markup=get_admin_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_bank_commission)
    await callback.answer()

async def _ask_for_company_commission(message: Message, state: FSMContext):
    """Отправляет запрос на ввод комиссии компании."""
    await message.answer(
         f"Текущая комиссия компании: `{settings.fees.company_commission_rub} ₽`.\n\n"
         f"Введите новую фиксированную комиссию компании в рублях:",
         reply_markup=get_admin_back_and_cancel_keyboard(),
         parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_company_commission)

async def _ask_for_china_expenses(message: Message, state: FSMContext):
    """Отправляет запрос на ввод расходов в Китае."""
    await message.answer(
         f"Текущие расходы в Китае: `{settings.fees.china_expenses_rub} ₽`.\n\n"
         f"Введите новую сумму расходов в рублях:",
         reply_markup=get_admin_back_and_cancel_keyboard(),
         parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_china_expenses)

@router.message(AdminStates.waiting_for_bank_commission, AdminFilter())
async def process_bank_commission(message: Message, state: FSMContext):
    """Обрабатывает комиссию банка и запрашивает комиссию компании."""
    try:
        new_percent = float(message.text.replace(',', '.').strip())
        if not (0 <= new_percent <= 100):
            raise ValueError("Процент должен быть от 0 до 100.")
        
        # Сохраняем как долю от единицы
        await state.update_data(bank_commission=new_percent / 100.0)
        await _ask_for_company_commission(message, state)
    except (ValueError, TypeError):
        await message.answer(
            "❌ Неверный формат. Пожалуйста, введите число от 0 до 100 (например, `2.5`).",
            reply_markup=get_admin_cancel_keyboard()
        )


@router.message(AdminStates.waiting_for_company_commission, AdminFilter())
async def process_company_commission(message: Message, state: FSMContext):
    """Обрабатывает комиссию компании и запрашивает расходы в Китае."""
    try:
        new_fee = float(message.text.replace(',', '.').strip())
        if new_fee < 0:
            raise ValueError("Сумма не может быть отрицательной.")
            
        await state.update_data(company_commission=new_fee)
        await _ask_for_china_expenses(message, state)
    except (ValueError, TypeError):
        await message.answer(
            "❌ Неверный формат. Пожалуйста, введите положительное число.",
            reply_markup=get_admin_cancel_keyboard()
        )


@router.message(AdminStates.waiting_for_china_expenses, AdminFilter())
async def process_china_expenses_and_save(message: Message, state: FSMContext):
    """Обрабатывает расходы в Китае, сохраняет все и показывает результат."""
    try:
        new_expenses = float(message.text.replace(',', '.').strip())
        if new_expenses < 0:
            raise ValueError("Сумма не может быть отрицательной.")

        data = await state.get_data()
        
        # Обновляем настройки в памяти
        settings.fees.bank_commission_percent = data['bank_commission']
        settings.fees.company_commission_rub = data['company_commission']
        settings.fees.china_expenses_rub = new_expenses
        
        # Сохраняем настройки в файл
        save_settings()

        await state.clear()
        
        await message.answer("✅ <b>Комиссии и расходы успешно обновлены!</b>", parse_mode="HTML")

        # Показываем обновленное меню настроек
        text = _get_calculator_settings_text()
        await message.answer(
            text,
            reply_markup=get_calculator_settings_keyboard(),
            parse_mode="HTML"
        )

    except (ValueError, TypeError):
        await message.answer(
            "❌ Неверный формат. Пожалуйста, введите положительное число.",
            reply_markup=get_admin_cancel_keyboard()
        )


# --- Управление FAQ ---

@router.callback_query(F.data == "admin_faq_menu", AdminFilter())
async def show_faq_management_menu(callback: types.CallbackQuery, state: FSMContext):
    """Показывает меню управления FAQ."""
    await state.clear()
    faq_data = load_faq_data()
    count = len(faq_data)
    await callback.message.edit_text(
        f"Управление FAQ. Всего вопросов: {count}.\n\nВыберите действие:",
        reply_markup=get_faq_management_keyboard()
    )
    await callback.answer()


# --- Добавление FAQ ---

@router.callback_query(F.data == "faq_add", AdminFilter())
async def start_adding_faq(callback: types.CallbackQuery, state: FSMContext):
    """Начинает процесс добавления нового вопроса."""
    await state.set_state(AdminStates.faq_add_question)
    await callback.message.edit_text(
        "Введите новый вопрос:",
        reply_markup=get_admin_cancel_keyboard()
    )
    await callback.answer()

async def _ask_for_faq_answer(message: Message, state: FSMContext):
    """Запрашивает ответ на вопрос."""
    await message.answer(
        "Вопрос сохранен. Теперь введите ответ:",
        reply_markup=get_admin_back_and_cancel_keyboard()
    )
    await state.set_state(AdminStates.faq_add_answer)

@router.message(AdminStates.faq_add_question, AdminFilter())
async def process_faq_question(message: Message, state: FSMContext):
    """Сохраняет вопрос и запрашивает ответ."""
    await state.update_data(question=message.text)
    await _ask_for_faq_answer(message, state)

@router.message(AdminStates.faq_add_answer, AdminFilter())
async def process_faq_answer(message: Message, state: FSMContext):
    """Сохраняет ответ и завершает процесс."""
    data = await state.get_data()
    question = data.get('question')
    answer = message.text

    faq_data = load_faq_data()
    new_key = str(uuid.uuid4())
    faq_data[new_key] = {"question": question, "answer": answer}
    save_faq_data(faq_data)

    await state.clear()
    await message.answer(
        "✅ Новый вопрос и ответ успешно добавлены в FAQ!",
        parse_mode="HTML"
    )
    
    count = len(faq_data)
    await message.answer(
        f"Управление FAQ. Всего вопросов: {count}.\n\nВыберите действие:",
        reply_markup=get_faq_management_keyboard()
    )


# --- Удаление FAQ ---
@router.callback_query(F.data == "faq_delete_list", AdminFilter())
async def show_faq_delete_list(callback: types.CallbackQuery):
    """Показывает клавиатуру для выбора вопроса для удаления."""
    faq_data = load_faq_data()
    if not faq_data:
        await callback.answer("Список FAQ пуст. Нечего удалять.", show_alert=True)
        return

    await callback.message.edit_text(
        "Выберите вопрос, который хотите удалить:",
        reply_markup=get_faq_delete_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("faq_delete_confirm_"), AdminFilter())
async def confirm_faq_deletion(callback: types.CallbackQuery, state: FSMContext):
    """Запрашивает подтверждение на удаление вопроса."""
    question_id = callback.data.split("_")[-1]

    faq_data = load_faq_data()
    if question_id in faq_data:
        del faq_data[question_id]
        save_faq_data(faq_data)
        await callback.answer("Вопрос удален.", show_alert=True)
    else:
        await callback.answer("Ошибка: вопрос не найден.", show_alert=True)

    faq_data = load_faq_data()
    if not faq_data:
        await callback.message.edit_text(
            f"Управление FAQ. Всего вопросов: 0.\n\nБольше вопросов нет. Выберите действие:",
            reply_markup=get_faq_management_keyboard()
        )
    else:
        await callback.message.edit_text(
            "Выберите вопрос, который хотите удалить:",
            reply_markup=get_faq_delete_keyboard()
        ) 

# --- Handler for sending a welcome message to a channel ---

@router.message(Command("send_welcome"))
@router.channel_post(Command("send_welcome"))
async def send_welcome_to_channel(message: types.Message):
    """
    Отправляет приветственное сообщение с главным меню и фото в чат.
    Проверяет права доступа в зависимости от типа чата.
    """
    # --- Проверка прав доступа ---
    # Для личного чата - проверяем ID пользователя
    if message.chat.type == "private":
        if message.from_user.id not in settings.bot.admin_ids:
            await message.answer("Эта команда доступна только администратору бота.")
            return
    # Для канала - проверяем ID канала
    elif message.chat.type == "channel":
        if message.chat.id != settings.bot.trusted_channel_id:
            logging.info(f"Ignoring /send_welcome from untrusted channel {message.chat.id}")
            return
    # В других типах чатов (группах) команду не выполняем
    else:
        return

    welcome_text = (
        "**Добро пожаловать на канал ChinaWD!**\n\n"
        "Я ваш личный помощник по заказу автомобилей из Китая. Что мы можем сделать:\n\n"
        "🔹 **Калькулятор:** Есть цена авто в юанях? Давайте посчитаем конечную стоимость в РФ с учетом всех сборов и комиссий.\n\n"
        "🔹 **Связь с менеджером:** Есть вопросы, нужна помощь с выбором, или хотите сделать заказ? Оставьте заявку.\n\n"
        "🔹 **Ответы на вопросы (FAQ):** Узнайте всё о сроках доставки, способах оплаты и гарантиях.\n\n"
        "Выберите нужный раздел в меню ниже 👇"
    )

    # Получаем клавиатуру со ссылками для канала
    keyboard = kb.get_main_channel_keyboard()
    
    try:
        # Получаем фото профиля бота
        profile_photos = await message.bot.get_user_profile_photos(message.bot.id)
        if not profile_photos or not profile_photos.photos:
             raise ValueError("Bot has no profile photo")
             
        # Берем file_id самой большой фотографии
        photo_id = profile_photos.photos[0][-1].file_id
        
        # Отправляем фото с текстом в качестве подписи
        await message.answer_photo(
            photo=photo_id,
            caption=welcome_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception as e:
        logging.info(f"Cannot send welcome photo, sending text instead: {e}")
        # Если фото нет или ошибка, отправляем просто текст
        await message.answer(welcome_text, parse_mode="Markdown", reply_markup=keyboard)

    # Удаляем исходное сообщение с командой, чтобы не засорять чат
    try:
        await message.delete()
    except Exception:
        # Не удалось удалить (нет прав или личный чат), просто игнорируем
        pass 