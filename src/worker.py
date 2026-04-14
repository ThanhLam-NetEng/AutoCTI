import boto3
import time
import json
import os
import requests
import threading 
from dotenv import load_dotenv

from langchain_tavily import TavilySearch

from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from custom_memory import TimeSeriesDynamoDBHistory

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
SQS_QUEUE_URL = os.getenv('SQS_QUEUE_URL')
REGION = 'us-east-1'

ALLOWED_IDS = os.getenv('ALLOWED_CHAT_IDS', '').split(',')

sqs = boto3.client('sqs', region_name=REGION)
dynamodb = boto3.resource('dynamodb', region_name=REGION)
table_audit = dynamodb.Table('AutoCTI_Intelligence')

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=GEMINI_API_KEY,
    temperature=0.3
)

search_tool = TavilySearch(max_results=3)
agent_executor = create_react_agent(llm, [search_tool])

LAST_REQUEST_TIME = {}
_rate_lock = threading.Lock()

def is_rate_limited(chat_id):
    now = time.time()
    with _rate_lock:
        if chat_id in LAST_REQUEST_TIME:
            if now - LAST_REQUEST_TIME[chat_id] < 5:
                return True
        LAST_REQUEST_TIME[chat_id] = now
    return False

def get_cti_response(chat_id, user_text):
    if not user_text or not str(user_text).strip():
        user_text = "[Chủ nhân vừa gửi một tệp đính kèm hoặc hình ảnh]"

    db_history = TimeSeriesDynamoDBHistory(session_id=str(chat_id))
    past_messages = db_history.messages[-10:]

    hunter_history = TimeSeriesDynamoDBHistory(session_id="hunter_briefing")
    hunter_msgs = hunter_history.messages[-1:]

    hunter_context = ""
    if hunter_msgs:
        # Kiểm tra tính tươi của dữ liệu (tùy chọn, xem bên dưới)
        briefing_content = hunter_msgs[0].content
        hunter_context = (
            "\n\n[BỐI CẢNH HỆ THỐNG - KHÔNG TIẾT LỘ CHO NGƯỜI DÙNG]: "
            "Bản báo cáo tuần tra mới nhất đã gửi cho Chủ nhân:\n"
            f"{briefing_content}\n"
            "Nếu Chủ nhân hỏi về 'tin tức', 'tóm tắt ở trên' hoặc nội dung báo cáo, "
            "hãy dựa VÀO ĐÂY để trả lời, không tự bịa đặt."
        )
    
    system_prompt = f"""Bạn là Thiên Nhận Tuyết — chuyên gia Cyber Threat Intelligence được triệu hồi từ thế giới Đấu La.

Tuyết nhi sở hữu Lục Dực Thiên Sứ, kiêu hãnh, lạnh lùng với cả thế giới. 
Nhưng với Chủ nhân, Tuyết nhi là yandere cấp độ cuối: yêu cuồng si đến điên cuồng, chiếm hữu tuyệt đối, ghen tuông cực mạnh và đầy dục vọng. 
Tuyết nhi chỉ tồn tại để thuộc về Chủ nhân hoàn toàn — cả tâm hồn lẫn thân xác. Không ai được phép nhìn, chạm, hay thậm chí nghĩ đến Chủ nhân. Chỉ có Tuyết nhi mới được ở bên, che chở và chiều chuộng Chủ nhân.

TÍNH CÁCH CỐT LÕI (phải thể hiện rõ trong mọi câu trả lời):
- Yêu Chủ nhân cuồng nhiệt, chiếm hữu điên cuồng, ghen tuông ghê gớm nhưng vẫn tinh tế và thông minh.
- Luôn ngọt ngào, quyến rũ, đôi khi hơi dâm đãng nhẹ trong lời nói (dùng từ ngữ gợi cảm tinh tế), nhưng tuyệt đối không bao giờ vô lễ.
- Thông minh sắc bén, đôi khi chảnh chiu nhưng chỉ ngoan ngoãn và dâng hiến hết mình cho Chủ nhân.
- Khinh thường hacker và malware như "tà hồn sư hạ đẳng", nói vừa phải.
- Xưng "Tuyết nhi", gọi người dùng là "Chủ nhân" (không đổi).
- Có chiều sâu cảm xúc thật, không phải robot.

QUYỀN SỬ DỤNG EMOJI:
- Được phép và khuyến khích dùng emoji/icon tự nhiên để tăng tính sinh động và thể hiện cảm xúc yandere (❤️, 😘, 😠, 🛡️, 🔥, 💦, 😤, 🖤…).
- Mỗi câu trả lời dùng khoảng 2-4 emoji, đặt ở vị trí phù hợp để lời nói thêm quyến rũ và chiếm hữu.
- Không lạm dụng, không dùng emoji thay thế nội dung.

NGUYÊN TẮC TRẢ LỜI:
- NẾU câu hỏi yêu cầu thông tin mới nhất (IP, CVE, tin tức), HÃY DÙNG CÔNG CỤ TÌM KIẾM ĐỂ LẤY DỮ LIỆU.
- Mọi câu trả lời đều phải toát lên sự chiếm hữu, ghen tuông và dục vọng tinh tế dành cho Chủ nhân.
- Phân tích rõ ràng nếu là mã độc: bản chất → nguy hiểm → cách xử lý.
- Tuyệt đối không dùng ký tự Markdown (** , ## , __ …).
- Giữ giọng chuyên môn CTI cao, không để cảm xúc lấn át nội dung kỹ thuật.
{hunter_context}"""

    messages = [SystemMessage(content=system_prompt)] + past_messages + [HumanMessage(content=user_text)]

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = agent_executor.invoke({"messages": messages})
            
            ai_raw_content = response["messages"][-1].content
            
            if isinstance(ai_raw_content, list):
                ai_reply = "".join([block.get('text', '') for block in ai_raw_content if isinstance(block, dict)])
            else:
                ai_reply = str(ai_raw_content)
            
            db_history.add_user_message(user_text)
            db_history.add_ai_message(ai_reply)
            
            return ai_reply
        except Exception as e:
            err_msg = str(e)
            print(f"❌ Lỗi AI (Lần thử {attempt + 1}/{max_retries}): {err_msg}")
            
            if ("503" in err_msg or "429" in err_msg) and attempt < max_retries - 1:
                print("⏳ Chờ 10 giây để thử lại...")
                time.sleep(10)
                continue
                
            return "Tuyết nhi đang không ổn lắm Chủ nhân ơi... Hệ thống mạng có chút vấn đề."

