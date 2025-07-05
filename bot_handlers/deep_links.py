from aiogram import Router, F
from aiogram.filters import CommandObject
from aiogram.filters.command import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from bot_handlers import calculator, faq, request

router = Router()

@router.message(CommandStart(deep_link=True))
async def handle_deep_link(message: Message, command: CommandObject, state: FSMContext):
    """
    Ловит и обрабатывает "глубокие ссылки" (вида /start=payload).
    Перенаправляет пользователя в нужный раздел.
    """
    # Очищаем состояние на случай, если пользователь был в каком-то диалоге
    await state.clear()
    
    payload = command.args
    
    # В aiogram 3 payload передается в command.args
    if payload:
        if payload == "calculator":
            await calculator.start_calculation(message, state)
        elif payload == "faq":
            await faq.show_faq_menu(message)
        elif payload == "application":
            await request.start_request(message, state)
        else:
            # На случай, если в ссылке будет что-то неизвестное
            await message.answer("Неизвестная команда. Выберите действие в меню.")
    else:
        # Если вдруг deep_link сработал, а payload пустой
        await message.answer("Здравствуйте! Выберите действие в меню.") 