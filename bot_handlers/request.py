from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from core.config import settings
from keyboards import get_main_inline_keyboard

router = Router()

class RequestState(StatesGroup):
    waiting_for_phone = State()
    waiting_for_comment = State()


def get_phone_request_keyboard() -> ReplyKeyboardMarkup:
    """Создает клавиатуру с кнопкой запроса номера телефона."""
    button = KeyboardButton(
        text="📱 Поделиться номером телефона",
        request_contact=True
    )
    return ReplyKeyboardMarkup(keyboard=[[button]], resize_keyboard=True, one_time_keyboard=True)


@router.callback_query(F.data == "main_menu:application")
async def start_request(message: Message | CallbackQuery, state: FSMContext):
    """Начинает процесс создания заявки, может вызываться и по deep-link."""
    import asyncio
    
    if isinstance(message, CallbackQuery):
        msg = message.message
        await message.answer()  # Закрываем "часики" на кнопке
    else:
        msg = message

    # Сначала отправляем текст без клавиатуры
    await msg.answer(
        "Чтобы оставить заявку, пожалуйста, отправьте ваш номер телефона в сообщении. "
        "Или нажмите на кнопку, которая появится ниже.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Делаем асинхронную паузу
    await asyncio.sleep(4)
    
    # Затем отправляем клавиатуру с подсказкой
    await msg.answer(
        "Нажмите на кнопку ниже 👇",
        reply_markup=get_phone_request_keyboard()
    )

    await state.set_state(RequestState.waiting_for_phone)


@router.message(RequestState.waiting_for_phone, F.contact)
async def process_phone_from_contact(message: Message, state: FSMContext):
    """Обрабатывает номер телефона, полученный через кнопку."""
    await state.update_data(phone=message.contact.phone_number)
    await message.answer(
        "Спасибо! Ваш номер принят.",
        reply_markup=ReplyKeyboardRemove()  # Убираем кастомную клавиатуру
    )
    await message.answer("Теперь оставьте комментарий (например, марка и модель авто):")
    await state.set_state(RequestState.waiting_for_comment)


@router.message(RequestState.waiting_for_phone, F.text)
async def process_phone_from_text(message: Message, state: FSMContext):
    """Обрабатывает номер телефона, введенный как текст."""
    await state.update_data(phone=message.text)
    await message.answer(
        "Спасибо! Ваш номер принят.",
        reply_markup=ReplyKeyboardRemove() # Убираем кастомную клавиатуру
    )
    await message.answer("Теперь оставьте комментарий (например, марка и модель авто):")
    await state.set_state(RequestState.waiting_for_comment)


@router.message(RequestState.waiting_for_comment)
async def process_comment(message: Message, state: FSMContext):
    """Обрабатывает комментарий, отправляет заявку и завершает процесс."""
    user_data = await state.get_data()
    user_data['comment'] = message.text
    
    # ИСПРАВЛЕНИЕ: Корректно обрабатываем случай, когда у пользователя нет username
    user_tg_link = f"@{message.from_user.username}" if message.from_user.username else "не указан"

    # Формируем сообщение для администратора
    admin_message = (
        f"🔔 Новая заявка!\n\n"
        f"👤 Имя: {message.from_user.full_name}\n"
        f"📞 Телефон: {user_data['phone']}\n"
        f"💬 Комментарий: {user_data['comment']}\n"
        f"TG: {user_tg_link} (ID: {message.from_user.id})"
    )
    
    # Отправляем уведомление всем администраторам
    for admin_id in settings.bot.admin_ids:
        try:
            await message.bot.send_message(admin_id, admin_message)
        except Exception as e:
            # В реальном проекте здесь лучше использовать логирование
            print(f"Не удалось отправить уведомление админу {admin_id}: {e}")

    # Благодарим пользователя и возвращаем в главное меню
    await message.answer(
        "✅ Ваша заявка принята! Менеджер скоро с вами свяжется.",
        reply_markup=get_main_inline_keyboard(message.from_user.id in settings.bot.admin_ids)
    )
    
    await state.clear() 