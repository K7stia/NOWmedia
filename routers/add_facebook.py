import os
import re
import aiohttp
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from utils.json_storage import load_known_media, save_known_media

router = Router()

class FacebookPageState(StatesGroup):
    waiting_input = State()

@router.callback_query(F.data == "add_facebook")
async def ask_facebook_info(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FacebookPageState.waiting_input)
    await callback.message.edit_text("🔗 Введіть @username або посилання/ID Facebook-сторінки:")

@router.message(FacebookPageState.waiting_input)
async def handle_facebook_input(message: Message, state: FSMContext):
    raw = message.text.strip()
    await state.clear()

    match = re.search(r"(?:facebook\.com/)?@?([\w\.\-]+)", raw)
    if not match:
        await message.answer("❌ Не вдалося розпізнати username або ID. Спробуйте ще раз.")
        return

    username_or_id = match.group(1)

    access_token = os.getenv("FB_PAGE_TOKEN")
    if not access_token:
        await message.answer("❌ FB токен не знайдено в .env")
        return

    url = f"https://graph.facebook.com/v22.0/{username_or_id}?fields=name,id&access_token={access_token}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    err_text = await resp.text()
                    await message.answer(f"❌ Facebook API помилка: {resp.status}\n{err_text}")
                    return
                data = await resp.json()
    except Exception as e:
        await message.answer(f"❌ Помилка при зверненні до Facebook API: {e}")
        return

    fb_id = str(data.get("id"))
    fb_title = data.get("name") or f"ID {fb_id}"

    entry = {
        "id": fb_id,
        "username": f"@{username_or_id}" if not username_or_id.isnumeric() else None,
        "title": fb_title,
        "platform": "facebook"
    }

    media = load_known_media()
    media[fb_id] = entry
    save_known_media(media)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 До списку", callback_data="view_channels")],
        [InlineKeyboardButton(text="🏠 Головне меню", callback_data="back_main")]
    ])

    await message.answer(
        f"✅ Facebook-сторінку <b>{fb_title}</b> збережено.\n"
        f"<code>{fb_id}</code>",
        parse_mode="HTML",
        reply_markup=kb
    )
