from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from core.config import settings
from keyboards import get_main_inline_keyboard

router = Router()

class RequestState(StatesGroup):
    waiting_for_phone = State()
    waiting_for_comment = State()


@router.callback_query(F.data == "main_menu:application")
async def start_request(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс создания заявки."""
    await callback.message.answer(
        "Чтобы оставить заявку, пожалуйста, укажите ваш номер телефона:",
    )
    await state.set_state(RequestState.waiting_for_phone)
    await callback.answer()


@router.message(RequestState.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    """Обрабатывает введенный телефон и запрашивает комментарий."""
    await state.update_data(phone=message.text)
    await message.answer("Спасибо. Если хотите, оставьте комментарий (например, марка и модель авто):")
    await state.set_state(RequestState.waiting_for_comment)


@router.message(RequestState.waiting_for_comment)
async def process_comment(message: Message, state: FSMContext):
    """Обрабатывает комментарий, отправляет заявку и завершает процесс."""
    user_data = await state.get_data()
    user_data['comment'] = message.text
    
    # Формируем сообщение для администратора
    admin_message = (
        f"🔔 Новая заявка!\n\n"
        f"👤 Имя: {message.from_user.full_name}\n"
        f"📞 Телефон: {user_data['phone']}\n"
        f"💬 Комментарий: {user_data['comment']}\n"
        f"TG: @{message.from_user.username} (ID: {message.from_user.id})"
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