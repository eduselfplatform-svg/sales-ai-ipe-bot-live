import html
import logging
from telegram import Update, User
from telegram.ext import ContextTypes

import config
import funnel
import knowledge
import lead_state
from llm_client import ask_deepseek

logger = logging.getLogger(__name__)


async def handle_business_connection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    business_connection yangilanishlarini qayta ishlaydi.
    Xodim botni ulaganda yoki aloqani uzganda ishga tushadi.
    """
    conn = update.business_connection
    if not conn:
        return

    user = conn.user
    conn_id = conn.id
    is_enabled = conn.is_enabled
    user_name = user.full_name if user else "Noma'lum"
    username_str = f"@{user.username}" if user and user.username else ""

    logger.info(
        "Business Connection yangilandi: ID=%s, User=%s (%s), is_enabled=%s",
        conn_id, user_name, username_str, is_enabled
    )

    if not config.ADMIN_CHAT_ID:
        return

    if is_enabled:
        msg = (
            f"✅ <b>Telegram Business ulanish faollashtirildi!</b>\n\n"
            f"👤 Xodim: <b>{html.escape(user_name)}</b> {username_str}\n"
            f"🆔 Connection ID: <code>{conn_id}</code>\n"
            f"💬 Ushbu profil orqali mijozlar bilan avtomatik muloqot boshlanadi."
        )
    else:
        msg = (
            f"⚠️ <b>DIQQAT: Telegram Business ulanish bekor qilindi!</b>\n\n"
            f"👤 Xodim: <b>{html.escape(user_name)}</b> {username_str}\n"
            f"🆔 Connection ID: <code>{conn_id}</code>\n"
            f"❌ Bot bu profil orqali xabarlarga javob bera olmaydi."
        )

    try:
        await context.bot.send_message(
            chat_id=config.ADMIN_CHAT_ID,
            text=msg,
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Admin chatga business_connection bildirishnomasini yuborishda xato: %s", e)


async def process_customer_message(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    sender: User,
    incoming_text: str,
    conn_id: str | None = None,
    reply_to_msg: object = None,
) -> None:
    """
    Mijoz xabarini qayta ishlash uchun umumiy funksiya:
    Ham Telegram Business, ham botga to'g'ridan-to'g'ri yozilgan xabarlar uchun ishlaydi.
    """
    lead_id = sender.id
    lead_name = sender.full_name or f"Mijoz {lead_id}"
    lead_username = sender.username or ""

    if not incoming_text.strip():
        logger.info("Mijoz %s bo'sh yoki media xabar yubordi.", lead_id)
        fallback_prompt = (
            "Assalomu alaykum! Iltimos, savolingizni matn ko'rinishida yozib yuborsangiz, "
            "sizga tezroq yordam bera olamiz."
        )
        try:
            if conn_id:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=fallback_prompt,
                    business_connection_id=conn_id,
                )
            elif reply_to_msg and hasattr(reply_to_msg, "reply_text"):
                await reply_to_msg.reply_text(fallback_prompt)
            else:
                await context.bot.send_message(chat_id=chat_id, text=fallback_prompt)
        except Exception as e:
            logger.error("Bo'sh xabarga javob yuborishda xato: %s", e)
        return

    # Rolni aniqlash
    role = config.get_role_by_business_connection_id(conn_id)
    source_type = "Telegram Business" if conn_id else "Bot Direct Chat"
    logger.info(
        "Mijozdan xabar keldi [%s]: Lead=%s (%s), Rol=%s, Matn='%s'...",
        source_type, lead_id, lead_name, role, incoming_text[:60]
    )

    # Lead ma'lumotlarini olish yoki yaratish
    lead, is_new = lead_state.get_or_create_lead(
        lead_id=lead_id,
        name=lead_name,
        username=lead_username,
        role_context=role,
    )

    # Varonka kanalida post mavjudligini ta'minlash
    if is_new or not lead.get("funnel_message_id"):
        await funnel.sync_funnel_post(context.bot, lead_id, lead)

    # Suhbat tarixiga yangi xabarni qo'shish
    lead_state.append_history(lead_id, "user", incoming_text)

    # AI holatini tekshirish: agar xodim muloqot qilayotgan bo'lsa yoki AI o'chirilgan bo'lsa
    ai_active, pause_reason = lead_state.is_ai_active_for_lead(lead_id)
    if not ai_active:
        logger.info("Mijoz (%s) yozdi, lekin AI nofaol (%s). LLM chaqirilmaydi.", lead_id, pause_reason)
        await funnel.sync_funnel_post(context.bot, lead_id, lead)
        await funnel.notify_admins(
            context.bot,
            lead,
            incoming_text,
            extra_alert=f"👤 <b>Xodim nazoratida:</b> {pause_reason}. AI xalaqit bermaslik uchun avtomatik javob bermadi."
        )
        return

    # Admin guruhiga bildirishnoma yuborish
    await funnel.notify_admins(context.bot, lead, incoming_text)

    # Suhbat tarixi va bilim matnini olish
    history = lead_state.get_conversation_history(lead_id)
    knowledge_text = knowledge.get_knowledge(role)

    # DeepSeek orqali javob olish (retry va xatoliklar bilan)
    try:
        customer_reply, meta = await ask_deepseek(
            role=role,
            knowledge=knowledge_text,
            history=history,
            user_message=incoming_text,
        )
    except Exception as e:
        logger.error("DeepSeek bilan ishlashda kutilmagan xatolik: %s", e)
        await funnel.notify_admins(
            context.bot,
            lead,
            incoming_text,
            extra_alert="⚠️ DeepSeek API javob bermadi! Iltimos, mijozga zudlik bilan qo'lda javob yozing."
        )
        fallback_msg = "Assalomu alaykum! Savolingiz qabul qilindi, mutaxassisimiz tez orada siz bilan bog'lanadi."
        try:
            if conn_id:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=fallback_msg,
                    business_connection_id=conn_id,
                )
            elif reply_to_msg and hasattr(reply_to_msg, "reply_text"):
                await reply_to_msg.reply_text(fallback_msg)
            else:
                await context.bot.send_message(chat_id=chat_id, text=fallback_msg)
        except Exception as send_err:
            logger.error("Fallback xabar yuborishda xato: %s", send_err)
        return

    # Assistant javobini tarixga qo'shish
    lead_state.append_history(lead_id, "assistant", customer_reply)

    # Agar LEAD_META qaytgan bo'lsa, lead holatini yangilash
    updated_fields = {}
    if meta.get("stage"):
        updated_fields["stage"] = meta["stage"]
    if meta.get("interest"):
        updated_fields["interest_note"] = meta["interest"]
    if meta.get("note"):
        updated_fields["note"] = meta["note"]

    if updated_fields:
        lead = lead_state.update_lead(lead_id, **updated_fields)

    # Varonka kanalidagi postni yangilash
    await funnel.sync_funnel_post(context.bot, lead_id, lead)

    # Agar eskalatsiya zarur bo'lsa (handoff_needed: true)
    if meta.get("handoff_needed"):
        logger.info("Eskalatsiya talab qilinmoqda: Lead=%s", lead_id)
        await funnel.notify_admins(
            context.bot,
            lead,
            incoming_text,
            extra_alert="🚨 <b>ESKALATSIYA:</b> Mijozga inson (administrator) aralashuvi zarur!"
        )

    # Mijozga javob yuborish
    try:
        if conn_id:
            await context.bot.send_message(
                chat_id=chat_id,
                text=customer_reply,
                business_connection_id=conn_id,
            )
        elif reply_to_msg and hasattr(reply_to_msg, "reply_text"):
            await reply_to_msg.reply_text(customer_reply)
        else:
            await context.bot.send_message(chat_id=chat_id, text=customer_reply)

        logger.info("Mijoz %s ga javob muvaffaqiyatli yetkazildi.", lead_id)
    except Exception as e:
        logger.error("Mijozga xabar yuborishda xatolik: %s", e)
        await funnel.notify_admins(
            context.bot,
            lead,
            incoming_text,
            extra_alert=f"⚠️ Mijozga javob yetkazib bo'lmadi (Xato: {e})"
        )


async def handle_business_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    business_message va edited_business_message yangilanishlarini qayta ishlaydi.
    """
    msg = update.business_message or update.edited_business_message
    if not msg:
        return

    conn_id = msg.business_connection_id
    chat_id = msg.chat.id
    sender = msg.from_user

    if not sender or sender.is_bot:
        return

    incoming_text = msg.text or msg.caption or ""

    # Agar xodim (biznes hisob egasi) o'zi yozgan bo'lsa:
    if sender.id != chat_id:
        clean_cmd = incoming_text.strip().lower()

        # Buyruq: botni to'xtatish
        if clean_cmd in ("#bot off", "/bot off", "#stop", "#ai off", "/ai off", "!bot off", "stop bot", "#pauza"):
            lead_state.set_ai_enabled(chat_id, False)
            logger.info("Xodim mijoz (%s) uchun AI javobini to'xtatdi.", chat_id)
            if config.ADMIN_CHAT_ID:
                try:
                    await context.bot.send_message(
                        chat_id=config.ADMIN_CHAT_ID,
                        text=f"⏸ <b>AI to'xtatildi:</b> Mijoz <code>{chat_id}</code> bilan endi bemalol o'zingiz muloqot qilishingiz mumkin.",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
            return

        # Buyruq: botni qayta yoqish
        if clean_cmd in ("#bot on", "/bot on", "#start", "#ai on", "/ai on", "!bot on", "start bot"):
            lead_state.set_ai_enabled(chat_id, True)
            logger.info("Xodim mijoz (%s) uchun AI javobini qayta yoqdi.", chat_id)
            if config.ADMIN_CHAT_ID:
                try:
                    await context.bot.send_message(
                        chat_id=config.ADMIN_CHAT_ID,
                        text=f"▶️ <b>AI qayta yoqildi:</b> Mijoz <code>{chat_id}</code> ning keyingi xabarlariga AI yana avtomatik javob beradi.",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
            return

        # Maxsus buyruq: Xodimning o'zi AI orqali sinov tariqasida javob olmoqchi bo'lsa: #ai <savol>
        for prefix in ("#ai ", "/ai ", "!ai ", "ai: "):
            if incoming_text.lower().startswith(prefix):
                test_query = incoming_text[len(prefix):].strip()
                logger.info("Xodim test tariqasida AI ga so'rov yubordi: '%s'", test_query)
                await process_customer_message(
                    context=context,
                    chat_id=chat_id,
                    sender=sender,
                    incoming_text=test_query,
                    conn_id=conn_id,
                    reply_to_msg=msg,
                )
                return

        # Oddiy xabar: xodim o'zi shaxsan javob yozmoqda
        logger.info(
            "Xodim (%s) mijozga (%s) shaxsan javob yozdi. AI avtomatik kutish rejimiga o'tdi.",
            sender.id, chat_id
        )
        if incoming_text:
            lead_state.record_human_reply(chat_id, incoming_text)
        return

    # Mijoz (Lead) yozganda:
    await process_customer_message(
        context=context,
        chat_id=chat_id,
        sender=sender,
        incoming_text=incoming_text,
        conn_id=conn_id,
        reply_to_msg=msg,
    )


async def handle_direct_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Foydalanuvchi botga to'g'ridan-to'g'ri shaxsiy chatda (@ipesalesai_bot)
    yozgan xabarlarini qayta ishlaydi.
    """
    msg = update.effective_message
    sender = update.effective_user
    chat = update.effective_chat

    if not msg or not sender or not chat or sender.is_bot:
        return

    incoming_text = msg.text or msg.caption or ""
    if not incoming_text.strip():
        return

    await process_customer_message(
        context=context,
        chat_id=chat.id,
        sender=sender,
        incoming_text=incoming_text,
        conn_id=None,
        reply_to_msg=msg,
    )
