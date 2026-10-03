import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

logger = logging.getLogger(__name__)

# --- Telegram Bot & Business Connections ---
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()

# Business connection IDs (Telegram Business ulanish ID'lari)
BUSINESS_CONNECTION_RECEPTION_ID: str = os.getenv("BUSINESS_CONNECTION_RECEPTION_ID", "").strip()
BUSINESS_CONNECTION_SALES_ID: str = os.getenv("BUSINESS_CONNECTION_SALES_ID", "").strip()

# --- Telegram Kanallar va Chatlar ---
def _parse_int(var_name: str, default: int = 0) -> int:
    val = os.getenv(var_name, "").strip()
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        logger.warning("Noto'g'ri butun son formati %s='%s'. Default %s ishlatiladi.", var_name, val, default)
        return default

ADMIN_KNOWLEDGE_CHANNEL_ID: int = _parse_int("ADMIN_KNOWLEDGE_CHANNEL_ID", 0)
SALES_KNOWLEDGE_CHANNEL_ID: int = _parse_int("SALES_KNOWLEDGE_CHANNEL_ID", 0)
FUNNEL_CHANNEL_ID: int = _parse_int("FUNNEL_CHANNEL_ID", 0)
ADMIN_CHAT_ID: int = _parse_int("ADMIN_CHAT_ID", 0)

# ADMIN_IDS: vergul bilan ajratilgan admin Telegram user ID'lari (masalan: 111111,222222)
def _parse_admin_ids() -> set[int]:
    raw = os.getenv("ADMIN_IDS", "").strip()
    if not raw:
        return set()
    result = set()
    for item in raw.split(","):
        cleaned = item.strip()
        if cleaned.isdigit() or (cleaned.startswith("-") and cleaned[1:].isdigit()):
            result.add(int(cleaned))
    return result

ADMIN_IDS: set[int] = _parse_admin_ids()

# --- DeepSeek LLM ---
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()

# --- Ishga tushirish rejimi ---
RUN_MODE: str = os.getenv("RUN_MODE", "polling").strip().lower()
WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "").strip().rstrip("/")
WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "").strip()
PORT: int = _parse_int("PORT", 8080)

# --- Lokal holat fayllari ---
LEAD_STATE_PATH: str = os.getenv("LEAD_STATE_PATH", "./data/lead_state.json").strip()
KNOWLEDGE_CACHE_PATH: str = os.getenv("KNOWLEDGE_CACHE_PATH", "./data/knowledge_cache.json").strip()
CONVERSATION_HISTORY_LIMIT: int = _parse_int("CONVERSATION_HISTORY_LIMIT", 20)

# Inson muloqotga aralashganda botni avtomatik kutish vaqti (daqiqalarda)
HUMAN_TAKEOVER_TIMEOUT_MINUTES: int = _parse_int("HUMAN_TAKEOVER_TIMEOUT_MINUTES", 30)

# Logging darajasi
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").strip().upper()


def get_role_by_business_connection_id(connection_id: str | None) -> str:
    """
    business_connection_id orqali rolni aniqlaydi.
    Agar alohida connection ID'lar berilmagan bo'lsa, 'combined' (Reception + Sales)
    roli ishlatiladi — bot ham qabulxona, ham sotuvchi bo'lib to'liq xizmat ko'rsatadi.
    """
    if BUSINESS_CONNECTION_RECEPTION_ID and connection_id == BUSINESS_CONNECTION_RECEPTION_ID:
        return "reception"
    if BUSINESS_CONNECTION_SALES_ID and connection_id == BUSINESS_CONNECTION_SALES_ID:
        return "sales"

    return "combined"


def validate_config(strict: bool = False) -> list[str]:
    """
    Konfiguratsiya xatolarini tekshiradi va ogohlantirishlar ro'yxatini qaytaradi.
    """
    issues = []
    if not BOT_TOKEN:
        issues.append("BOT_TOKEN ko'rsatilmagan!")
    if not DEEPSEEK_API_KEY:
        issues.append("DEEPSEEK_API_KEY ko'rsatilmagan!")
    if not ADMIN_CHAT_ID:
        issues.append("ADMIN_CHAT_ID ko'rsatilmagan (Bildirishnomalar guruhi yoki Admin ID).")
    if not FUNNEL_CHANNEL_ID:
        issues.append("FUNNEL_CHANNEL_ID ko'rsatilmagan (Savdo varonkasi kanali).")

    if RUN_MODE == "webhook" and not WEBHOOK_URL:
        issues.append("RUN_MODE=webhook tanlangan, lekin WEBHOOK_URL kiritilmagan!")

    if issues:
        for issue in issues:
            logger.warning("[CONFIG OGOHLANTIRISH] %s", issue)

    return issues
