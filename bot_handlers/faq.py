from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.faq_manager import load_faq_data

router = Router()

# --- Клавиатуры для FAQ ---

def get_faq_keyboard() -> InlineKeyboardMarkup:
    """Генерирует клавиатуру с вопросами из FAQ_DATA."""
    buttons = []
    faq_data = load_faq_data()
    for key, data in faq_data.items():
        buttons.append([InlineKeyboardButton(text=data["question"], callback_data=f"faq_{key}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- Обработчики FAQ ---

@router.message(F.text == "❓ FAQ")
@router.callback_query(F.data == "main_menu:faq")
async def show_faq_menu(message: types.Message | types.CallbackQuery):
    """Отправляет меню с вопросами FAQ."""
    if isinstance(message, types.CallbackQuery):
        # Если это колбэк, редактируем текущее сообщение, чтобы было красивее
        await message.message.edit_text(
            "Часто задаваемые вопросы. Выберите вопрос, чтобы увидеть ответ:",
            reply_markup=get_faq_keyboard()
        )
        await message.answer()
    else:
        # Если это текстовая команда, отправляем новое сообщение
        await message.answer(
            "Часто задаваемые вопросы. Выберите вопрос, чтобы увидеть ответ:",
            reply_markup=get_faq_keyboard()
        )

@router.callback_query(F.data.startswith("faq_"))
async def show_faq_answer(callback: types.CallbackQuery):
    """Показывает ответ на выбранный вопрос и кнопку 'Назад'."""
    faq_key = callback.data.split("_", 1)[1]
    faq_data = load_faq_data()
    
    if faq_key in faq_data:
        question = faq_data[faq_key]["question"]
        answer = faq_data[faq_key]["answer"]
        
        # Создаем кнопку "Назад к вопросам"
        back_button = InlineKeyboardButton(text="⬅️ Назад к вопросам", callback_data="back_to_faq")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[back_button]])
        
        # Формируем текст сообщения
        response_text = f"<b>Вопрос:</b> {question}\n\n<b>Ответ:</b>\n{answer}"
        
        await callback.message.edit_text(response_text, reply_markup=keyboard, parse_mode="HTML")
    
    await callback.answer()

@router.callback_query(F.data == "back_to_faq")
async def back_to_faq_menu(callback: types.CallbackQuery):
    """Обрабатывает нажатие кнопки 'Назад к вопросам'."""
    await callback.message.edit_text(
        "Часто задаваемые вопросы. Выберите вопрос, чтобы увидеть ответ:",
        reply_markup=get_faq_keyboard()
    )
    await callback.answer() 