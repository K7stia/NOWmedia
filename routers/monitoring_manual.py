import html
import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from aiogram.fsm.context import FSMContext

from states.monitoring_states import ManualMonitorState
from keyboards.monitoring_keyboards import get_category_keyboard, get_model_keyboard
from keyboards.monitoring import monitoring_mode_kb, monitoring_target_kb, monitoring_options_kb
from utils.json_storage import (
    load_monitoring_groups,
    load_config,
    load_known_media,
    load_groups,
    get_trim_settings
)
from utils.monitoring_utils import build_media_targets, build_full_caption
from utils.rewrite import rewrite_text
from routers.monitoring_moderation import send_post_to_moderation
from monitoring_models import model_registry
from utils.telethon_fetcher import forward_post_to_staging
from utils.facebook_publisher import post_to_facebook_text, post_to_facebook_with_image

router = Router()

@router.callback_query(F.data == "manual_monitoring")
async def manual_monitoring_entry(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ManualMonitorState.selecting_category)
    await callback.message.edit_text("📂 Виберіть категорію моніторингу:", reply_markup=get_category_keyboard())

@router.callback_query(F.data.startswith("manual_select_category|"))
async def manual_select_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split("|", 1)[1]
    await state.update_data(category=category)
    await state.set_state(ManualMonitorState.selecting_model)
    await callback.message.edit_text(
        f"🧠 Обрано категорію: <b>{category}</b>\n\nВиберіть модель моніторингу:",
        reply_markup=get_model_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("manual_model|"))
async def manual_model_selected(callback: CallbackQuery, state: FSMContext):
    model = callback.data.split("|", 1)[1]
    await state.update_data(model=model)
    await state.set_state(ManualMonitorState.selecting_publish_mode)
    await callback.message.edit_text("Оберіть куди публікувати результати моніторингу:", reply_markup=monitoring_mode_kb())

@router.callback_query(F.data.startswith("monitor_mode|"))
async def monitor_select_mode(callback: CallbackQuery, state: FSMContext):
    mode = callback.data.split("|", 1)[1]
    groups = load_groups()
    media = load_known_media()
    await state.update_data({"selected_channels": [], "selected_groups": [], "publish_mode": mode})

    if mode == "channels" and not media:
        await callback.answer("❗️ Немає доступних акаунтів.", show_alert=True)
        return
    if mode == "groups" and not groups:
        await callback.answer("❗️ Немає доступних груп.", show_alert=True)
        return
    if mode == "mix" and not groups and not media:
        await callback.answer("❗️ Немає каналів або груп для вибору.", show_alert=True)
        return

    await state.set_state(ManualMonitorState.selecting_targets)
    await callback.message.edit_text("Оберіть куди публікувати:", reply_markup=monitoring_target_kb(
        channels=media if mode != "groups" else {},
        groups=groups if mode != "channels" else {},
        selected_channels=[],
        selected_groups=[],
        show_channels=(mode in ["channels", "mix"]),
        show_groups=(mode in ["groups", "mix"])
    ))

@router.callback_query(F.data == "monitor_proceed_targets")
async def proceed_to_monitoring_settings(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ManualMonitorState.toggle_moderation)
    await state.update_data(moderation=False, rewrite=False)
    data = await state.get_data()
    await callback.message.edit_text(
        "🛠 Налаштування перед запуском:",
        reply_markup=monitoring_options_kb(
            data.get("moderation", False),
            data.get("rewrite", False)
        )
    )

