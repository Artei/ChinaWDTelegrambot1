from aiogram import Router, F, types
from aiogram.filters import Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

from core.config import settings
from core.settings_manager import save_settings

class AdminFilter(Filter):
    """Фильтр для проверки, является ли пользователь администратором."""
    async def __call__(self, event: types.TelegramObject, *args, **kwargs) -> bool:
        # Универсальная проверка и для Message, и для CallbackQuery
        user = event.from_user
        return user.id in settings.bot.admin_ids

router = Router()
# Применяем фильтр ко всем обработчикам в этом роутере
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


# --- FSM для изменения настроек ---
class AdminStates(StatesGroup):
    waiting_for_cny_rate = State()
    waiting_for_eur_rate = State()
    # TODO: Добавить состояния для комиссий и прочих сборов


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
        [InlineKeyboardButton(text="Изменить курсы валют", callback_data="admin_set_rates")],
        [InlineKeyboardButton(text="Изменить комиссии и сборы", callback_data="admin_set_fees")],
        [InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin_main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура отмены для админских FSM (инлайн)."""
    buttons = [
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel_action")]
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

@router.message(F.text == "🔧 Админ-панель")
@router.callback_query(F.data == "main_menu:admin")
async def show_admin_menu(message: types.Message | types.CallbackQuery):
    """Показывает главное меню админ-панели."""
    if isinstance(message, types.CallbackQuery):
        msg = message.message
        await message.answer()
    else:
        msg = message
    await msg.answer("Добро пожаловать в панель администратора!", reply_markup=get_admin_main_keyboard())

@router.callback_query(F.data == "admin_main_menu")
async def back_to_admin_menu(callback: types.CallbackQuery):
    """Возвращает в главное меню админки."""
    await callback.message.edit_text("Добро пожаловать в панель администратора!", reply_markup=get_admin_main_keyboard())
    await callback.answer()

@router.callback_query(F.data == "admin_calculator_menu")
async def show_calculator_settings(callback: types.CallbackQuery):
    """Показывает меню настроек калькулятора с текущими значениями."""
    text = _get_calculator_settings_text()
    await callback.message.edit_text(
        text,
        reply_markup=get_calculator_settings_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_cancel_action")
async def cancel_admin_action(callback: types.CallbackQuery, state: FSMContext):
    """Отменяет FSM в админке и возвращает в меню настроек калькулятора."""
    await state.clear()
    await callback.answer("Действие отменено.")
    # Формируем и отправляем меню настроек калькулятора
    text = _get_calculator_settings_text()
    await callback.message.edit_text(
        text,
        reply_markup=get_calculator_settings_keyboard(),
        parse_mode="HTML"
    )

# --- Логика изменения курсов валют ---

@router.callback_query(F.data == "admin_set_rates")
async def start_setting_rates(callback: types.CallbackQuery, state: FSMContext):
    """Начинает диалог изменения курсов валют."""
    await state.clear()
    await callback.message.edit_text(
        "Введите новый курс юаня к рублю...",
        reply_markup=get_admin_cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_cny_rate)
    await callback.answer()

@router.message(AdminStates.waiting_for_cny_rate)
async def process_cny_rate(message: Message, state: FSMContext):
    """Обрабатывает новый курс юаня и запрашивает курс евро."""
    try:
        new_rate = float(message.text.replace(',', '.').strip())
        if new_rate <= 0:
            raise ValueError("Курс должен быть положительным.")
        await state.update_data(cny_rate=new_rate)
        await message.answer(
            "Курс юаня принят. Введите новый курс евро к рублю...",
            reply_markup=get_admin_cancel_keyboard()
        )
        await state.set_state(AdminStates.waiting_for_eur_rate)
    except (ValueError, TypeError):
        await message.answer(
            "❌ Неверный формат. Пожалуйста, введите положительное число (например, `12.5`).",
            reply_markup=get_admin_cancel_keyboard()
        )

@router.message(AdminStates.waiting_for_eur_rate)
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

# TODO: Добавить диалоги для изменения комиссий и таможенных тарифов. 