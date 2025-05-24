import os
import requests
from dotenv import load_dotenv

load_dotenv()

PAGE_ID = os.getenv("FB_PAGE_ID")
ACCESS_TOKEN = os.getenv("FB_PAGE_TOKEN")

def clean_caption(text: str) -> str:
    """Видаляє чужі підписи (✍️) з тексту."""
    return text.split("✍️")[0].strip()

def post_to_facebook_text(text: str) -> dict:
    """Публікує звичайний текстовий пост на Facebook."""
    url = f"https://graph.facebook.com/v22.0/{PAGE_ID}/feed"
    payload = {
        "message": clean_caption(text),
        "access_token": ACCESS_TOKEN
    }
    try:
        response = requests.post(url, params=payload)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def post_to_facebook_with_image(text: str, image_path: str) -> dict:
    """Публікує фото (файл) з підписом."""
    url = f"https://graph.facebook.com/v22.0/{PAGE_ID}/photos"
    try:
        with open(image_path, "rb") as image_file:
            files = {
                "source": image_file
            }
            data = {
                "caption": clean_caption(text),
                "access_token": ACCESS_TOKEN
            }
            response = requests.post(url, files=files, data=data)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# 🔜 Публікація відео — за потреби
# def post_video_to_facebook(text: str, video_path: str) -> dict:
#     url = f"https://graph.facebook.com/v22.0/{PAGE_ID}/videos"
#     try:
#         with open(video_path, "rb") as video_file:
#             files = {
#                 "source": video_file
#             }
#             data = {
#                 "description": clean_caption(text),
#                 "access_token": ACCESS_TOKEN
#             }
#             response = requests.post(url, files=files, data=data)
#         return response.json()
#     except Exception as e:
#         return {"error": str(e)}
