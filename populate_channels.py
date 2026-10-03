"""
Admin va Sales bilim kanallarini demo ma'lumotlar bilan to'ldirish skripti.
"""
import asyncio
import logging
import sys

# Windows konsolida UTF-8 ni to'g'ri ko'rsatish
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from telegram import Bot
from telegram.error import TelegramError

import config
import knowledge

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def populate():
    print("=" * 60)
    print("IPE School — Bilim kanallariga demo ma'lumotlarni yuklash")
    print("=" * 60)

    if not config.BOT_TOKEN:
        print("❌ XATO: .env faylida BOT_TOKEN ko'rsatilmagan!")
        return

    # 1. Lokal keshni darhol to'ldirish
    knowledge.load_knowledge_cache()
    print("✅ Lokal bilim keshi (data/knowledge_cache.json) demo ma'lumotlar bilan to'ldirildi.")

    bot = Bot(config.BOT_TOKEN)
    me = await bot.get_me()
    print(f"🤖 Bot aniqlandi: @{me.username} ({me.first_name})")

    # 2. Admin bilim kanaliga yuborish
    admin_cid = config.ADMIN_KNOWLEDGE_CHANNEL_ID
    if admin_cid:
        print(f"\n📢 Admin bilim kanaliga ({admin_cid}) ma'lumotlar yuborilmoqda...")
        for key, text in knowledge.DEFAULT_DEMO_KNOWLEDGE["admin"].items():
            try:
                sent = await bot.send_message(chat_id=admin_cid, text=text)
                print(f"  ✅ Post yuborildi: Msg ID {sent.message_id} ({key})")
                await asyncio.sleep(1)
            except TelegramError as e:
                print(f"  ⚠️ Admin kanalga ({admin_cid}) yuborib bo'lmadi: {e}")
                print(f"     Iltimos, @{me.username} botini kanalga ADMINISTRATOR qilib qo'shing!")
                break
    else:
        print("⚠️ ADMIN_KNOWLEDGE_CHANNEL_ID sozlanmagan.")

    # 3. Sales bilim kanaliga yuborish
    sales_cid = config.SALES_KNOWLEDGE_CHANNEL_ID
    if sales_cid:
        print(f"\n📢 Sales bilim kanaliga ({sales_cid}) ma'lumotlar yuborilmoqda...")
        for key, text in knowledge.DEFAULT_DEMO_KNOWLEDGE["sales"].items():
            try:
                sent = await bot.send_message(chat_id=sales_cid, text=text)
                print(f"  ✅ Post yuborildi: Msg ID {sent.message_id} ({key})")
                await asyncio.sleep(1)
            except TelegramError as e:
                print(f"  ⚠️ Sales kanalga ({sales_cid}) yuborib bo'lmadi: {e}")
                print(f"     Iltimos, @{me.username} botini kanalga ADMINISTRATOR qilib qo'shing!")
                break
    else:
        print("⚠️ SALES_KNOWLEDGE_CHANNEL_ID sozlanmagan.")

    print("\n" + "=" * 60)
    print("Yakunlandi! Bilim bazasi tayyor.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(populate())
