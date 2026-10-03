import json
import logging
import os
import threading
from pathlib import Path

import config

logger = logging.getLogger(__name__)

_lock = threading.Lock()

# message_id -> matn ko'rinishida saqlash (tahrirlangan postlar avtomatik yangilanishi uchun)
_knowledge_cache: dict[str, dict[str, str]] = {
    "admin": {},
    "sales": {}
}
_loaded = False


def _ensure_dir(filepath: str) -> None:
    path = Path(filepath)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)


DEFAULT_DEMO_KNOWLEDGE = {
    "admin": {
        "demo_admin_1": """🏫 IPE School (Innovative Professional Education) haqida umumiy ma'lumot:

📍 Bosh filial manzili: Toshkent shahri, Chilonzor tumani, Bunyodkor shoh ko'chasi, 42-uy.
Mo'ljal: Mirzo Ulug'bek metro bekati (2 daqiqalik piyoda yo'l).

📍 2-filial (Yunusobod): Toshkent shahri, Yunusobod tumani, Amir Temur shoh ko'chasi, 107-uy (Shahriston metro bekati).

🕒 Ish vaqti:
Dushanba – Shanba: 09:00 dan 20:00 gacha
Yakshanba: Dam olish kuni

📞 Aloqa raqamlari: +998 (71) 200-00-55, +998 (90) 123-45-67
🌐 Veb-sayt: ipeschool.uz""",

        "demo_admin_2": """📋 Qabul shartlari, hujjatlar va to'lov usullari:

1. Hujjatlar:
- Shaxsni tasdiqlovchi hujjat (Pasport / ID-karta yoki haydovchilik guvohnomasi).
- 16 yoshgacha bo'lgan o'quvchilar uchun: ota-onaning pasport nusxasi va o'quvchining tug'ilganlik haqida guvohnomasi.
- Shartnoma rasmiylashtiriladi.

2. To'lov usullari:
- Payme, Click, Uzum Bank mobil ilovalari orqali
- Bank o'tkazmasi yoki naqd pul
- Har oy boshida oyma-oy to'lov qilinadi.

3. O'quv muhiti va qoidalar:
- Darslar zamonaviy kompyuterlar va proyektorlar bilan jihozlangan xonalarda o'tiladi.
- Har bir o'quvchiga mentorlar alohida yordam beradi.
- Dars qoldirilganda video yozuvlar va qo'shimcha dars tashkil etiladi."""
    },
    "sales": {
        "demo_sales_1": """💻 IT Kurslari va Narxlar:

1️⃣ Python Backend Dasturlash:
- Davomiyligi: 6 oy (Haftada 3 kun, 2 soatdan)
- Mundarija: Python Asoslari, OOP, Algoritmlar, PostgreSQL, Django, FastAPI, Celery, Docker, REST API, Telegram Botlar.
- Narxi: 1,500,000 so'm/oy (kurs uchun to'liq to'langanda 15% chegirma: 7,650,000 so'm).
- O'qituvchilar: 4+ yillik tajribaga ega senior dasturchilar.

2️⃣ Frontend Dasturlash (React & Next.js):
- Davomiyligi: 5 oy (Haftada 3 kun, 2 soatdan)
- Mundarija: HTML5, CSS3, JavaScript (ES6+), TypeScript, React.js, Next.js, Redux Toolkit, Tailwind CSS.
- Narxi: 1,400,000 so'm/oy.

3️⃣ Bolalar va o'smirlar uchun IT-Foundation (9-14 yosh):
- Davomiyligi: 4 oy (Haftada 3 kun, 1.5 soatdan)
- Mundarija: Kompyuter savodxonligi, Mantiq, Scratch, Robottotexnika, Python for Kids.
- Narxi: 950,000 so'm/oy.""",

        "demo_sales_2": """🇬🇧 Xorijiy Tillar va Boshqa Yo'nalishlar:

1️⃣ General English & IELTS:
- Davomiyligi: Har bir daraja 3 oy (Beginner dan IELTS 7.5+ gacha)
- Darslar: Haftada 3 kun 1.5 soatdan
- Qo'shimcha bepul: Har shanba Speaking Club (Native speaker bilan) va haftalik Mock imtihonlar
- Narxi: 850,000 so'm/oy.

2️⃣ Prezident maktabi va Litseylarga tayyorgarlik (Matematika & Mantiq):
- Davomiyligi: 6 oy
- Narxi: 800,000 so'm/oy.""",

        "demo_sales_3": """🎁 BEPUL DEMO (SINOV) DARSI VA AKSIYALAR:

🔹 Bepul Demo Dars:
Har bir yangi mijoz uchun istalgan kursimiz bo'yicha 1-dars mutlaqo BEPUL!
Demo darsda o'quvchi markazimizga kelib, ustoz bilan shaxsan tanishadi, dars sifatini baholaydi va o'zining darajasini aniqlaydi.
Demo darsga yozilish uchun faqat Ismingiz, qiziqqan yo'nalishingiz va sizga qulay vaqtni aytsangiz bas!

🔥 Amaldagi Chegirmalar:
• Demo dars kuni shartnoma tuzganlarga 1-oy uchun 15% maxsus chegirma!
• 'Do'stingni olib kel' aksiyasi: har bir taklif qilingan do'st uchun 10% doimiy keshbek/chegirma."""
    }
}


