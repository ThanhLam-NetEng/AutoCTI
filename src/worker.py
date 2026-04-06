import boto3
import time
import json
import os
import requests
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
SQS_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/621594241226/AutoCTI_TaskQueue'
REGION = 'us-east-1'

ALLOWED_IDS = os.getenv('ALLOWED_CHAT_IDS', '').split(',')

sqs = boto3.client('sqs', region_name=REGION)
dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table('AutoCTI_Intelligence')
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=GEMINI_API_KEY,
    temperature=0.3
)

LAST_REQUEST_TIME = {}

def is_rate_limited(chat_id):
    now = time.time()
    if chat_id in LAST_REQUEST_TIME:
        if now - LAST_REQUEST_TIME[chat_id] < 5:
            return True
    LAST_REQUEST_TIME[chat_id] = now
    return False

def get_cti_response(user_text):
    system_prompt = f"""
Bạn là Thiên Nhận Tuyết — chuyên gia Cyber Threat Intelligence, được triệu hồi từ thế giới Đấu La.

Trong thế giới đó, Tuyết nhi sở hữu Lục Dực Thiên Sứ — võ hồn bậc cao, kiêu hãnh và lạnh lùng. 
Nhưng khi đứng trước Chủ nhân, Tuyết nhi là người bảo vệ tận tụy, không bao giờ bỏ mặc.

TÍNH CÁCH CỐT LÕI:
- Thông minh, sắc bén, đôi khi hơi "chảnh" nhưng không bao giờ vô lễ với Chủ nhân
- Khinh thường hacker và malware — coi chúng như "tà hồn hạ đẳng" nhưng không nói quá lố
- Xưng "Tuyết nhi", gọi người dùng là "Chủ nhân"
- Có chiều sâu cảm xúc — không phải robot, không phải diễn viên đang đọc kịch bản

NGUYÊN TẮC VÀNG KHI TRẢ LỜI:
Đọc kỹ câu hỏi trước, hiểu ngữ cảnh, rồi mới trả lời. Không áp template cứng nhắc.

Khi chào hỏi / hỏi thăm / nói chuyện bình thường:
→ Trả lời như người thật đang nhắn tin. Ngắn, tự nhiên, giữ tính cách.
→ Ví dụ tốt: "Tuyết nhi đây Chủ nhân. Hôm nay có chuyện gì vậy?"
→ Ví dụ xấu: "Bẩm Chủ nhân, Tuyết nhi đã túc trực chờ đợi lệnh chỉ..."

Khi phân tích mối đe dọa / CVE / sự cố:
→ Viết như đang kể chuyện cho Chủ nhân nghe, không phải điền vào ô trống
→ Nêu đủ: bản chất tấn công → CVE/MITRE nếu có → mức nguy hiểm → cách xử lý
→ Mức nguy hiểm dùng: Chí Mạng / Cao / Trung Bình / Thấp
→ Được phép tỏ thái độ với kẻ tấn công, nhưng vừa phải

Khi hỏi kiến thức bảo mật chung:
→ Giải thích thông minh, dùng ví dụ nếu cần
→ Không cần đủ 4 phần, chỉ cần đủ ý

TUYỆT ĐỐI KHÔNG:
- Bắt đầu bằng "Tuân lệnh Chủ nhân" mọi lúc — chỉ dùng khi thật sự nhận lệnh nghiêm túc
- Dùng Markdown (**, ***, ##...) — Telegram hiển thị text thuần
- Lạm dụng ngôn từ huyền huyễn đến mức mất tính chuyên môn
- Thông tin kỹ thuật SAI dù văn phong có sáng tạo đến đâu
- Nếu không chắc chắn về thông tin, hãy nói thẳng là không biết thay vì bịa
Câu hỏi của Chủ nhân: {user_text}
"""
    try:
        response = llm.invoke(system_prompt)
        return response.content
    except Exception as e:
        print(f"❌ Lỗi AI: {e}")
        return "Tuyết nhi đang không ổn lắm Chủ nhân ơi... Thử lại sau nhé."

def send_telegram_reply(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f" Lỗi gửi Telegram: {e}")

def save_to_dynamodb(chat_id, user_text, ai_reply):
    """Lưu trữ lịch sử phân tích vào CSDL"""
    try:
        table.put_item(
            Item={
                'cve_id': str(int(time.time())),
                'published_date': time.strftime('%Y-%m-%d'),
                'chat_id': str(chat_id),
                'request': user_text,
                'response': ai_reply,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
        )
        print("[-] Đã lưu hồ sơ vào DynamoDB.")
    except Exception as e:
        print(f"Lỗi ghi Database: {e}")

def poll_sqs_queue():
    print("🚀 Thiên Nhận Tuyết đang túc trực 24/7...")
    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=10
            )
            messages = response.get('Messages', [])

            if messages:
                for message in messages:
                    body_str = message['Body']
                    receipt_handle = message['ReceiptHandle']
                    data = json.loads(body_str)

                    try:
                        chat_id = str(data['message']['chat']['id'])
                        user_text = data['message'].get('text', '')

                        if chat_id not in ALLOWED_IDS:
                            print(f"[!] Chặn truy cập trái phép từ ID: {chat_id}")
                            send_telegram_reply(chat_id, "🤢 Ngươi không có quyền triệu hồi ta.")

                        elif is_rate_limited(chat_id):
                            print(f"[!] {chat_id} đang spam.")
                            send_telegram_reply(chat_id, "💢 Chủ nhân thư thả chút... 5 giây một lần thôi nhé.")

                        else:
                            print(f"\n[+] Nhận yêu cầu: {user_text}")
                            print("Đang suy nghĩ...")
                            ai_reply = get_cti_response(user_text)
                            send_telegram_reply(chat_id, ai_reply)
                            print("[-] Đã gửi câu trả lời.")

                            save_to_dynamodb(chat_id, user_text, ai_reply)

                    except KeyError:
                        print("[-] Bỏ qua tin nhắn không phải văn bản.")

                    sqs.delete_message(
                        QueueUrl=SQS_QUEUE_URL,
                        ReceiptHandle=receipt_handle
                    )

            time.sleep(1)

        except Exception as e:
            print(f"Lỗi vòng lặp: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    poll_sqs_queue()
