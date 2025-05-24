from telethon.sync import TelegramClient

API_ID = int(input("API_ID: "))
API_HASH = input("API_HASH: ")
SESSION_NAME = input("Назва сесії (наприклад 'anon'): ")

with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
    print("✅ Сесія збережена.")
