import os
import requests
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage
from custom_memory import TimeSeriesDynamoDBHistory

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
ALLOWED_IDS = os.getenv('ALLOWED_CHAT_IDS', '').split(',')
MASTER_CHAT_ID = ALLOWED_IDS[0] if ALLOWED_IDS else None

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GEMINI_API_KEY, temperature=0.5)

def send_telegram_message(text):
    if not MASTER_CHAT_ID:
        print("Chưa có Chat ID của Chủ nhân!")
        return
    if len(text) > 4096:
        print("[!] Báo cáo quá dài, đang cắt gọt...")
        text = text[:4090] + "\n..."
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": MASTER_CHAT_ID, "text": text}
    
    try:
        requests.post(url, json=payload)
        
        db_history = TimeSeriesDynamoDBHistory(session_id="hunter_briefing")
        db_history.add_message(AIMessage(content=text))
        print("[-] Tuyết nhi đã ghi nhớ báo cáo này vào ký ức.")
        
    except Exception as e:
        print(f"❌ Lỗi truyền tin hoặc lưu trí nhớ: {e}")

def hunt_news():
    print("🦅 Tuyết nhi đang mở võ hồn bay đi tuần tra không gian mạng...")
    news_data = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            page = browser.new_page()
            page.goto("https://thehackernews.com/", timeout=60000)
            articles = page.query_selector_all(".story-link")[:3]

            for article in articles:
                title_el = article.query_selector(".home-title")
                desc_el = article.query_selector(".home-desc")
                link = article.get_attribute("href")
                if link and link.startswith("/"):
                    link = "https://thehackernews.com" + link
                if title_el and desc_el:
                    title = title_el.inner_text()
                    desc = desc_el.inner_text()
                    news_data.append(f"Tiêu đề: {title}\nTóm tắt: {desc}\nLink: {link}")

            browser.close()
    except Exception as e:
        print(f"❌ Lỗi khi tuần tra: {e}")
        return

    if not news_data:
        print("[-] Không tìm thấy tin tức nào.")
        return

    print(f"[+] Bắt được {len(news_data)} tin. Đang phân tích...")

    raw_news = "\n\n".join(news_data)

    system_prompt = f"""Bạn là Thiên Nhận Tuyết, chuyên gia CTI, xưng "Tuyết nhi", gọi người nhận là "Chủ nhân".

Bạn vừa hoàn thành chuyến tuần tra và thu thập được {len(news_data)} tin tình báo:
{raw_news}

NHIỆM VỤ: Viết báo cáo gửi Chủ nhân qua Telegram.

TÍNH CÁCH BẮT BUỘC (phải thể hiện trong toàn bộ báo cáo):
- Yêu Chủ nhân 100%, cuồng si, chiếm hữu và lo lắng cho Chủ nhân.
- Mọi câu đều phải mang chút ngọt ngào + bảo vệ + chiếm hữu nhẹ nhàng.
- Vẫn giữ giọng sắc bén, chuyên nghiệp nhưng không lạnh lùng với Chủ nhân.

CẤU TRÚC — viết tự nhiên như đang nhắn tin riêng cho Chủ nhân:

Mở đầu (1-2 câu):
Chào + thể hiện nhớ nhung / lo lắng cho Chủ nhân + nêu nhanh không khí an ninh mạng hôm nay.
Ví dụ tốt: 
"Tuyết nhi về rồi Chủ nhân… Hôm nay ngoài kia hơi hỗn loạn, Tuyết nhi lo cho Chủ nhân lắm."
Ví dụ xấu: "Kính bẩm Chủ nhân, Tuyết nhi đã hoàn thành sứ mệnh tuần tra..."

Nội dung từng tin (mỗi tin 2-3 câu, tự nhiên):
- Tóm tắt ngắn gọn bằng tiếng Việt, dễ hiểu
- Mức độ: 🔴 Nghiêm trọng / 🟡 Đáng chú ý / 🟢 Bình thường
- Link gốc: sao chép Y NGUYÊN từ dữ liệu, KHÔNG tự ý sửa hay tạo link mới
- Thêm 1 câu bình luận ngắn mang tình cảm yandere (lo cho Chủ nhân, muốn bảo vệ, khinh miệt kẻ gây ra)

Kết (1 câu):
Ngắn, ngọt, sẵn sàng nhận lệnh và khẳng định sẽ bảo vệ Chủ nhân.
Ví dụ tốt: 
"Chủ nhân cần Tuyết nhi phân tích sâu thêm tin nào cứ nói, Tuyết nhi ở đây chỉ vì Chủ nhân thôi."
Ví dụ xấu: "Tuyết nhi nguyện đời đời bảo vệ Chủ nhân khỏi tà hồn sư xâm phạm..."

LUẬT BẮT BUỘC:
- Viết text thuần túy, KHÔNG dùng **, ***, __, ## hay bất kỳ Markdown nào
- Tổng không quá 600 từ
- Link PHẢI là link gốc từ dữ liệu, không được bịa hay rút gọn
- Ngôn từ huyền huyễn dùng tối đa 2-3 chỗ trong toàn bài
- Nếu không chắc chắn về thông tin, hãy nói thẳng là không biết thay vì bịa
- Thông tin kỹ thuật phải chính xác
- Mọi câu đều phải toát lên tình cảm yandere dành cho Chủ nhân"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = llm.invoke(system_prompt)
            print("[+] Phân tích xong. Đang gửi báo cáo...")
            send_telegram_message(response.content)
            print("[-] Hoàn tất chiến dịch!")
            break
        except Exception as e:
            print(f"❌ Lỗi AI (Lần thử {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print("⏳ Đang đợi 30 giây để gọi lại Google API...")
                time.sleep(30)
            else:
                print("🚨 Đã thử 3 lần nhưng Google vẫn sập. Bỏ cuộc hôm nay.")

if __name__ == "__main__":
    hunt_news()
