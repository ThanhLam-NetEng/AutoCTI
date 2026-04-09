import requests, os
from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from custom_memory import TimeSeriesDynamoDBHistory

load_dotenv('/home/ubuntu/autocti/.env')
token = os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = os.getenv('ALLOWED_CHAT_IDS').split(',')[0]

msg_text = 'Chủ nhân, 7 giờ sáng rồi đó. Tuyết nhi chúc Chủ nhân ngày mới năng lượng nha! Cần gì cứ hỏi Tuyết nhi nhé. ☀️❤️'

requests.post(f'https://api.telegram.org/bot{token}/sendMessage', json={'chat_id': chat_id, 'text': msg_text})

try:
    db_history = TimeSeriesDynamoDBHistory(session_id=str(chat_id))
    db_history.add_message(AIMessage(content=msg_text))
    print("[-] Đã lưu lời chào vào DynamoDB.")
except Exception as e:
    print(f"Lỗi: {e}")