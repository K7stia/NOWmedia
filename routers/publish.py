import logging, html
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from states.publish import PublishNews
from keyboards.publish import publish_target_kb, publish_options_kb, publish_mode_kb
from utils.json_storage import load_groups, load_known_media, load_channel_signature
from utils.monitoring_utils import build_media_targets
from utils.facebook_publisher import post_to_facebook_text, post_to_facebook_with_image
from utils.media_helper import download_file_and_get_url  # забезпечує посилання на фото

router = Router()

@router.callback_query(F.data == "publish_news")
async def cb_publish_news(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Оберіть режим публікації:", reply_markup=publish_mode_kb())

@router.callback_query(F.data.startswith("select_mode|"))
async def cb_select_mode(callback: CallbackQuery, state: FSMContext):
    mode = callback.data.split("|", 1)[1]
    groups = load_groups()
    media = load_known_media()
    await state.set_data({"selected_channels": [], "selected_groups": [], "publish_mode": mode})

    if mode == "channels":
        if not media:
            await callback.answer("❗️ Немає медіа для публікації.", show_alert=True)
            return
        await callback.message.edit_text("Оберіть канал(и):", reply_markup=publish_target_kb(channels=media, groups={}, selected_channels=[], selected_groups=[], show_channels=True, show_groups=False))

    elif mode == "groups":
        if not groups:
            await callback.answer("❗️ Немає доступних груп.", show_alert=True)
            return
        await callback.message.edit_text("Оберіть групу(и):", reply_markup=publish_target_kb(channels={}, groups=groups, selected_channels=[], selected_groups=[], show_channels=False, show_groups=True))

    else:  # mix
        if not groups and not media:
            await callback.answer("❗️ Немає каналів або груп для вибору.", show_alert=True)
            return
        await callback.message.edit_text("Оберіть місця для публікації:", reply_markup=publish_target_kb(channels=media, groups=groups, selected_channels=[], selected_groups=[], show_channels=True, show_groups=True))

@router.callback_query(F.data.startswith("toggle_group|"))
async def toggle_group(callback: CallbackQuery, state: FSMContext):
    group_name = callback.data.split("|", 1)[1]
    data = await state.get_data()
    selected_groups = set(data.get("selected_groups", []))
    selected_channels = set(data.get("selected_channels", []))
    publish_mode = data.get("publish_mode", "mix")

    if group_name in selected_groups:
        selected_groups.remove(group_name)
    else:
        selected_groups.add(group_name)

    await state.update_data(selected_groups=list(selected_groups))
    await callback.message.edit_reply_markup(reply_markup=publish_target_kb(
        channels=load_known_media() if publish_mode != "groups" else {},
        groups=load_groups() if publish_mode != "channels" else {},
        selected_channels=selected_channels,
        selected_groups=selected_groups,
        show_channels=(publish_mode in ["channels", "mix"]),
        show_groups=(publish_mode in ["groups", "mix"])
    ))
    await callback.answer()

@router.callback_query(F.data.startswith("toggle_channel|"))
async def toggle_channel(callback: CallbackQuery, state: FSMContext):
    channel = callback.data.split("|", 1)[1]
    data = await state.get_data()
    selected_channels = set(data.get("selected_channels", []))
    selected_groups = set(data.get("selected_groups", []))
    publish_mode = data.get("publish_mode", "mix")

    if channel in selected_channels:
        selected_channels.remove(channel)
    else:
        selected_channels.add(channel)

    await state.update_data(selected_channels=list(selected_channels))
    await callback.message.edit_reply_markup(reply_markup=publish_target_kb(
        channels=load_known_media() if publish_mode != "groups" else {},
        groups=load_groups() if publish_mode != "channels" else {},
        selected_channels=selected_channels,
        selected_groups=selected_groups,
        show_channels=(publish_mode in ["channels", "mix"]),
        show_groups=(publish_mode in ["groups", "mix"])
    ))
    await callback.answer()

@router.callback_query(F.data == "proceed_to_content")
async def proceed_to_content(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    groups = load_groups()
    known = load_known_media()
    media_targets = build_media_targets(data, known, groups)
    await state.update_data(channels=media_targets, use_signature=True, sound_on=True)
    await state.set_state(PublishNews.waiting_content)
    await callback.message.edit_text("Відправте новину для публікації. Це може бути текст або фото. Для скасування натисніть /cancel")

@router.message(PublishNews.waiting_content)
async def handle_content(message: Message, state: FSMContext, bot: Bot):
    data_to_store = {}
    if message.text and not any([message.photo, message.video, message.document, message.animation, message.audio]):
        data_to_store["text"] = message.html_text or ""
    elif message.photo:
        data_to_store["photo_file_id"] = message.photo[-1].file_id
        if message.caption:
            data_to_store["caption"] = message.html_text
    else:
        await message.answer("❗️ Підтримуються лише текст або фото для публікацій.")
        return

    await state.update_data(**data_to_store)
    opts = await state.get_data()
    await state.set_state(PublishNews.waiting_options)
    await message.answer("Налаштування перед публікацією:", reply_markup=publish_options_kb(opts.get("sound_on", True), opts.get("use_signature", False)))

@router.callback_query(PublishNews.waiting_options, F.data == "toggle_sound")
async def cb_toggle_sound(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    new_val = not data.get("sound_on", True)
    await state.update_data(sound_on=new_val)
    await callback.message.edit_reply_markup(reply_markup=publish_options_kb(new_val, data.get("use_signature", False)))
    await callback.answer()

@router.callback_query(PublishNews.waiting_options, F.data == "toggle_signature")
async def cb_toggle_signature(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    new_val = not data.get("use_signature", False)
    await state.update_data(use_signature=new_val)
    await callback.message.edit_reply_markup(reply_markup=publish_options_kb(data.get("sound_on", True), new_val))
    await callback.answer()

@router.callback_query(PublishNews.waiting_options, F.data == "publish_now")
async def cb_publish_now(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    targets = data.get("channels", [])
    use_signature = data.get("use_signature", False)
    text = data.get("text") or data.get("caption") or ""
    media_url = ""

    # Додаємо підпис для Telegram
    if use_signature:
        for ch in targets:
            if ch["platform"] == "telegram":
                sig = load_channel_signature(ch["id"])
                if sig.get("enabled", True) and sig.get("signature"):
                    text += f"\n\n{sig['signature']}"
                    break

    # Якщо фото — отримуємо URL
    if "photo_file_id" in data:
        try:
            media_url = await download_file_and_get_url(bot, data["photo_file_id"])
        except Exception as e:
            logging.error(f"[publish_now] ❌ download_file_and_get_url failed: {e}")

    success, failed = 0, []
    for ch in targets:
        try:
            if ch["platform"] == "telegram":
                if "text" in data:
                    await bot.send_message(chat_id=ch["id"], text=text, parse_mode="HTML", disable_web_page_preview=True)
                elif "photo_file_id" in data:
                    await bot.send_photo(chat_id=ch["id"], photo=data["photo_file_id"], caption=text, parse_mode="HTML")

            elif ch["platform"] == "facebook":
                if media_url:
                    post_to_facebook_with_image(text, media_url)
                else:
                    post_to_facebook_text(text)

            success += 1
        except Exception as e:
            logging.error(f"❌ Не вдалося надіслати до {ch['title']}: {e}")
            failed.append(ch["title"])

    await state.clear()
    summary = f"✅ Успішно: {success} | ❌ Помилки: {len(failed)}"
    if failed:
        summary += f"\nНе вдалося: {', '.join(failed)}"

    await callback.message.edit_text(summary, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Ще одна публікація", callback_data="publish_news")],
        [InlineKeyboardButton(text="🏠 Головне меню", callback_data="back_main")]
    ]))