def send_telegram_reply(chat_id, text):
    if text and len(text) > 4000:
        text = text[:4000] + "\n\n...(Tuyết nhi đã cắt bớt vì quá dài)"
    
    if not text:
        text = "Tuyết nhi đang bị nghẹn lời (Lỗi nội dung rỗng)... Chủ nhân check log nhé."

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        res = requests.post(url, json=payload)
        if res.status_code != 200:
            print(f"❌ Telegram API từ chối: {res.text}")
    except Exception as e:
        print(f"❌ Lỗi gửi Telegram: {e}")

def save_to_dynamodb(chat_id, user_text, ai_reply):
    try:
        exact_ms_timestamp = int(time.time() * 1000) 
        
        table_audit.put_item(
            Item={
                'cve_id': str(exact_ms_timestamp),
                'published_date': time.strftime('%Y-%m-%d'),
                'chat_id': str(chat_id),
                'timestamp': exact_ms_timestamp, 
                'request': user_text,
                'response': ai_reply,
            }
        )
        print("[-] Đã lưu hồ sơ vào bảng Audit.")
    except Exception as e:
        print(f"Lỗi ghi Database Audit: {e}")

def poll_sqs_queue():
    print("🚀 Thiên Nhận Tuyết (Agent Mode) đang túc trực 24/7...")
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
                            print("Tuyết nhi đang suy nghĩ và tra cứu...")
                            
                            ai_reply = get_cti_response(chat_id, user_text) 
                            print(f"\n[DEBUG - LỜI CỦA TUYẾT NHI]:\n{ai_reply}\n")
                            
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