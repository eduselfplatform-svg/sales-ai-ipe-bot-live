import json
import logging
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

import config

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_state_cache: dict[str, dict[str, Any]] | None = None


def _ensure_dir(filepath: str) -> None:
    """Fayl joylashgan katalogni mavjudligini ta'minlaydi."""
    path = Path(filepath)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)


def load_state() -> dict[str, dict[str, Any]]:
    """lead_state.json faylidan holatni yuklaydi."""
    global _state_cache
    with _lock:
        if _state_cache is not None:
            return _state_cache

        filepath = config.LEAD_STATE_PATH
        if not os.path.exists(filepath):
            logger.info("lead_state.json topilmadi (%s), yangi bo'sh holat yaratiladi.", filepath)
            _state_cache = {}
            return _state_cache

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    _state_cache = {}
                else:
                    _state_cache = json.loads(content)
            logger.info("lead_state.json muvaffaqiyatli yuklandi: %d ta lead.", len(_state_cache))
        except Exception as e:
            logger.error("lead_state.json o'qishda xatolik yuz berdi: %s. Bo'sh holat ishlatiladi.", e)
            _state_cache = {}

        return _state_cache


def save_state() -> None:
    """lead_state.json faylini xavfsiz (atomik) tarzda saqlaydi."""
    global _state_cache
    with _lock:
        if _state_cache is None:
            return

        filepath = config.LEAD_STATE_PATH
        _ensure_dir(filepath)
        dir_name = os.path.dirname(os.path.abspath(filepath))

        try:
            # Atomik yozish: avval vaqtinchalik faylga yozamiz, so'ng almashtiramiz
            with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
                json.dump(_state_cache, tf, ensure_ascii=False, indent=2)
                temp_name = tf.name

            # Windows va Linux da atomik almashtirish
            os.replace(temp_name, filepath)
        except Exception as e:
            logger.error("lead_state.json saqlashda xatolik: %s", e)
            if "temp_name" in locals() and os.path.exists(temp_name):
                try:
                    os.remove(temp_name)
                except OSError:
                    pass


def get_lead(lead_id: int | str) -> dict[str, Any] | None:
    """Berilgan lead_id bo'yicha lead ma'lumotlarini qaytaradi."""
    state = load_state()
    str_id = str(lead_id)
    lead = state.get(str_id)
    if not lead:
        return None
    res = dict(lead)
    if "id" not in res:
        res["id"] = str_id
    return res


def get_or_create_lead(
    lead_id: int | str,
    name: str = "",
    username: str = "",
    role_context: str = "sales",
) -> tuple[dict[str, Any], bool]:
    """
    Leadni oladi yoki yangi yaratadi.
    Qaytaradi: (lead_dict, is_new: bool)
    """
    state = load_state()
    str_id = str(lead_id)
    is_new = False

    if str_id not in state:
        is_new = True
        state[str_id] = {
            "id": str_id,
            "name": name or f"Foydalanuvchi {str_id}",
            "username": username or "",
            "role_context": role_context,
            "stage": "new",
            "ai_enabled": True,
            "human_takeover": False,
            "last_human_message_at": None,
            "assigned_admin_id": None,
            "assigned_admin_name": None,
            "funnel_message_id": None,
            "interest_note": "",
            "note": "",
            "history": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        save_state()
    else:
        # Mavjud ma'lumotlarni yangilash (agar ism yoki username o'zgargan bo'lsa)
        changed = False
        if name and state[str_id].get("name") != name:
            state[str_id]["name"] = name
            changed = True
        if username and state[str_id].get("username") != username:
            state[str_id]["username"] = username
            changed = True
        if role_context and not state[str_id].get("role_context"):
            state[str_id]["role_context"] = role_context
            changed = True
        if changed:
            state[str_id]["updated_at"] = datetime.now().isoformat()
            save_state()

    return dict(state[str_id]), is_new


def update_lead(lead_id: int | str, **fields: Any) -> dict[str, Any]:
    """Lead maydonlarini yangilaydi va saqlaydi."""
    state = load_state()
    str_id = str(lead_id)

    if str_id not in state:
        lead, _ = get_or_create_lead(lead_id)
    else:
        lead = state[str_id]

    for key, value in fields.items():
        if value is not None:
            lead[key] = value

    lead["updated_at"] = datetime.now().isoformat()
    state[str_id] = lead
    save_state()
    return dict(lead)


def append_history(lead_id: int | str, role: str, content: str) -> None:
    """
    Lead suhbat tarixiga yangi xabar qo'shadi va
    CONVERSATION_HISTORY_LIMIT dan oshsa eskisini qirqadi.
    """
    state = load_state()
    str_id = str(lead_id)

    if str_id not in state:
        get_or_create_lead(lead_id)

    lead = state[str_id]
    history: list[dict[str, str]] = lead.get("history", [])
    history.append({"role": role, "content": content})

    # Limit bo'yicha qirqish
    limit = config.CONVERSATION_HISTORY_LIMIT
    if limit > 0 and len(history) > limit:
        history = history[-limit:]

    lead["history"] = history
    lead["updated_at"] = datetime.now().isoformat()
    state[str_id] = lead
    save_state()


def get_conversation_history(lead_id: int | str) -> list[dict[str, str]]:
    """Lead suhbat tarixini qaytaradi."""
    lead = get_lead(lead_id)
    if not lead:
        return []
    return list(lead.get("history", []))


def is_ai_active_for_lead(lead_id: int | str) -> tuple[bool, str]:
    """
    Ushbu lead uchun AI avtomatik javob berishi kerakmi yoki yo'qligini tekshiradi.
    Qaytaradi: (is_active: bool, reason: str)
    """
    lead = get_lead(lead_id)
    if not lead:
        return True, "Yangi lead"

    # 1. Admin tomonidan to'g'ridan-to'g'ri o'chirilgan bo'lsa
    if lead.get("ai_enabled") is False:
        return False, "AI qo'lda to'xtatilgan"

    # 2. Xodim yaqinda mijozga o'zi yozgan bo'lsa (Human takeover)
    last_human = lead.get("last_human_message_at")
    if last_human and lead.get("human_takeover", False):
        try:
            last_dt = datetime.fromisoformat(last_human)
            elapsed_minutes = (datetime.now() - last_dt).total_seconds() / 60.0
            timeout = config.HUMAN_TAKEOVER_TIMEOUT_MINUTES
            if elapsed_minutes < timeout:
                remaining = int(timeout - elapsed_minutes)
                return False, f"Xodim shaxsan muloqot qilmoqda ({remaining} daqiqa qoldi)"
        except Exception:
            pass

    return True, "AI faol"


def set_ai_enabled(lead_id: int | str, enabled: bool) -> dict[str, Any]:
    """Lead uchun AI ni yoqadi yoki o'chiradi."""
    state = load_state()
    str_id = str(lead_id)
    if str_id not in state:
        get_or_create_lead(lead_id)

    updates: dict[str, Any] = {
        "ai_enabled": enabled,
        "human_takeover": not enabled,
    }
    if enabled:
        updates["last_human_message_at"] = None

    return update_lead(lead_id, **updates)


def record_human_reply(lead_id: int | str, text: str) -> dict[str, Any]:
    """
    Xodim (biznes profil egasi) mijozga shaxsan javob yozganda chaqiriladi.
    Tarixga qo'shadi va AI ni avtomatik ravishda kutish (takeover) rejimiga o'tkazadi.
    """
    append_history(lead_id, "assistant", text)
    return update_lead(
        lead_id,
        human_takeover=True,
        last_human_message_at=datetime.now().isoformat(),
    )
