import aiohttp
import os
import tempfile
from uuid import uuid4
from pathlib import Path
from aiogram import Bot

TELEGRAPH_UPLOAD_URL = "https://telegra.ph/upload"

async def download_file_and_get_url(bot: Bot, file_id: str) -> str:
    # Завантаження файлу з Telegram
    tg_file = await bot.get_file(file_id)
    temp_dir = tempfile.gettempdir()
    filename = f"{uuid4()}.jpg"
    temp_path = os.path.join(temp_dir, filename)

    await bot.download_file(tg_file.file_path, destination=temp_path)

    try:
        async with aiohttp.ClientSession() as session:
            with open(temp_path, "rb") as f:
                form = aiohttp.FormData()
                form.add_field("file", f, filename=filename, content_type="image/jpeg")

                async with session.post(TELEGRAPH_UPLOAD_URL, data=form) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list) and "src" in data[0]:
                            return "https://telegra.ph" + data[0]["src"]
                        else:
                            raise Exception(f"Unexpected response: {data}")
                    else:
                        error_text = await resp.text()
                        raise Exception(f"Upload to Telegraph failed: {resp.status} - {error_text}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
