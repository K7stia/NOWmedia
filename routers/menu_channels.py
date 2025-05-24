from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.state import StatesGroup, State

from utils.json_storage import load_known_media, save_known_media
from states.add_channel import AddChannelState
from utils.telethon_fetcher import resolve_channel_by_username
from states.signature import SignatureState

router = Router()

platform_emojis = {
    "telegram": "📩",
    "facebook": "📘",
    "instagram": "📷",
    "twitter": "🐦"
}

@router.callback_query(F.data == "menu_channels")
async def menu_channels(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Переглянути медіа", callback_data="view_channels")],
        [InlineKeyboardButton(text="➕ Додати Telegram-канал", callback_data="add_channel")],
        [InlineKeyboardButton(text="➕ Додати Facebook паблік", callback_data="add_facebook")],
        [InlineKeyboardButton(text="🔄 Оновити Telegram-канали", callback_data="refresh_channels")],
        [InlineKeyboardButton(text="👥 Групи медіа", callback_data="menu_groups")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])
    await callback.message.edit_text("📡 Оберіть дію для медіа:", reply_markup=kb)


@router.callback_query(F.data == "view_channels")
async def view_channels(callback: CallbackQuery):
    media = load_known_media()
    buttons = []

    for media_id, meta in sorted(media.items()):
        platform = meta.get("platform", "telegram")
        emoji = platform_emojis.get(platform, "❔")
        title = meta.get("title") or meta.get("username") or media_id
        status = "✅" if platform == "telegram" else "📡"
        buttons.append([InlineKeyboardButton(text=f"{status} {emoji} {title}", callback_data=f"channel_menu|{media_id}")])

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_channels")])
    await callback.message.edit_text("🔍 Ваші медіа:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


class AddChannelState(StatesGroup):
    waiting_forward = State()


@router.callback_query(F.data == "add_channel")
async def ask_channel_to_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddChannelState.waiting_forward)
    await callback.message.edit_text("📥 Перешліть повідомлення з Telegram-каналу або надішліть @username / ID / посилання")


@router.message(AddChannelState.waiting_forward)
async def handle_text_add_channel(message: Message, state: FSMContext, bot: Bot):
    raw = message.text.strip() if message.text else ""
    input_data = None
    chat = None
    chat_dict = None

    if message.forward_from_chat:
        chat = message.forward_from_chat
        input_data = str(chat.id)
    elif raw.startswith("https://t.me/"):
        extracted = raw.split("https://t.me/")[-1].split("/")[0]
        input_data = extracted.lstrip("@")
    elif raw.startswith("@"):
        input_data = raw[1:]
    elif raw.startswith("-100") and raw[1:].isdigit():
        input_data = raw

    if not input_data:
        await message.answer("❌ Не вдалося розпізнати канал. Надішліть:\n• @username\n• https://t.me/... \n• ID (-100...)\n• або переслане повідомлення")
        return

    try:
        try:
            chat = await bot.get_chat(input_data)
            member = await bot.get_chat_member(chat.id, bot.id)
            chat_dict = {
                "id": chat.id,
                "username": f"@{chat.username}" if chat.username else None,
                "title": chat.title or f"ID {chat.id}",
                "platform": "telegram"
            }
        except Exception:
            chat_dict = await resolve_channel_by_username(input_data)
            if not chat_dict:
                raise Exception(f"Telethon не зміг знайти @{input_data}")
            chat_dict["platform"] = "telegram"
            member = await bot.get_chat_member(chat_dict["id"], bot.id)

    except Exception as e:
        await message.answer(f"❌ Не вдалося отримати канал: {e}")
        return

    if member.status not in ("administrator", "creator"):
        await message.answer("❌ Бот не є адміністратором у цьому каналі.")
        return

    channel_id = str(chat_dict["id"])
    entry = {
        "id": chat_dict["id"],
        "username": chat_dict.get("username"),
        "title": chat_dict.get("title") or channel_id,
        "platform": "telegram"
    }

    media = load_known_media()
    media[channel_id] = entry
    save_known_media(media)

    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 До списку", callback_data="view_channels")],
        [InlineKeyboardButton(text="🏠 Головне меню", callback_data="back_main")]
    ])
    await message.answer(f"✅ Додано <b>{entry['title']}</b> ({entry['platform']})", parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("channel_menu|"))
async def channel_menu(callback: CallbackQuery):
    channel_id = callback.data.split("|", 1)[1]
    media = load_known_media()
    meta = media.get(channel_id)

    if not meta:
        await callback.message.edit_text("❌ Медіа не знайдено.")
        return

    title = meta.get("title") or meta.get("username") or channel_id
    platform = meta.get("platform", "telegram")
    emoji = platform_emojis.get(platform, "❔")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Видалити", callback_data=f"delete_channel_confirm|{channel_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="view_channels")]
    ])
    await callback.message.edit_text(f"⚙️ Керування:\n<b>{emoji} {title}</b>", parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("delete_channel_confirm|"))
async def confirm_delete_channel(callback: CallbackQuery):
    channel_id = callback.data.split("|", 1)[1]
    media = load_known_media()
    meta = media.get(channel_id)

    title = meta.get("title") or meta.get("username") or channel_id
    emoji = platform_emojis.get(meta.get("platform", ""), "❔")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Так, видалити", callback_data=f"delete_channel_final|{channel_id}")],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="view_channels")]
    ])
    await callback.message.edit_text(f"⚠️ Видалити {emoji} <b>{title}</b>?", parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("delete_channel_final|"))
async def delete_channel_final(callback: CallbackQuery):
    channel_id = callback.data.split("|", 1)[1]
    media = load_known_media()

    if channel_id in media:
        del media[channel_id]
        save_known_media(media)
        await callback.message.edit_text("✅ Успішно видалено.")
    else:
        await callback.message.edit_text("⚠️ Не знайдено.")


@router.callback_query(F.data == "refresh_channels")
async def refresh_channels(callback: CallbackQuery, bot: Bot):
    media = load_known_media()
    updated = {}

    for media_id, meta in media.items():
        if meta.get("platform") != "telegram":
            continue
        try:
            chat = await bot.get_chat(int(media_id))
            member = await bot.get_chat_member(chat.id, bot.id)
            if member.status in ("administrator", "creator"):
                updated[media_id] = {
                    "id": chat.id,
                    "username": f"@{chat.username}" if chat.username else None,
                    "title": chat.title or f"ID {chat.id}",
                    "platform": "telegram"
                }
        except Exception:
            continue

    media.update(updated)
    save_known_media(media)

    count = len(updated)
    text = f"✅ Оновлено: {count} Telegram-канал(и) з правами адміністратора."

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 До меню", callback_data="menu_channels")],
        [InlineKeyboardButton(text="🏠 Головне меню", callback_data="back_main")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)
