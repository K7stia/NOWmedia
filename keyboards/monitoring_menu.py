from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def monitoring_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📂 Категорії моніторингу", callback_data="monitoring_categories")],
        [InlineKeyboardButton(text="🛠 Автоматизація моніторингу", callback_data="monitoring_automation")],
        [InlineKeyboardButton(text="🔍 Ручний моніторинг", callback_data="manual_monitoring")],
        [InlineKeyboardButton(text="🚀 Запустити сценарій", callback_data="run_scenario")],
        [InlineKeyboardButton(text="⚙️ Модерація та моделі", callback_data="monitoring_config")],
        [InlineKeyboardButton(text="🧾 Журнал моніторингів", callback_data="monitoring_logs")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])

def monitoring_automation_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Створити сценарій", callback_data="create_scenario")],
        [InlineKeyboardButton(text="📋 Переглянути сценарії", callback_data="list_scenarios")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="monitoring_menu")]
    ])

