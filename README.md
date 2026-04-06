# AutoCTI — Serverless Cyber Threat Intelligence Assistant

A 24/7 automated CTI pipeline built on AWS, powered by AI. AutoCTI
automatically collects cybersecurity threat intelligence, analyzes
CVEs and MITRE ATT&CK techniques, and delivers daily briefings via
Telegram — all within AWS Free Tier budget.

---

## System Architecture


![Uploading autocti_architecture.svg…]()


Flow:
1. User sends message via Telegram
2. Webhook hits API Gateway → message queued in SQS
3. EC2 Worker polls SQS → validates Whitelist & Rate Limit
4. Gemini AI analyzes threat → returns CTI report
5. Hunter (Playwright) crawls The Hacker News daily at 8AM GMT+7
6. AI summarizes news → pushes briefing to Telegram via Cronjob

---

## Features

- Event-Driven & Long Polling — API Gateway queues messages to SQS, Worker uses Long Polling to optimize API calls and reduce CPU idle load
- Security First — IAM Role (no hardcoded credentials), Whitelist, Rate Limiting
- AI Persona — Thien Nhan Tuyet CTI analyst with structured threat analysis
- Daily Briefing — Automated 8AM news crawl with CVE & MITRE ATT&CK mapping
- FinOps Optimized — Entire stack runs within AWS Free Tier (~$0/month)
- Docker — Fully containerized for portability and reproducibility

---

## Tech Stack

| Layer | Technology |
|---|---|
| Cloud Infrastructure | AWS EC2, SQS, DynamoDB, API Gateway, IAM |
| AI Engine | Google Gemini 2.5 Flash via LangChain |
| Web Automation | Playwright (Headless Chromium) |
| Runtime | Python 3.11, Docker |
| Messaging | Telegram Bot API |
| Scheduling | Linux Cronjob |

---

autocti/
├── src/
│   ├── worker.py       # SQS listener + AI response engine
│   ├── hunter.py       # Web crawler + daily briefing
│   ├── morning.py      # 7AM greeting scheduler
│   └── goodnight.py    # 12AM rest reminder
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key
ALLOWED_CHAT_IDS=your_telegram_chat_id
SQS_QUEUE_URL=your_sqs_queue_url

---

## Known Limitations & Roadmap

### Current Limitations (v1.0)

- Stateless architecture — AI has no memory of previous messages
- No real-time web search in worker (only hunter has Playwright)
- Hallucination risk with niche/local Vietnamese products not in training data

### Roadmap (v2.0)

- [ ] LangChain Memory + DynamoDB for conversation context
- [ ] RAG (Retrieval-Augmented Generation) with Vector DB
- [ ] Tavily Search API integration for real-time web search in worker
- [ ] NVD API integration for automated CVE tracking

---

## Cost Estimate

| Service | Usage | Cost |
|---|---|---|
| EC2 t2.micro | 24/7 | $0 (Free Tier 750h/month) |
| Amazon SQS | <1M req/month | $0 |
| DynamoDB | <25GB | $0 |
| API Gateway | <1M calls/month | $0 |
| Gemini 2.5 Flash | AI inference | $0 (Free Tier) |
| Total | | ~$0/month |

---

## Author

Pham Thanh Lam — Network Security Student @ UIT

## Project Structure
