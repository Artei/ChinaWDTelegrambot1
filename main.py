import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command, CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BotCommand

from core.config import settings
from core.settings_manager import load_settings
from bot_handlers import calculator, faq, admin, request
import keyboards as kb

# --- ЗАГРУЗКА НАСТРОЕК ПРИ СТАРТЕ ---
# Загружаем настройки из файла. Если файла нет, используются дефолтные.
load_settings()

# Устанавливаем уровень логирования
logging.basicConfig(level=logging.INFO)

# Получаем токен бота из переменных окружения
# На Replit это делается через раздел "Secrets"
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ID администраторов и менеджеров будут храниться здесь
# В реальном проекте их лучше хранить в базе данных или конфиг файле
ADMIN_IDS = [int(admin_id) for admin_id in os.getenv("ADMIN_IDS", "").split(",") if admin_id]
MANAGER_IDS = [int(manager_id) for manager_id in os.getenv("MANAGER_IDS", "").split(",") if manager_id]


async def main():
    """Основная функция для запуска бота."""
    
    if not settings.bot.token:
        logging.critical("Не удалось получить токен бота. Проверьте переменную окружения BOT_TOKEN.")
        return

    # Инициализация бота и диспетчера
    bot = Bot(token=settings.bot.token)
    dp = Dispatcher()

    # Настраиваем кнопку "Меню"
    main_menu_commands = [
        BotCommand(command='/start', description='▶️ Запустить/Перезапустить бота')
    ]
    await bot.set_my_commands(main_menu_commands)

    # --- РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ---
    # Подключаем роутеры из других файлов
    dp.include_router(admin.router) # Админ-роутер должен быть первым, чтобы его фильтры проверялись раньше
    dp.include_router(calculator.router)
    dp.include_router(faq.router)
    dp.include_router(request.router)
    
    # Обработчик команды /start
    @dp.message(CommandStart())
    async def send_welcome(message: types.Message):
        """Отправляет приветственное сообщение с основной клавиатурой."""
        user_id = message.from_user.id
        
        # Проверяем роль пользователя
        # TODO: Вынести логику определения роли в отдельную функцию
        if user_id in settings.bot.admin_ids:
            role = "Администратор"
        else:
            role = "Пользователь"
            
        welcome_text = (
            f"Здравствуйте, {message.from_user.full_name}!\n"
            f"Ваша роль: **{role}**\n\n"
            "Я бот для расчета стоимости импорта автомобилей из Китая.\n"
            "Воспользуйтесь меню для навигации."
        )
        
        keyboard = kb.get_main_inline_keyboard(user_id in settings.bot.admin_ids)
        await message.answer(welcome_text, parse_mode="Markdown", reply_markup=keyboard)

    # ------------------------------------

    # Запуск бота
    try:
        logging.info("Бот запускается...")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    # На Replit, для постоянной работы, нужно будет использовать веб-хуки или keep-alive.
    # Для начала разработки достаточно простого запуска.
    asyncio.run(main())