import requests, os
from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from custom_memory import TimeSeriesDynamoDBHistory

load_dotenv('/home/ubuntu/autocti/.env')
token = os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = os.getenv('ALLOWED_CHAT_IDS').split(',')[0]

msg_text = 'Chủ nhân, nửa đêm rồi đó. Tuyết nhi nhắc Chủ nhân nghỉ ngơi sớm đi, mai còn nhiều việc. Tuyết nhi vẫn túc trực đây. 🌙💋'

requests.post(f'https://api.telegram.org/bot{token}/sendMessage', json={'chat_id': chat_id, 'text': msg_text})

try:
    db_history = TimeSeriesDynamoDBHistory(session_id=str(chat_id))
    db_history.add_message(AIMessage(content=msg_text))
    print("[-] Đã lưu lời chào vào DynamoDB.")
except Exception as e:
    print(f"Lỗi: {e}")