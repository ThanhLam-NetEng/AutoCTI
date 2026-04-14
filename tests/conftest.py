import sys
from unittest.mock import MagicMock

# ── AWS ──────────────────────────────────────────────
sys.modules['boto3'] = MagicMock()
sys.modules['boto3.dynamodb'] = MagicMock()
sys.modules['boto3.dynamodb.conditions'] = MagicMock()

# ── LangChain / LangGraph ────────────────────────────
sys.modules['langchain_tavily'] = MagicMock()
sys.modules['langgraph'] = MagicMock()
sys.modules['langgraph.prebuilt'] = MagicMock()
sys.modules['langchain_google_genai'] = MagicMock()

# ── Playwright ───────────────────────────────────────
sys.modules['playwright'] = MagicMock()
sys.modules['playwright.sync_api'] = MagicMock()

# ── Misc ─────────────────────────────────────────────
sys.modules['dotenv'] = MagicMock()
sys.modules['custom_memory'] = MagicMock()
