from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

PLATFORM_EMOJIS = {
    "telegram": "📢",
    "facebook": "📘",
    "instagram": "📸",
    "twitter": "🐦"
}

def monitoring_target_kb(
    groups: dict[str, list],
    channels: dict[str, dict],  # всі медіа акаунти, не лише ТГ
    selected_groups: list[str] = None,
    selected_channels: list[str] = None,
    show_channels: bool = True,
    show_groups: bool = True
) -> InlineKeyboardMarkup:
    selected_groups = selected_groups or []
    selected_channels = selected_channels or []

    buttons = []

    if show_channels:
        for key, info in channels.items():
            mark = "✅" if key in selected_channels else "◾️"
            platform = info.get("platform", "telegram")
            emoji = PLATFORM_EMOJIS.get(platform, "❔")
            title = info.get("title", key)
            buttons.append([
                InlineKeyboardButton(
                    text=f"{mark} {emoji} {title}",
                    callback_data=f"manual_toggle_channel|{key}"
                )
            ])

    if show_groups:
        for group in groups:
            mark = "✅" if group in selected_groups else "◾️"
            buttons.append([
                InlineKeyboardButton(
                    text=f"{mark} {group}",
                    callback_data=f"manual_toggle_group|{group}"
                )
            ])

    buttons.append([InlineKeyboardButton(text="➡️ Підтвердити вибір", callback_data="monitor_proceed_targets")])
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="manual_monitoring"),
        InlineKeyboardButton(text="🏠 Головне меню", callback_data="back_main")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def monitoring_mode_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Вибрати канал(и)", callback_data="monitor_mode|channels")],
        [InlineKeyboardButton(text="🧩 Вибрати групу(и)", callback_data="monitor_mode|groups")],
        [InlineKeyboardButton(text="🔀 Мікс: канали + групи", callback_data="monitor_mode|mix")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="manual_monitoring")]
    ])

def monitoring_options_kb(moderation: bool, rewrite: bool) -> InlineKeyboardMarkup:
    mod_label = "🛡 Модерація: ✅" if moderation else "🛡 Модерація: ❌"
    rew_label = "✍️ Рерайт: ✅" if rewrite else "✍️ Рерайт: ❌"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=mod_label, callback_data="toggle_moderation")],
        [InlineKeyboardButton(text=rew_label, callback_data="toggle_rewrite")],
        [InlineKeyboardButton(text="🚀 Запустити моніторинг", callback_data="manual_monitor_launch")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="manual_monitoring")]
    ])