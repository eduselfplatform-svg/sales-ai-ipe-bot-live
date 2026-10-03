import logging
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

import config
import funnel
import lead_state

logger = logging.getLogger(__name__)


async def handle_stage_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Varonka kanalidagi bosqich tugmalari bosilganda ishlaydi:
    - ADMIN_IDS tekshiruvi
    - Bosqichni yangilash
    - Bosgan adminni mas'ul qilib belgilash
    - Varonka postini tahrirlash
    """
    query = update.callback_query
    if not query or not query.data:
        return

    data = query.data
    if not data.startswith("stage:"):
        return

    user = query.from_user
    user_id = user.id

    # 1. Huquqni tekshirish
    if config.ADMIN_IDS and user_id not in config.ADMIN_IDS:
        logger.warning("Ruxsatsiz foydalanuvchi (%s - %s) varonka tugmasini bosdi.", user_id, user.full_name)
        await query.answer("Sizda ushbu amalni bajarish uchun ruxsat yo'q!", show_alert=True)
        return

    # 2. Parametrlarni ajratib olish
    parts = data.split(":")
    if len(parts) != 3:
        await query.answer("Noto'g'ri so'rov!", show_alert=True)
        return

    _, lead_id_str, new_stage = parts

    lead = lead_state.get_lead(lead_id_str)
    if not lead:
        await query.answer("Lead ma'lumotlari topilmadi!", show_alert=True)
        return

    # 3. Lead holatini yangilash (bosgan odam mas'ul bo'ladi)
    lead = lead_state.update_lead(
        lead_id=lead_id_str,
        stage=new_stage,
        assigned_admin_id=user.id,
        assigned_admin_name=user.full_name,
    )

    stage_label = funnel.STAGE_LABELS.get(new_stage, new_stage)
    logger.info(
        "Lead %s bosqichi '%s' ga o'zgartirildi. Yangi mas'ul: %s (%s)",
        lead_id_str, new_stage, user.full_name, user.id
    )

    # 4. Xabarni tahrirlash
    try:
        await query.edit_message_text(
            text=funnel.build_funnel_text(lead),
            parse_mode="HTML",
            reply_markup=funnel.build_funnel_keyboard(lead_id_str),
        )
        await query.answer(f"Bosqich o'zgartirildi: {stage_label}")
    except TelegramError as e:
        if "message is not modified" in str(e).lower():
            await query.answer(f"Hozirda ham shu bosqichda: {stage_label}")
        else:
            logger.error("Varonka postini tahrirlashda xatolik: %s", e)
            await query.answer("Xabarni yangilashda xatolik yuz berdi.")


async def handle_toggle_ai_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    toggle_ai:{lead_id} tugmasi bosilganda:
    AI ni yoqadi yoki o'chiradi (erkin insoniy muloqot uchun).
    """
    query = update.callback_query
    if not query or not query.data:
        return

    data = query.data
    if not data.startswith("toggle_ai:"):
        return

    user = query.from_user
    if config.ADMIN_IDS and user.id not in config.ADMIN_IDS:
        await query.answer("Sizda ushbu amalni bajarish uchun ruxsat yo'q!", show_alert=True)
        return

    parts = data.split(":", 1)
    if len(parts) != 2:
        await query.answer("Noto'g'ri so'rov!", show_alert=True)
        return

    lead_id_str = parts[1]
    is_active, _ = lead_state.is_ai_active_for_lead(lead_id_str)
    new_status = not is_active
    lead = lead_state.set_ai_enabled(lead_id_str, new_status)

    alert_text = (
        "▶️ AI avtomatik javob berishi YOQILDI!"
        if new_status
        else "⏸ AI TO'XTATILDI! Endi mijoz bilan bemalol o'zingiz muloqot qilishingiz mumkin (AI aralashmaydi)."
    )
    await query.answer(alert_text, show_alert=True)

    # Postni yoki xabarni yangilash
    try:
        if query.message and query.message.chat.id == config.FUNNEL_CHANNEL_ID:
            await query.edit_message_text(
                text=funnel.build_funnel_text(lead),
                parse_mode="HTML",
                reply_markup=funnel.build_funnel_keyboard(lead_id_str),
            )
        else:
            await query.edit_message_reply_markup(
                reply_markup=funnel.build_funnel_keyboard(lead_id_str)
            )
    except Exception as e:
        logger.debug("Tugma yangilashda: %s", e)
