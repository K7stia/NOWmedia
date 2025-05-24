from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.json_storage import load_monitoring_groups

def get_category_keyboard():
    groups = load_monitoring_groups()
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=name, callback_data=f"manual_select_category|{name}")]
            for name in sorted(groups.keys())
        ] + [[InlineKeyboardButton(text="◀️ Назад", callback_data="monitoring_menu")]]
    )

def get_model_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Популярне", callback_data="manual_model|popular")],
        [InlineKeyboardButton(text="🕒 Найновіше", callback_data="manual_model|latest")],
        [InlineKeyboardButton(text="📈 Тренд", callback_data="manual_model|trending")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="manual_monitoring")]
    ])

def get_channel_settings_keyboard(category: str, channel_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✂️ Змінити кількість рядків", callback_data=f"change_lines|{category}|{channel_id}")],
        [InlineKeyboardButton(text="🧹 Змінити фрази", callback_data=f"change_phrases|{category}|{channel_id}")],
        [InlineKeyboardButton(text="🗑 Видалити канал", callback_data=f"confirm_remove_channel|{category}|{channel_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"list_cat_channels|{category}")]
    ])