from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

# --- Текст для FAQ ---
# В будущем это можно вынести в базу данных или YAML-файл для удобного редактирования
FAQ_DATA = {
    "delivery_time": {
        "question": "Сколько времени занимает доставка?",
        "answer": "Стандартные сроки доставки из Китая до нашего склада в Москве составляют 15-25 дней. Сроки могут меняться в зависимости от загруженности таможни и праздничных дней."
    },
    "payment_methods": {
        "question": "Какие способы оплаты вы принимаете?",
        "answer": "Мы принимаем оплату на карту российского банка (Сбер, Тинькофф, Альфа) или через систему быстрых платежей (СБП). Реквизиты предоставляются после подтверждения заказа."
    },
    "guarantees": {
        "question": "Какие у меня гарантии?",
        "answer": "Мы работаем официально и заключаем договор. Весь товар страхуется. В случае утери или повреждения груза мы полностью возмещаем его стоимость. Мы предоставляем фото- и видеоотчет по запросу."
    },
    "what_can_be_delivered": {
        "question": "Что можно и нельзя доставлять?",
        "answer": "Мы доставляем большинство категорий товаров: одежду, обувь, электронику, товары для дома, автозапчасти и многое другое.\n\n<b>Мы не доставляем:</b>\n- Скоропортящиеся продукты\n- Оружие и боеприпасы\n- Наркотические и психотропные вещества\n- Животных и растения"
    }
}

# --- Клавиатуры для FAQ ---

def get_faq_keyboard() -> InlineKeyboardMarkup:
    """Генерирует клавиатуру с вопросами из FAQ_DATA."""
    buttons = []
    for key, data in FAQ_DATA.items():
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
    
    if faq_key in FAQ_DATA:
        question = FAQ_DATA[faq_key]["question"]
        answer = FAQ_DATA[faq_key]["answer"]
        
        # Создаем кнопку "Назад к вопросам"
        back_button = InlineKeyboardButton(text="⬅️ Назад к вопросам", callback_data="back_to_faq")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[back_button]])
        
        # Формируем текст сообщения
        response_text = f"<b>Вопрос:</b> {question}\n\n<b>Ответ:</b> {answer}"
        
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