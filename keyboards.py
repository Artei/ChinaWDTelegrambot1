from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard(is_admin: bool) -> ReplyKeyboardMarkup:
    """Генерирует основную клавиатуру в зависимости от роли пользователя."""
    buttons = [
        [KeyboardButton(text="🚗 Калькулятор")],
        [KeyboardButton(text="❓ Частые вопросы (FAQ)"), KeyboardButton(text="📝 Оставить заявку")],
        [KeyboardButton(text="👋 Привет")]
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="🔧 Админ-панель")])
    
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    return keyboard

def get_main_inline_keyboard(is_admin: bool) -> InlineKeyboardMarkup:
    """Генерирует основную Inline-клавиатуру."""
    buttons = [
        [InlineKeyboardButton(text="🚗 Калькулятор", callback_data="main_menu:calculator")],
        [
            InlineKeyboardButton(text="❓ Частые вопросы (FAQ)", callback_data="main_menu:faq"),
            InlineKeyboardButton(text="📝 Оставить заявку", callback_data="main_menu:application")
        ],
        [InlineKeyboardButton(text="👋 Привет", callback_data="main_menu:hello")]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="🔧 Админ-панель", callback_data="main_menu:admin")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_main_channel_keyboard() -> InlineKeyboardMarkup:
    """Генерирует Inline-клавиатуру со ссылками для канала."""
    bot_username = "ChinaWD_bot"  # Ваше имя пользователя бота
    buttons = [
        [InlineKeyboardButton(text="🚗 Калькулятор", url=f"https://t.me/{bot_username}?start=calculator")],
        [
            InlineKeyboardButton(text="❓ Частые вопросы (FAQ)", url=f"https://t.me/{bot_username}?start=faq"),
            InlineKeyboardButton(text="📝 Оставить заявку", url=f"https://t.me/{bot_username}?start=application")
        ],
        [InlineKeyboardButton(text="👋 Привет", url=f"https://t.me/{bot_username}?start=hello")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons) 