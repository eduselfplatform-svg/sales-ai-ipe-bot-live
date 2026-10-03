import html
import logging
from telegram import Update
from telegram.ext import ContextTypes

import config
import knowledge
import lead_state
from funnel import STAGE_LABELS

logger = logging.getLogger(__name__)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Bot shaxsiy chatida /start bosilganda:
    Admin ro'yxatdan o'tadi va unga bot proaktiv DM yubora olishi faollashadi.
    """
    user = update.effective_user
    if not user:
        return

    user_id = user.id
    user_name = user.full_name
    is_admin = not config.ADMIN_IDS or user_id in config.ADMIN_IDS

    logger.info("Foydalanuvchi /start bosdi: %s (ID: %s, Admin: %s)", user_name, user_id, is_admin)

    greeting = (
        f"Assalomu alaykum, <b>{html.escape(user_name)}</b>!\n\n"
        f"🤖 <b>IPE School Savdo va Qabulxona AI Boti</b> tizimiga xush kelibsiz.\n\n"
        f"📌 Sizning Telegram ID: <code>{user_id}</code>\n"
    )

    if is_admin:
        greeting += (
            "✅ <b>Siz tizim administratori sifatida muvaffaqiyatli ro'yxatdan o'tdingiz!</b>\n"
            "Endi sizga biriktirilgan mijozlar xabar yozganda yoki eskalatsiya yuz berganda, "
            "bot sizga to'g'ridan-to'g'ri shaxsiy xabar (DM) yubora oladi.\n\n"
            "Mavjud buyruqlar:\n"
            "🔹 /status — Tizim holati va savdo varonkasi statistikasi\n"
            "🔹 /test_dm — Shaxsiy bildirishnoma yetib kelishini sinab ko'rish\n"
            "🔹 /help — Qo'llanma va yordam"
        )
    else:
        greeting += (
            "ℹ️ Ushbu bot IPE School Telegram Business hisoblari orqali avtomatik muloqot qilish "
            "va savdo jarayonlarini boshqarish uchun mo'ljallangan."
        )

    await update.message.reply_text(greeting, parse_mode="HTML")


async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /status komandasi: Savdo varonkasi statistikasi va bot holatini chiqaradi.
    """
    user = update.effective_user
    if not user:
        return

    if config.ADMIN_IDS and user.id not in config.ADMIN_IDS:
        await update.message.reply_text("Kechirasiz, faqat xodimlar tizim holatini ko'rishi mumkin.")
        return

    leads = lead_state.load_state()
    total_leads = len(leads)

    # Bosqichlar bo'yicha taqsimot
    stage_counts = {k: 0 for k in STAGE_LABELS}
    for lead in leads.values():
        st = lead.get("stage", "new")
        stage_counts[st] = stage_counts.get(st, 0) + 1

    stage_lines = []
    for st_key, label in STAGE_LABELS.items():
        count = stage_counts.get(st_key, 0)
        stage_lines.append(f"  • {label}: <b>{count}</b>")

    admin_knowledge_count = len(knowledge._knowledge_cache.get("admin", {}))
    sales_knowledge_count = len(knowledge._knowledge_cache.get("sales", {}))

    text = (
        f"📊 <b>IPE School AI Boti — Tizim Holati</b>\n\n"
        f"👥 Jami leadlar (mijozlar): <b>{total_leads}</b> ta\n\n"
        f"📌 <b>Varonka bosqichlari bo'yicha:</b>\n"
        + "\n".join(stage_lines) + "\n\n"
        f"📚 <b>Bilim bazasi (Kanal postlari):</b>\n"
        f"  • Qabulxona (Admin): <b>{admin_knowledge_count}</b> ta post\n"
        f"  • Sotuv (Sales): <b>{sales_knowledge_count}</b> ta post\n\n"
        f"⚙️ <b>Sozlamalar:</b>\n"
        f"  • Rejim: <code>{config.RUN_MODE}</code>\n"
        f"  • LLM Model: <code>{config.DEEPSEEK_MODEL}</code>\n"
        f"  • Varonka kanali ID: <code>{config.FUNNEL_CHANNEL_ID or 'Sozlanmagan'}</code>\n"
        f"  • Admin chat ID: <code>{config.ADMIN_CHAT_ID or 'Sozlanmagan'}</code>"
    )

    await update.message.reply_text(text, parse_mode="HTML")


async def handle_test_dm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /test_dm komandasi: Admin bot bilan DM aloqasi ishlayotganini tekshiradi.
    """
    user = update.effective_user
    if not user:
        return

    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=(
                f"✅ <b>Sinov muvaffaqiyatli!</b>\n\n"
                f"Assalomu alaykum, {html.escape(user.full_name)}! "
                f"Sizga botdan to'g'ridan-to'g'ri xabar yuborish imkoniyati mavjud. "
                f"Mijozlaringiz xabar yozganda xabarnomalar shu yerga yetib keladi."
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Shaxsiy xabar yuborishda xato: {e}")


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help komandasi."""
    text = (
        "📖 <b>IPE School Savdo Boti — Ma'muriyat qo'llanmasi</b>\n\n"
        "1. <b>Telegram Business ulanishi:</b>\n"
        "   Telegram Premium obunangiz bo'lishi va Telegram ilovasida "
        "   <i>Sozlamalar ➡️ Telegram Business ➡️ Chatbots</i> bo'limidan ushbu botni ulab qo'yishingiz kerak.\n\n"
        "2. <b>Savdo Varonkasi:</b>\n"
        "   Mijozlar yozganda maxsus kanalda bitta interaktiv post hosil bo'ladi. "
        "   Xodimlar bosqich tugmalarini bosish orqali o'zlarini mas'ul qilib biriktirishlari mumkin.\n\n"
        "3. <b>Bilim bazasi:</b>\n"
        "   Qabulxona va Sotuv kanallariga yangi post tashlansa yoki tahrirlansa, "
        "   AI miyasi avtomatik ravishda yangi ma'lumotlarni o'zlashtiradi.\n\n"
        "Mavjud buyruqlar:\n"
        "/start — Botga ulanish / Ro'yxatdan o'tish\n"
        "/status — Varonka va tizim holati\n"
        "/test_dm — DM xabar yetib kelishini sinash"
    )
    await update.message.reply_text(text, parse_mode="HTML")
