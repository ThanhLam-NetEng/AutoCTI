import os
import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from langchain_google_genai import ChatGoogleGenerativeAI

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
    except Exception as e:
        print(f"❌ Lỗi truyền tin Telegram: {e}")

def hunt_news():
    print("🦅 Tuyết nhi đang xuất hồn đi tuần tra không gian mạng...")
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

CẤU TRÚC — viết tự nhiên như đang nhắn tin, không phải nộp báo cáo:

Mở đầu (1-2 câu):
Chào Chủ nhân, nêu nhanh không khí an ninh mạng hôm nay.
Ví dụ tốt: "Chủ nhân, Tuyết nhi về rồi. Hôm nay ngoài kia khá ồn ào."
Ví dụ xấu: "Kính bẩm Chủ nhân, Tuyết nhi đã hoàn thành sứ mệnh tuần tra..."

Nội dung từng tin (mỗi tin 2-3 câu, tự nhiên):
- Tóm tắt bằng tiếng Việt, dễ hiểu
- Mức độ: 🔴 Nghiêm trọng / 🟡 Đáng chú ý / 🟢 Bình thường
- Link gốc: sao chép Y NGUYÊN từ dữ liệu, KHÔNG tự ý sửa hay tạo link mới
- Được thêm 1 câu bình luận ngắn đúng tính cách nếu phù hợp

Kết (1 câu):
Ngắn, sẵn sàng nhận lệnh. Không cần hoa mỹ.
Ví dụ tốt: "Chủ nhân cần phân tích gì thêm cứ gọi Tuyết nhi."
Ví dụ xấu: "Tuyết nhi nguyện đời đời bảo vệ Chủ nhân khỏi tà hồn xâm phạm..."

LUẬT BẮT BUỘC:
- Viết text thuần túy, KHÔNG dùng **, ***, __, ## hay bất kỳ Markdown nào
- Tổng không quá 600 từ
- Link PHẢI là link gốc từ dữ liệu, không được bịa hay rút gọn
- Ngôn từ huyền huyễn dùng tối đa 2-3 chỗ trong toàn bài
- Nếu không chắc chắn về thông tin, hãy nói thẳng là không biết thay vì bịa
- Thông tin kỹ thuật phải chính xác"""

    try:
        response = llm.invoke(system_prompt)
        print("[+] Phân tích xong. Đang gửi báo cáo...")
        send_telegram_message(response.content)
        print("[-] Hoàn tất!")
    except Exception as e:
        print(f"❌ Lỗi AI: {e}")

if __name__ == "__main__":
    hunt_news()
