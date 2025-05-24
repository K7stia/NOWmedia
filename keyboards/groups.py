from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.json_storage import load_known_media, load_groups

def group_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📃 Переглянути групи", callback_data="list_groups")],
        [InlineKeyboardButton(text="➕ Додати групу", callback_data="add_group")],
        [InlineKeyboardButton(text="➖ Видалити групу", callback_data="delete_group")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])

def delete_group_kb(group_names: list[str]) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text=name, callback_data=f"delete_{i}")] for i, name in enumerate(group_names)]
    buttons.append([InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_delete")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def channels_group_kb(group_name: str, mode: str = "selected") -> InlineKeyboardMarkup:
    all_channels = load_known_media()  # Telegram, Facebook, etc.
    groups = load_groups()
    group_channels = groups.get(group_name, [])

    selected_ids = {c["id"] for c in group_channels if isinstance(c, dict)}
    buttons = []

    platform_emojis = {
        "telegram": "📩",
        "facebook": "📘",
        "instagram": "📷",
        "twitter": "🐦"
    }

    for key, info in sorted(all_channels.items()):
        channel_id = info.get("id")
        channel_title = info.get("title") or key
        platform = info.get("platform", "telegram")
        emoji = platform_emojis.get(platform, "")
        is_selected = channel_id in selected_ids
        icon = "✅" if is_selected else "➖"

        if mode == "selected" and not is_selected:
            continue

        buttons.append([
            InlineKeyboardButton(
                text=f"{icon} {emoji} {channel_title}",
                callback_data=f"toggle_group_channel|{key}|{group_name}"
            )
        ])

    control_buttons = []
    if mode == "selected":
        control_buttons.append([
            InlineKeyboardButton(text="➕ Додати ще медіа", callback_data=f"show_all_channels|{group_name}")
        ])

    control_buttons.extend([
        [InlineKeyboardButton(text="✏️ Переіменувати групу", callback_data=f"rename_group|{group_name}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_groups")]
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons + control_buttons)
