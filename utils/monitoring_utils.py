import re
import logging
from html import escape
from bs4 import BeautifulSoup
from utils.json_storage import load_groups, load_known_media, load_channel_signature

def build_media_targets(data, known_media, groups_data):
    all_keys = set(data.get("selected_channels", []))

    for group in data.get("selected_groups", []):
        for ch in groups_data.get(group, []):
            all_keys.add(ch["title"] if isinstance(ch, dict) else ch)

    result = []
    for key in all_keys:
        info = known_media.get(key)
        if info and "id" in info and "platform" in info:
            result.append({
                "id": info["id"],
                "title": info.get("title", key),
                "platform": info["platform"]
            })

    return result

def fix_malformed_links(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    anchors = soup.find_all('a')

    for a in anchors:
        prev = a.previous_sibling
        if prev and isinstance(prev, str) and prev.strip() and not prev.strip().startswith("<"):
            a.string = (prev.strip() + " " + (a.string or "")).strip()
            prev.extract()

        nxt = a.next_sibling
        if nxt and isinstance(nxt, str) and nxt.strip() and not nxt.strip().startswith("<"):
            a.string = ((a.string or "") + " " + nxt.strip()).strip()
            nxt.extract()

    return str(soup)

def build_full_caption(text: str, chat_id: int, remove_links: bool = False) -> str:
    logging.debug(f"[build_full_caption] ▶️ chat_id={chat_id}, remove_links={remove_links}")

    caption = text or ""

    if remove_links:
        logging.debug("[build_full_caption] ⚠️ Форматування лінків вимкнене")

    sig_info = load_channel_signature(chat_id)
    raw_sig = sig_info.get("signature", "")
    if sig_info.get("enabled", True) and raw_sig:
        logging.debug(f"[build_full_caption] 🖋 Додаємо підпис (довжина {len(raw_sig)} симв.)")
        caption += "\n\n" + raw_sig
    else:
        logging.debug("[build_full_caption] ℹ️ Підпис вимкнено або порожній")

    logging.debug(f"[build_full_caption] 🧾 Фінальний текст (обрізано): {caption[:100]}...")
    return caption.strip()

def custom_html_formatter(text: str) -> str:
    platforms = {
        "ТЕЛЕГРАМ": r"(📩)?(ТЕЛЕГРАМ)",
        "ТІКТОК": r"(🔓)?(ТІКТОК)",
        "ФЕЙСБУК": r"(😎)?(ФЕЙСБУК)",
    }

    urls = re.findall(r'https?://\S+', text)
    if not urls:
        return text

    url_index = 0
    for name, pattern in platforms.items():
        match = re.search(pattern, text)
        if match and url_index < len(urls):
            emoji = match.group(1) or ""
            label = match.group(2)
            url = urls[url_index]
            url_index += 1

            link_html = f'{emoji}<a href="{escape(url)}">{escape(label)}</a>'
            text = text.replace(match.group(0), link_html, 1)

    text = re.sub(r'https?://\S+', '', text)
    return text
