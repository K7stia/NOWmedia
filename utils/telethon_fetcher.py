import os
import time
from html import escape
from collections import defaultdict
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.custom.message import Message
from telethon.tl.types import MessageEntityBold, MessageEntityItalic, Channel
from utils.json_storage import load_monitoring_groups

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("TELETHON_SESSION")
STAGING_CHANNEL_ID = -1002651113048  # staging-канал
POST_LIMIT = 20

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

def compute_score(msg: Message) -> float:
    if not msg.views:
        return 0
    age_minutes = max((time.time() - msg.date.timestamp()) / 60, 1)
    return msg.views / age_minutes

def telethon_to_html_safe(msg: Message) -> str:
    text = msg.message or ""
    entities = msg.entities or []

    chars = list(text)
    inserts = {}

    for entity in entities:
        start = entity.offset
        end = entity.offset + entity.length
        if start >= len(chars) or end > len(chars):
            continue

        open_tag, close_tag = "", ""
        if isinstance(entity, MessageEntityBold):
            open_tag, close_tag = "<b>", "</b>"
        elif isinstance(entity, MessageEntityItalic):
            open_tag, close_tag = "<i>", "</i>"
        else:
            continue

        inserts.setdefault(start, []).append(open_tag)
        inserts.setdefault(end, []).insert(0, close_tag)

    result = ""
    for i in range(len(chars)):
        if i in inserts:
            result += "".join(inserts[i])
        result += escape(chars[i])
    if len(chars) in inserts:
        result += "".join(inserts[len(chars)])

    return result

def get_trim_settings(category: str, src_id: int) -> dict:
    groups = load_monitoring_groups()
    category_data = groups.get(category)
    if not category_data:
        return {}

    for ch in category_data.get("channels", []):
        if ch.get("id") == src_id:
            return {
                "lines_to_trim": ch.get("lines_to_trim", 0),
                "trim_phrases": ch.get("trim_phrases", [])
            }

    return {}

def to_telegram_channel_id(raw_id: int) -> int:
    return -1 * (1000000000000 + abs(raw_id))

async def forward_post_to_staging(post: dict, bot) -> dict:
    await client.start()
    try:
        entity = await client.get_entity(post["channel_id"])
        original_chat_id = entity.id if hasattr(entity, "id") else post["channel_id"]

        if post["media_type"] == "album":
            # 🟡 Альбоми в Facebook поки не підтримуються
            return {}

        # 🔁 Forward single message
        msg = await client.forward_messages(
            entity=STAGING_CHANNEL_ID,
            messages=post["original_msg_id"],
            from_peer=entity
        )
        post["from_chat_id"] = STAGING_CHANNEL_ID
        post["original_chat_id"] = original_chat_id
        post["message_id"] = msg.id

        # ✅ Отримуємо фото без збереження на диск
        if post["media_type"] == "photo" and msg.photo:
            buffer = io.BytesIO()
            await client.download_media(msg.photo, file=buffer)
            buffer.seek(0)
            post["photo_url"] = await download_file_and_get_url(bot=bot, file_stream=buffer)

        # 🧾 Отримуємо HTML-текст
        html_text = telethon_to_html_safe(msg)
        text_lines = html_text.strip().splitlines()

        # ✂️ Обрізання підпису
        channel_id_for_trim = to_telegram_channel_id(original_chat_id)
        settings = get_trim_settings(post.get("category", ""), channel_id_for_trim)
        trim_count = settings.get("lines_to_trim", 0)
        phrases = settings.get("trim_phrases", [])
        if trim_count > 0 and phrases and len(text_lines) >= trim_count:
            last_lines = "\n".join(text_lines[-trim_count:])
            if any(p.lower() in last_lines.lower() for p in phrases):
                text_lines = text_lines[:-trim_count]

        post["html_text"] = "\n".join(text_lines)
        post["text"] = msg.message or ""

        return post

    except Exception as e:
        logging.error(f"❌ Помилка пересилки поста з {post.get('channel')}: {e}")
        return {}

    finally:
        await client.disconnect()


async def fetch_posts_for_category(channels: list[dict]) -> list[dict]:
    await client.start()
    all_posts = []

    for ch in channels:
        try:
            entity = await client.get_entity(ch["id"])
            print(f"[DEBUG] get_entity for: {ch['title']}, resolved id: {entity.id}")

            messages = [msg async for msg in client.iter_messages(entity, limit=POST_LIMIT)]

            grouped = defaultdict(list)
            single_posts = []

            for msg in messages:
                if getattr(msg, "grouped_id", None):
                    grouped[msg.grouped_id].append(msg)
                else:
                    single_posts.append(msg)

            for msg in single_posts:
                if not msg.message and not msg.media:
                    continue

                media_type = "text"
                if msg.photo:
                    media_type = "photo"
                elif msg.video:
                    media_type = "video"
                elif msg.document:
                    media_type = "document"

                post = {
                    "channel": ch["title"],
                    "channel_id": ch["id"],
                    "text": msg.raw_text or "",
                    "html_text": telethon_to_html_safe(msg),
                    "views": msg.views or 0,
                    "forwards": msg.forwards or 0,
                    "date": msg.date.timestamp(),
                    "score": compute_score(msg),
                    "media_type": media_type,
                    "grouped_id": None,
                    "original_msg_id": msg.id
                }

                all_posts.append(post)

            for group_msgs in grouped.values():
                sorted_msgs = sorted(group_msgs, key=lambda m: m.date)
                if not sorted_msgs:
                    continue

                media_group = []
                for msg in sorted_msgs:
                    media_type = None
                    if msg.photo:
                        media_type = "photo"
                    elif msg.video:
                        media_type = "video"
                    if media_type:
                        media_group.append({
                            "type": media_type,
                            "message_id": msg.id
                        })

                if not media_group:
                    continue

                first_msg = sorted_msgs[0]
                post = {
                    "channel": ch["title"],
                    "channel_id": ch["id"],
                    "text": first_msg.raw_text or "",
                    "html_text": telethon_to_html_safe(first_msg),
                    "views": first_msg.views or 0,
                    "forwards": first_msg.forwards or 0,
                    "date": first_msg.date.timestamp(),
                    "score": compute_score(first_msg),
                    "media_type": "album",
                    "grouped_id": first_msg.grouped_id,
                    "original_group_ids": [m.id for m in sorted_msgs]
                }

                all_posts.append(post)

        except Exception as e:
            print(f"❌ Помилка для каналу {ch['title']}: {e}")
            continue

    await client.disconnect()
    all_posts.sort(key=lambda x: x["score"], reverse=True)
    return all_posts


async def resolve_channel_by_username(username: str) -> dict | None:
    try:
        await client.start()
        if username.startswith("@"): 
            username = username[1:]

        print(f"[resolve_channel_by_username] 🟡 Запит на {username}")
        entity = await client.get_entity(username)

        if isinstance(entity, Channel):
            channel_id = entity.id
            if channel_id > 0:
                channel_id = int(f"-100{channel_id}")

            return {
                "id": channel_id,
                "title": getattr(entity, "title", None),
                "username": f"@{entity.username}" if getattr(entity, "username", None) else None
            }

        print(f"[resolve_channel_by_username] ⚠️ Об'єкт {username} не є каналом")
        return None

    except Exception as e:
        print(f"[resolve_channel_by_username] ❌ Не вдалося отримати {username}: {e}")
        return None

    finally:
        await client.disconnect()
