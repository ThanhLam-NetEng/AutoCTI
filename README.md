# 🛡️ AutoCTI — Autonomous Cyber Threat Intelligence Agent

A 24/7 automated CTI pipeline built on AWS, powered by AI. AutoCTI automatically collects cybersecurity threat intelligence, analyzes CVEs and MITRE ATT&CK techniques, and delivers daily briefings via Telegram. 

**v2.0 Major Update:** Re-architected with **LangGraph** (Agentic Workflow), **Tavily** (Real-time Search), and **DynamoDB** (Persistent Memory) to achieve a stateful, highly optimized, and robust SOC Assistant.

---

## 🏗️ System Architecture

![Architecture](autocti_v2_architecture.svg)

Flow:
1. User sends message via Telegram.
2. Webhook hits API Gateway → message queued in SQS.
3. EC2 Worker (Dockerized) polls SQS → validates Whitelist & Thread-safe Rate Limit.
4. **LangGraph Agent** retrieves conversation history from **DynamoDB**.
5. Agent decides if real-time web search (**Tavily**) is needed based on context.
6. Gemini AI analyzes threat → returns CTI report & saves Audit to Database.
7. Hunter crawls top security news daily at 8AM GMT+7 (Exponential Backoff enabled).

---

## ✨ Features

- **Agentic Workflow (New in v2.0):** Uses LangGraph to dynamically route tasks, enabling the AI to search the internet autonomously when asked about recent threats.
- **Persistent Memory (New in v2.0):** Integrated AWS DynamoDB to store conversation context (Session IDs) and Audit logs with microsecond precision.
- **Ultra-Lightweight Web Automation:** Replaced Playwright with Tavily Search API, reducing container RAM usage by ~80%.
- **Resilience & Rate Limiting:** Built-in `threading.Lock()` for rate limiting and Exponential Backoff to gracefully handle Google API 503/429 limits.
- **Security First:** IAM Role (no hardcoded credentials), Strict Telegram Whitelist.
- **AI Persona:** "Thien Nhan Tuyet" — A CTI analyst with a fiercely loyal (Yandere-lite) personality.
- **Docker Compose:** Fully containerized with `restart: always` for immortal uptime on EC2.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Cloud Infrastructure | AWS EC2 (t3.small), SQS, DynamoDB, API Gateway, IAM |
| AI Engine | Google Gemini 2.5 Flash |
| Agentic Framework | LangChain & LangGraph |
| Web Search API | Tavily |
| Runtime | Python 3.12, Docker & Docker Compose |
| Messaging | Telegram Bot API |

---

## 📂 Project Structure

```text
autocti/
├── src/
│   ├── worker.py          # SQS listener + LangGraph Agent + Database logging
│   ├── hunter.py          # Tavily news crawler + daily briefing
│   ├── morning.py         # 7AM greeting scheduler
│   ├── goodnight.py       # 12AM rest reminder
│   └── custom_memory.py   # DynamoDB BaseChatMessageHistory implementation
├── docker-compose.yml     # Container orchestration
├── Dockerfile             # Multi-layer slim Python image
├── requirements.txt
├── .env.example
└── README.md
```

---

## ⚙️ Environment Variables

Copy .env.example to .env and fill in your values. (Note: Ensure you have your TAVILY_API_KEY for v2.0).

TELEGRAM_BOT_TOKEN=your_telegram_bot_token

GEMINI_API_KEY=your_gemini_api_key

TAVILY_API_KEY=your_tavily_api_key

ALLOWED_CHAT_IDS=your_telegram_chat_id

SQS_QUEUE_URL=your_sqs_queue_url

---

## 📸 Demo & Screenshots

Below are real-world operational screenshots of AutoCTI running on the AWS EC2 Production environment:

### 1. Personal Assistant (Daily Alarms)
Automated morning wake-up calls and bedtime reminders triggered by system cronjobs.
<details>
<summary><b>View: Morning & Goodnight Alerts</b></summary>

![Morning Alarm](screenshots/morning_alarm.png)
*Daily briefing trigger at 07:00 AM (GMT+7).*

![Goodnight Reminder](screenshots/goodnight_reminder.png)
*System sleep reminder at 24:00 (GMT+7).*
</details>

### 2. Daily Threat Briefing (08:00 AM)
Automated web scraping (via Playwright) from HackerNews, summarized by AI, and delivered daily.
![Daily Briefing](screenshots/daily_briefing.png)

### 3. Deep-Dive CTI Q&A
Real-time interaction with the AI agent for technical threat analysis (e.g., SQL Injection analysis, MITRE ATT&CK mapping).
![CTI Analysis](screenshots/cti_analysis.png)

### 4. Security Layer (Access Control)
Strict Whitelist mechanism blocking unauthorized Telegram IDs from interacting with the SOC infrastructure.
![Whitelist Block](screenshots/whitelist_block.png)

### 5. Agentic Web Search (v2.0 Exclusive) 🌟
The AI autonomously decides to use the `TavilySearch` tool to crawl the internet for real-time news when asked about the latest APT campaigns.
![Agentic Search](screenshots/tavily_search.png)

## Known Limitations & Roadmap

### Current Limitations (v1.0)

- Stateless architecture — AI has no memory of previous messages
- No real-time web search in worker (only hunter has Playwright)
- Hallucination risk with niche/local Vietnamese products not in training data

### 🗺️ Roadmap (v2.0)

- [x] LangChain Memory + DynamoDB for conversation context.
- [x] Tavily Search API integration for real-time web search in worker.
- [x] Replace Playwright to optimize EC2 RAM limitations.
- [x] Fix SQS/DynamoDB Race Conditions with Global Agents & Locks.

### Roadmap (v3.0)

- [ ] RAG (Retrieval-Augmented Generation) with Vector DB (e.g., Pinecone/Chroma) to query internal SOC playbooks.
- [ ] NVD API integration for automated & precise CVE tracking.
- [ ] Automated IOC (IP/Domain) extraction and submission to VirusTotal API.

---

## 💰 Cost Estimate

| Service | Usage | Cost |
|---|---|---|
| EC2 t2.micro | 24/7 | $0 (Free Tier 750h/month) |
| Amazon SQS | <1M req/month | $0 |
| DynamoDB | <25GB | $0 |
| API Gateway | <1M calls/month | $0 |
| Gemini 2.5 Flash | AI inference | $0 (Free Tier) |
| Total | | ~$0/month |

---

## 👨‍💻 Author

Pham Thanh Lam — Network Security Student @ UIT
