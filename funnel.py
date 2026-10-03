import html
import logging
from typing import Any
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

import config
import lead_state

logger = logging.getLogger(__name__)

STAGE_LABELS = {
    "new": "🆕 Yangi",
    "in_conversation": "💬 Muloqotda",
    "course_recommended": "🎯 Kurs tavsiya qilindi",
    "demo_invited": "📅 Demo taklif qilindi",
    "demo_confirmed": "✅ Demo tasdiqlandi",
    "won": "🏆 Sotib oldi",
    "lost": "❌ Qiziqmadi",
}


def build_funnel_keyboard(lead_id: int | str) -> InlineKeyboardMarkup:
    """Varonka posti uchun 2 tadan qilib inline tugmalar klaviaturasini tuzadi."""
    rows: list[list[InlineKeyboardButton]] = []
    current_row: list[InlineKeyboardButton] = []

    for stage_key, label in STAGE_LABELS.items():
        button = InlineKeyboardButton(
            text=label,
            callback_data=f"stage:{lead_id}:{stage_key}",
        )
        current_row.append(button)
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []

    if current_row:
        rows.append(current_row)

    # AI ni yoqish / to'xtatish boshqaruv tugmasi
    is_active, _ = lead_state.is_ai_active_for_lead(lead_id)
    toggle_text = "⏸ AI ni to'xtatish (Erkin muloqot)" if is_active else "▶️ AI ni yoqish (Avto-javob)"
    rows.append([InlineKeyboardButton(text=toggle_text, callback_data=f"toggle_ai:{lead_id}")])

    return InlineKeyboardMarkup(rows)


def build_funnel_text(lead: dict[str, Any]) -> str:
    """Lead ma'lumotlari asosida chiroyli HTML formatidagi varonka posti matnini tuzadi."""
    admin_name = lead.get("assigned_admin_name") or "— hali tayinlanmagan —"
    stage_key = lead.get("stage", "new")
    stage_label = STAGE_LABELS.get(stage_key, stage_key)

    username = lead.get("username")
    username_display = f"@{username}" if username else "—"

    name_display = html.escape(str(lead.get("name") or "Noma'lum"))
    interest_display = html.escape(str(lead.get("interest_note") or "—"))
    note_display = html.escape(str(lead.get("note") or "—"))
    admin_display = html.escape(str(admin_name))

    lead_id = lead.get("id")
    is_active, reason = lead_state.is_ai_active_for_lead(lead_id) if lead_id else (True, "Faol")
    ai_status = "🟢 Faol (avto-javob)" if is_active else f"🔴 To'xtatilgan ({reason})"

    updated_at = str(lead.get("updated_at") or "")
    if "T" in updated_at:
        updated_at = updated_at[:19].replace("T", " ")

    return (
        f"👤 <b>{name_display}</b> ({username_display})\n"
        f"📌 Bosqich: <b>{stage_label}</b>\n"
        f"🤖 AI holati: <b>{ai_status}</b>\n"
        f"🙋 Mas'ul: <b>{admin_display}</b>\n"
        f"💡 Qiziqishi: {interest_display}\n"
        f"📝 Izoh: {note_display}\n"
        f"🕒 Yangilandi: <code>{updated_at}</code>"
    )


async def sync_funnel_post(bot: Bot, lead_id: int | str, lead: dict[str, Any]) -> int | None:
    """
    Funnel kanalidagi postni sinxronlaydi:
    - Agar post mavjud bo'lsa, uni tahrirlaydi (edit_message_text).
    - Agar post hali yo'q bo'lsa, yangi post yaratadi (send_message) va ID ni saqlaydi.
    """
    if not config.FUNNEL_CHANNEL_ID:
        logger.warning("FUNNEL_CHANNEL_ID sozlanmagan, varonka posti yangilanmadi.")
        return None

    text = build_funnel_text(lead)
    keyboard = build_funnel_keyboard(lead_id)
    message_id = lead.get("funnel_message_id")

    if message_id:
        try:
            await bot.edit_message_text(
                chat_id=config.FUNNEL_CHANNEL_ID,
                message_id=message_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            logger.info("Varonka posti tahrirlandi: Lead=%s, MsgId=%s", lead_id, message_id)
            return message_id
        except TelegramError as e:
            err_msg = str(e).lower()
            if "message is not modified" in err_msg:
                return message_id
            logger.warning(
                "Varonka postini tahrirlashda xatolik (%s). Yangi post yaratishga uriniladi...", e
            )

    # Yangi post yaratish
    try:
        sent = await bot.send_message(
            chat_id=config.FUNNEL_CHANNEL_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        new_msg_id = sent.message_id
        lead_state.update_lead(lead_id, funnel_message_id=new_msg_id)
        logger.info("Yangi varonka posti yaratildi: Lead=%s, MsgId=%s", lead_id, new_msg_id)
        return new_msg_id
    except Exception as e:
        logger.error("Varonka postini yuborishda xatolik: %s", e)
        return None


async def notify_admins(
    bot: Bot,
    lead: dict[str, Any],
    incoming_text: str,
    extra_alert: str = "",
) -> None:
    """
    Admin guruhiga live bildirishnoma yuboradi va
    agar mas'ul admin bo'lsa, unga shaxsiy DM xabar yuboradi.
    """
    if not config.ADMIN_CHAT_ID:
        logger.warning("ADMIN_CHAT_ID sozlanmagan, bildirishnoma yuborilmadi.")
        return

    admin_name = lead.get("assigned_admin_name") or "— hali tayinlanmagan —"
    lead_name = html.escape(str(lead.get("name") or "Mijoz"))
    username = lead.get("username")
    user_tag = f" (@{username})" if username else ""
    safe_text = html.escape(incoming_text)

    group_msg = (
        f"🔔 <b>{lead_name}</b>{user_tag}:\n"
        f"<i>\"{safe_text}\"</i>\n"
        f"🙋 Mas'ul: <b>{html.escape(admin_name)}</b>"
    )
    if extra_alert:
        group_msg += f"\n\n⚠️ <b>Diqqat:</b> {extra_alert}"

    lead_id = lead.get("id")
    reply_markup = None
    if lead_id:
        is_active, _ = lead_state.is_ai_active_for_lead(lead_id)
        btn_text = "⏸ AI ni to'xtatish" if is_active else "▶️ AI ni yoqish"
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(btn_text, callback_data=f"toggle_ai:{lead_id}")]
        ])

    # 1) Umumiy admin guruhiga yuborish
    try:
        await bot.send_message(
            chat_id=config.ADMIN_CHAT_ID,
            text=group_msg,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.error("Admin guruhiga bildirishnoma yuborishda xatolik: %s", e)

    # 2) Agar avval mas'ul tayinlangan bo'lsa — unga SHAXSIY DM ham yuboriladi
    assigned_id = lead.get("assigned_admin_id")
    if assigned_id:
        try:
            dm_msg = (
                f"📩 <b>Sizning mijozingiz {lead_name} yozdi:</b>\n\n"
                f"\"{safe_text}\""
            )
            if extra_alert:
                dm_msg += f"\n\n⚠️ {extra_alert}"

            await bot.send_message(
                chat_id=assigned_id,
                text=dm_msg,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
            logger.info("Mas'ul admin (%s) ga DM muvaffaqiyatli yuborildi.", assigned_id)
        except Exception:
            logger.warning(
                "Admin %s botga /start bosmagan yoki bloklagan, shaxsiy DM yuborib bo'lmadi.",
                assigned_id,
            )