def load_knowledge_cache() -> None:
    """Fayldagi keshni yuklaydi, agar bo'sh bo'lsa demo ma'lumotlarni o'rnatadi."""
    global _loaded, _knowledge_cache
    with _lock:
        if _loaded:
            return

        filepath = config.KNOWLEDGE_CACHE_PATH
        loaded_from_file = False
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        _knowledge_cache["admin"] = data.get("admin", {})
                        _knowledge_cache["sales"] = data.get("sales", {})
                        loaded_from_file = True
                        logger.info(
                            "Bilim keshi yuklandi: Admin=%d ta post, Sales=%d ta post",
                            len(_knowledge_cache["admin"]),
                            len(_knowledge_cache["sales"]),
                        )
            except Exception as e:
                logger.error("Bilim keshini o'qishda xatolik: %s", e)

        # Agar kesh bo'sh bo'lsa, demo ma'lumotlarni o'rnatamiz
        if not _knowledge_cache.get("admin"):
            _knowledge_cache["admin"] = dict(DEFAULT_DEMO_KNOWLEDGE["admin"])
        if not _knowledge_cache.get("sales"):
            _knowledge_cache["sales"] = dict(DEFAULT_DEMO_KNOWLEDGE["sales"])

        if not loaded_from_file:
            # Faylga saqlab qo'yamiz
            _ensure_dir(filepath)
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(_knowledge_cache, f, ensure_ascii=False, indent=2)
                logger.info("Demo bilim ma'lumotlari keshga saqlandi.")
            except Exception as e:
                logger.error("Demo bilim ma'lumotlarini saqlashda xato: %s", e)

        _loaded = True


def save_knowledge_cache() -> None:
    """Bilim keshini faylga saqlaydi."""
    with _lock:
        filepath = config.KNOWLEDGE_CACHE_PATH
        _ensure_dir(filepath)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(_knowledge_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Bilim keshini saqlashda xatolik: %s", e)


def append_knowledge(category: str, message_id: int | str, text: str) -> None:
    """
    Yangi yoki tahrirlangan kanal postini bilim keshiga qo'shadi.
    category: 'admin' yoki 'sales'
    """
    load_knowledge_cache()
    if not text or not text.strip():
        return

    cat = category.lower()
    if cat not in _knowledge_cache:
        _knowledge_cache[cat] = {}

    with _lock:
        _knowledge_cache[cat][str(message_id)] = text.strip()

    save_knowledge_cache()
    logger.info("Bilim yangilandi [%s]: Post ID %s (%d belgi)", cat, message_id, len(text))


def remove_knowledge(category: str, message_id: int | str) -> None:
    """O'chirilgan postni keshdan olib tashlaydi."""
    load_knowledge_cache()
    cat = category.lower()
    with _lock:
        if cat in _knowledge_cache and str(message_id) in _knowledge_cache[cat]:
            del _knowledge_cache[cat][str(message_id)]
            save_knowledge_cache()
            logger.info("Bilim o'chirildi [%s]: Post ID %s", cat, message_id)


def get_raw_knowledge_text(category: str) -> str:
    """Bitta kategoriya (admin yoki sales) ga tegishli barcha postlar matnini birlashtiradi."""
    load_knowledge_cache()
    cat = category.lower()
    posts = _knowledge_cache.get(cat, {})
    if not posts:
        return ""
    return "\n\n---\n\n".join(posts.values())


def get_knowledge(role: str) -> str:
    """
    DeepSeek LLM uchun rolga moslashtirilgan bilim matnini shakllantiradi.
    - role="reception" -> Admin bilimi asosiy, Kurslar qisqa ma'lumot sifatida.
    - role="sales" -> Sales bilimi asosiy, Admin ma'lumotlari qo'shimcha kontekst sifatida.
    - role="combined" -> Admin va Sales bilimlari to'liq uyg'unlashgan holda.
    """
    load_knowledge_cache()
    admin_text = get_raw_knowledge_text("admin").strip()
    sales_text = get_raw_knowledge_text("sales").strip()

    role_lower = role.lower() if role else "combined"

    if role_lower == "reception":
        sections = []
        if admin_text:
            sections.append(f"【ASOSIY BILIM - QABULXONA VA UMUMIY QOIDALAR】\n{admin_text}")
        else:
            sections.append("【ASOSIY BILIM - QABULXONA】\n(Hozircha admin kanalida yangi ma'lumot yuklanmagan)")

        if sales_text:
            sections.append(f"【QO'SHIMCHA KONTEKST - KURSLAR VA DASTURLAR】\n{sales_text}")

        return "\n\n".join(sections)

    elif role_lower == "sales":
        sections = []
        if sales_text:
            sections.append(f"【ASOSIY BILIM - KURSLAR, NARXLAR VA AKSIYALAR】\n{sales_text}")
        else:
            sections.append("【ASOSIY BILIM - KURSLAR】\n(Hozircha sotuv kanalida kurslar bo'yicha ma'lumot yuklanmagan)")

        if admin_text:
            sections.append(f"【QO'SHIMCHA KONTEKST - MANZIL, ISH VAQTI VA MAKTAB QOIDALARI】\n{admin_text}")

        return "\n\n".join(sections)

    else:  # combined
        sections = []
        if admin_text:
            sections.append(f"【QABULXONA VA UMUMIY MA'LUMOTLAR (Manzil, ish vaqti, qoidalar)】\n{admin_text}")
        if sales_text:
            sections.append(f"【KURSLAR, NARXLAR, AKSIYALAR VA DEMO DARS (Sotuv bilimlari)】\n{sales_text}")

        return "\n\n".join(sections)
