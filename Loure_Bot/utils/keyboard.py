from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import INDUSTRIES, TARGETS

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Создать анкету", callback_data='create_profile')],
        [InlineKeyboardButton(text="🔍 Смотреть анкеты", callback_data='view_profiles')]
    ])

def get_industry_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎨 Художник", callback_data='industry_artist')],
        [InlineKeyboardButton(text="✍️ Писатель", callback_data='industry_writer')],
        [InlineKeyboardButton(text="🎵 Музыкант", callback_data='industry_musician')]
    ])

def get_target_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Заказчика", callback_data='target_client'),
            InlineKeyboardButton(text="👥 Аудиторию", callback_data='target_audience')
        ],
        [
            InlineKeyboardButton(text="👨‍👩‍👧‍👦 Команду", callback_data='target_team'),
            InlineKeyboardButton(text="🛠 Исполнителя", callback_data='target_executor')
        ]
    ])

def get_skip_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data='skip_step')]
    ])

def get_cancel_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data='cancel')]
    ])

def get_profile_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data='edit_profile')],
        [InlineKeyboardButton(text="🗑️ Удалить", callback_data='delete_confirm')],
        [InlineKeyboardButton(text="🔍 Смотреть другие", callback_data='view_profiles')]
    ])