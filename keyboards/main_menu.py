from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📡 Наші медіа", callback_data="menu_channels")],
        [InlineKeyboardButton(text="🧠 Моніторинг публікацій", callback_data="monitoring_menu")],
        [InlineKeyboardButton(text="📅 Сценарії публікацій", callback_data="post_scenarios")],
        [InlineKeyboardButton(text="📝 Зробити публікацію", callback_data="publish_news")],
        [InlineKeyboardButton(text="⚙️ Управління", callback_data="admin_menu")]
    ])
