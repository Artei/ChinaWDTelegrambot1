import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command, CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web

from core.config import settings
from core.settings_manager import load_settings, save_settings
from bot_handlers import calculator, faq, admin, request, deep_links
import keyboards as kb
from core.currency_updater import fetch_currency_rates


# --- КОД ДЛЯ ВЕБ-СЕРВЕРА (KEEP-ALIVE) ---
async def web_server_handler(request):
    """Обработчик, отвечающий на HTTP-запросы для поддержания активности."""
    logging.info("Получен keep-alive запрос.")
    return web.Response(text="Bot is running!")

async def run_web_server():
    """Запускает фоновый веб-сервер на aiohttp."""
    app = web.Application()
    app.add_routes([web.get('/', web_server_handler)])
    runner = web.AppRunner(app)
    await runner.setup()
    # Порт для хостингов типа Replit обычно берется из переменной окружения
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Веб-сервер для keep-alive запущен на порту {port}")
    # Эта конструкция не даст задаче завершиться и будет ждать вечно
    await asyncio.Event().wait()
# --- КОНЕЦ КОДА ДЛЯ ВЕБ-СЕРВЕРА ---


async def update_and_save_rates():
    """Получает и сохраняет актуальные курсы валют."""
    logging.info("Попытка обновить курсы валют...")
    cny_rate, eur_rate = await fetch_currency_rates()

    if cny_rate and eur_rate:
        settings.rates.cny_to_rub = cny_rate
        settings.rates.eur_to_rub = eur_rate
        save_settings()
        logging.info(f"Курсы валют успешно обновлены: CNY={cny_rate}, EUR={eur_rate}")
    else:
        logging.warning("Не удалось обновить курсы валют. Используются последние сохраненные значения.")


async def main():
    """Основная функция для запуска бота."""
    # --- ЗАГРУЗКА НАСТРОЕК ПРИ СТАРТЕ ---
    load_settings()

    # Устанавливаем уровень логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    
    # Первоначальное обновление курсов при запуске
    await update_and_save_rates()
    
    # Настройка и запуск планировщика
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(update_and_save_rates, 'cron', hour=11, minute=30)
    scheduler.start()

    if not settings.bot.token:
        logging.critical("Не удалось получить токен бота. Проверьте переменную окружения BOT_TOKEN.")
        return

    # Инициализация бота и диспетчера
    bot = Bot(token=settings.bot.token)
    dp = Dispatcher()

    # Настраиваем кнопку "Меню"
    main_menu_commands = [
        BotCommand(command='/start', description='▶️ Запустить/Перезапустить бота'),
        BotCommand(command='/admin', description='Панель администратора')
    ]
    await bot.set_my_commands(main_menu_commands)

    # --- РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ---
    # Подключаем роутеры из других файлов
    dp.include_router(admin.router) # Админ-роутер должен быть первым, чтобы его фильтры проверялись раньше
    # Этот обработчик должен быть зарегистрирован после admin.router, чтобы не перекрывать его фильтры
    @dp.message(Command("admin"))
    async def admin_panel_command(message: types.Message):
        if message.from_user.id in settings.bot.admin_ids:
            await admin.show_admin_menu(message)
        else:
            await message.answer("У вас нет доступа к этой команде.")
            
    dp.include_router(calculator.router)
    dp.include_router(faq.router)
    dp.include_router(request.router)
    dp.include_router(deep_links.router)
    
    # Обработчик команды /start
    @dp.message(CommandStart())
    async def send_welcome(message: types.Message):
        """Отправляет приветственное сообщение с основной клавиатурой."""
        user_id = message.from_user.id
        
        welcome_text = (
            f"Здравствуйте, {message.from_user.full_name}!\n\n"
            "Я ваш личный помощник по заказу автомобилей из Китая. Что мы можем сделать:\n\n"
            "🔹 **Калькулятор:** Есть цена авто в юанях? Давайте посчитаем конечную стоимость в РФ с учетом всех сборов и комиссий.\n\n"
            "🔹 **Связь с менеджером:** Есть вопросы, нужна помощь с выбором, или хотите сделать заказ? Оставьте заявку.\n\n"
            "🔹 **Ответы на вопросы (FAQ):** Узнайте всё о сроках доставки, способах оплаты и гарантиях.\n\n"
            "Выберите нужный раздел в меню ниже 👇"
        )

        if user_id in settings.bot.admin_ids:
            welcome_text += "\n\n*Вы вошли как администратор.*"
        
        keyboard = kb.get_main_inline_keyboard(user_id in settings.bot.admin_ids)
        await message.answer(welcome_text, parse_mode="Markdown", reply_markup=keyboard)

    # ------------------------------------

    # Создаем фоновую задачу для веб-сервера
    web_server_task = asyncio.create_task(run_web_server())

    # Запуск бота
    try:
        logging.info("Бот запускается в режиме long polling...")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()
        # При остановке бота, отменяем и задачу веб-сервера
        web_server_task.cancel()


if __name__ == "__main__":
    # На Replit, для постоянной работы, нужно будет использовать веб-хуки или keep-alive.
    # Для начала разработки достаточно простого запуска.
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")