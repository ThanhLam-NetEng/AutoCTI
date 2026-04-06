import requests, os
from dotenv import load_dotenv
load_dotenv('/home/ubuntu/autocti/.env')
token = os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = os.getenv('ALLOWED_CHAT_IDS').split(',')[0]
requests.post(f'https://api.telegram.org/bot{token}/sendMessage', json={'chat_id': chat_id, 'text': 'Chủ nhân, nửa đêm rồi đó. Tuyết nhi nhắc Chủ nhân nghỉ ngơi sớm đi, mai còn nhiều việc. Tuyết nhi vẫn túc trực đây. 🌙💋'})
