from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard(is_admin: bool) -> ReplyKeyboardMarkup:
    """Генерирует основную клавиатуру в зависимости от роли пользователя."""
    buttons = [
        [KeyboardButton(text="🚗 Калькулятор")],
        [KeyboardButton(text="❓ FAQ"), KeyboardButton(text="📝 Оставить заявку")]
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
            InlineKeyboardButton(text="❓ FAQ", callback_data="main_menu:faq"),
            InlineKeyboardButton(text="📝 Оставить заявку", callback_data="main_menu:application")
        ]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="🔧 Админ-панель", callback_data="main_menu:admin")])

    return InlineKeyboardMarkup(inline_keyboard=buttons) 