import asyncio
import logging
import re
from typing import Any
import yaml
from openai import OpenAI

import config
from prompts import build_system_prompt

logger = logging.getLogger(__name__)

# LEAD_META blokini topish uchun moslashuvchan regex
META_RE = re.compile(r"---LEAD_META---\s*\n?(.*?)\n?\s*---END---", re.DOTALL)

ALLOWED_STAGES = {
    "new",
    "in_conversation",
    "course_recommended",
    "demo_invited",
    "demo_confirmed",
    "won",
    "lost",
}


def get_openai_client() -> OpenAI:
    """OpenAI mijozini DeepSeek sozlamalari bilan yaratadi."""
    return OpenAI(
        api_key=config.DEEPSEEK_API_KEY,
        base_url=config.DEEPSEEK_BASE_URL,
        timeout=35.0,
    )


def parse_llm_response(raw: str) -> tuple[str, dict[str, Any]]:
    """
    LLM xom javobidan mijozga ko'rsatiladigan toza matn va
    yashirin LEAD_META parametrlarini ajratib oladi.

    Qaytaradi: (customer_text, meta_dict)
    """
    if not raw:
        return "", {}

    match = META_RE.search(raw)
    if not match:
        # Agar blok topilmasa, lekin ---LEAD_META--- so'zi bo'lsa, qirqib tashlaymiz
        clean_text = raw.split("---LEAD_META---")[0].strip()
        return clean_text, {}

    # Mijozga ko'rinadigan matn blokdan oldingi qism
    customer_text = raw[:match.start()].strip()

    meta_raw = match.group(1).strip()
    meta: dict[str, Any] = {}

    try:
        loaded = yaml.safe_load(meta_raw)
        if isinstance(loaded, dict):
            meta = loaded
    except Exception as e:
        logger.warning("LEAD_META YAML parse xatosi: %s. Xom blok: %s", e, meta_raw)

    # Validatsiya va tozalash
    stage = str(meta.get("stage", "")).strip().lower()
    if stage in ALLOWED_STAGES:
        meta["stage"] = stage
    else:
        if stage:
            logger.warning("Ruxsat berilmagan stage: '%s'", stage)
        meta["stage"] = None

    # handoff_needed bool ekanligini ta'minlash
    handoff = meta.get("handoff_needed")
    if isinstance(handoff, str):
        meta["handoff_needed"] = handoff.strip().lower() in ("true", "1", "yes", "ha")
    elif isinstance(handoff, bool):
        meta["handoff_needed"] = handoff
    else:
        meta["handoff_needed"] = False

    # interest va note tozalash
    if "interest" in meta and meta["interest"] is not None:
        meta["interest"] = str(meta["interest"]).strip()
    if "note" in meta and meta["note"] is not None:
        meta["note"] = str(meta["note"]).strip()

    return customer_text, meta


def _sync_deepseek_call(
    role: str,
    knowledge: str,
    history: list[dict[str, str]],
    user_message: str,
) -> str:
    """Sinxron chat completion so'rovi (asyncio.to_thread ichida chaqiriladi)."""
    client = get_openai_client()
    system_prompt = build_system_prompt(role, knowledge)

    # Tarixdan faqat user va assistant rollarini filtrlaymiz
    clean_history = []
    for h in history:
        r = h.get("role")
        c = h.get("content", "")
        if r in ("user", "assistant") and c:
            clean_history.append({"role": r, "content": c})

    messages = [
        {"role": "system", "content": system_prompt},
        *clean_history,
        {"role": "user", "content": user_message},
    ]

    response = client.chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=messages,
        temperature=0.4,
        max_tokens=700,
    )

    choice = response.choices[0]
    return choice.message.content or ""


async def ask_deepseek(
    role: str,
    knowledge: str,
    history: list[dict[str, str]],
    user_message: str,
) -> tuple[str, dict[str, Any]]:
    """
    DeepSeek API ga asinxron so'rov yuboradi (1 marta avtomatik retry bilan).
    Muvaffaqiyatli bo'lsa (customer_text, meta) qaytaradi.
    """
    last_error: Exception | None = None

    for attempt in range(1, 3):
        try:
            logger.info("DeepSeek ga so'rov yuborilmoqda (urinish %d/2, rol=%s)...", attempt, role)
            raw_response = await asyncio.to_thread(
                _sync_deepseek_call,
                role,
                knowledge,
                history,
                user_message,
            )
            customer_text, meta = parse_llm_response(raw_response)
            logger.info(
                "DeepSeek javobi olindi: text_len=%d, stage=%s, handoff=%s",
                len(customer_text),
                meta.get("stage"),
                meta.get("handoff_needed"),
            )
            return customer_text, meta
        except Exception as e:
            last_error = e
            logger.warning("DeepSeek API xatoligi (urinish %d): %s", attempt, e)
            if attempt == 1:
                await asyncio.sleep(1.5)

    logger.error("DeepSeek so'rovi 2 ta urinishdan so'ng muvaffaqiyatsiz bo'ldi: %s", last_error)
    raise last_error if last_error else RuntimeError("DeepSeek javob bermadi")