@router.callback_query(F.data == "toggle_moderation")
async def toggle_moderation(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    new_val = not data.get("moderation", False)
    await state.update_data(moderation=new_val)
    await callback.message.edit_reply_markup(reply_markup=monitoring_options_kb(new_val, data.get("rewrite", False)))
    await callback.answer()

@router.callback_query(F.data == "toggle_rewrite")
async def toggle_rewrite(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    new_val = not data.get("rewrite", False)
    await state.update_data(rewrite=new_val)
    await callback.message.edit_reply_markup(reply_markup=monitoring_options_kb(data.get("moderation", False), new_val))
    await callback.answer()

@router.callback_query(F.data == "manual_monitor_launch")
async def manual_monitor_launch(callback: CallbackQuery, state: FSMContext, bot: Bot):
    logging.debug("✅ manual_monitor_launch TRIGGERED")

    data = await state.get_data()
    logging.debug(f"✅ FSM DATA: {data}")
    await state.clear()

    category = data.get('category')
    model = data.get('model')
    moderation = data.get('moderation', False)
    rewrite = data.get('rewrite', False)

    if not category or not model:
        await callback.message.edit_text("❗️Помилка: відсутні необхідні дані для запуску моніторингу.")
        return

    groups_data = load_groups()
    known_media = load_known_media()
    media_targets = build_media_targets(data, known_media, groups_data)

    if not media_targets:
        await callback.message.edit_text(
            "❗️Не вдалося знайти жодного акаунта для публікації.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Спробувати ще раз", callback_data="manual_monitoring")],
                [InlineKeyboardButton(text="🏠 У головне меню", callback_data="back_main")]
            ])
        )
        return

    sources = load_monitoring_groups().get(category, {}).get('channels', [])
    posts = await model_registry[model](sources)

    if not posts:
        await callback.message.edit_text("❌ Не вдалося отримати жодної публікації.")
        return

    top = posts[0]
    logging.debug(f"[manual_monitor_launch] 📤 Before forward_post_to_staging:\n{top}")

    try:
        top["category"] = category
        top = await forward_post_to_staging(top, bot)  # передаємо bot явно
        logging.warning(f"[manual_monitor_launch] post after staging:\n{top}")
    except Exception as e:
        logging.error(f"[manual_monitor_launch] ❌ forward_post_to_staging failed: {e}")
        await callback.message.edit_text("❌ Помилка при пересиланні в staging-канал.")
        return

    if not top or not top.get("html_text"):
        await callback.message.edit_text("❌ Не вдалося отримати текст з поста.")
        return

    if rewrite:
        style = load_config().get("rewrite_style", "Перефразуй цей текст для Telegram-каналу")
        top["html_text"] = await rewrite_text(top["html_text"], style)
        if top["html_text"].startswith("[❗️Помилка рерайту"):
            await callback.message.edit_text("❌ Помилка рерайту. Моніторинг скасовано.")
            return

    if moderation:
        await send_post_to_moderation(bot, top, "(група/канали)", category, model)
        await callback.message.edit_text("📨 Пост надіслано на модерацію")
        return

    success = 0
    failed = []

    for media in media_targets:
        chat_id = media["id"]
        title = media["title"]
        platform = media.get("platform", "telegram")
        try:
            if platform == "telegram":
                full_caption = build_full_caption(top["html_text"], chat_id)
                media_type = top.get("media_type", "text")
                from_chat_id = top.get("from_chat_id")

                if media_type == "photo":
                    forwarded = await bot.forward_message(from_chat_id=from_chat_id, message_id=top["message_id"], chat_id=callback.from_user.id)
                    await bot.send_photo(chat_id, photo=forwarded.photo[-1].file_id, caption=full_caption, parse_mode="HTML")
                    await bot.delete_message(callback.from_user.id, forwarded.message_id)
                elif media_type == "video":
                    forwarded = await bot.forward_message(from_chat_id=from_chat_id, message_id=top["message_id"], chat_id=callback.from_user.id)
                    await bot.send_video(chat_id, video=forwarded.video.file_id, caption=full_caption, parse_mode="HTML")
                    await bot.delete_message(callback.from_user.id, forwarded.message_id)
                else:
                    await bot.send_message(chat_id, text=full_caption, parse_mode="HTML", disable_web_page_preview=True)

            elif platform == "facebook":
                fb_text = top["html_text"]
                media_type = top.get("media_type", "text")
                fb_result = None

                if media_type == "photo" and top.get("photo_url"):
                    fb_result = post_to_facebook_with_image(fb_text, top["photo_url"])
                else:
                    fb_result = post_to_facebook_text(fb_text)

                if "id" not in fb_result:
                    raise Exception(f"Facebook post failed: {fb_result}")

            success += 1

        except Exception as e:
            logging.error(f"❌ Не вдалося опублікувати до {title} ({platform}): {e}")
            failed.append(title)

    preview = html.escape(top.get("text", "")[:100])
    summary = (
        f"✅ Моніторинг завершено\n\n"
        f"Категорія: <b>{category}</b>\n"
        f"Модель: <b>{model}</b>\n"
        f"Модерація: {'✅' if moderation else '❌'}\n"
        f"Рерайт: {'✅' if rewrite else '❌'}\n\n"
        f"🔝 Топ-публікація:\n{preview}...\n\n"
        f"Успішно: {success} | Помилки: {len(failed)}"
    )
    if failed:
        summary += f"\nНе вдалося: {', '.join(map(html.escape, failed))}"

    await callback.message.edit_text(summary, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📡 Запустити ще раз", callback_data="manual_monitoring")],
        [InlineKeyboardButton(text="🏠 На головну", callback_data="back_main")]
    ]))

@router.callback_query(F.data.startswith("manual_toggle_channel|"))
async def toggle_channel(callback: CallbackQuery, state: FSMContext):
    channel = callback.data.split("|", 1)[1]
    data = await state.get_data()
    selected_channels = set(data.get("selected_channels", []))
    selected_groups = set(data.get("selected_groups", []))
    mode = data.get("publish_mode", "mix")

    if channel in selected_channels:
        selected_channels.remove(channel)
    else:
        selected_channels.add(channel)

    await state.update_data(selected_channels=list(selected_channels))
    await callback.message.edit_reply_markup(reply_markup=monitoring_target_kb(
        channels=load_known_media() if mode != "groups" else {},
        groups=load_groups() if mode != "channels" else {},
        selected_channels=selected_channels,
        selected_groups=selected_groups,
        show_channels=(mode in ["channels", "mix"]),
        show_groups=(mode in ["groups", "mix"])
    ))
    await callback.answer()

@router.callback_query(F.data.startswith("manual_toggle_group|"))
async def toggle_group(callback: CallbackQuery, state: FSMContext):
    group = callback.data.split("|", 1)[1]
    data = await state.get_data()
    selected_groups = set(data.get("selected_groups", []))
    selected_channels = set(data.get("selected_channels", []))
    mode = data.get("publish_mode", "mix")

    if group in selected_groups:
        selected_groups.remove(group)
    else:
        selected_groups.add(group)

    await state.update_data(selected_groups=list(selected_groups))
    await callback.message.edit_reply_markup(reply_markup=monitoring_target_kb(
        channels=load_known_media() if mode != "groups" else {},
        groups=load_groups() if mode != "channels" else {},
        selected_channels=selected_channels,
        selected_groups=selected_groups,
        show_channels=(mode in ["channels", "mix"]),
        show_groups=(mode in ["groups", "mix"])
    ))
    await callback.answer()
