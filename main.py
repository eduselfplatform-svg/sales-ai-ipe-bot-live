import html
import logging
import sys
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
import knowledge
import lead_state
from handlers import admin_register, business, funnel_buttons, knowledge_channels

# Logging sozlamalari
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
)
logger = logging.getLogger("sales_bot")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Kutilmagan xatoliklarni qayd qiladi va admin guruhiga yetkazadi."""
    logger.error("Kutilmagan xatolik yuz berdi:", exc_info=context.error)

    if not config.ADMIN_CHAT_ID:
        return

    err_str = html.escape(str(context.error))
    update_str = html.escape(str(update))[:300] if update else "Yo'q"

    alert = (
        f"🚨 <b>BOTDA KUTILMAGAN XATOLIK!</b>\n\n"
        f"❌ <b>Xatolik:</b> <code>{err_str}</code>\n\n"
        f"📦 <b>Update:</b> <code>{update_str}</code>"
    )

    try:
        await context.bot.send_message(
            chat_id=config.ADMIN_CHAT_ID,
            text=alert,
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Admin chatga xatolik xabarini yuborishda xato: %s", e)


def main() -> None:
    """Botni ishga tushirish funksiyasi."""
    logger.info("=== IPE School Reception + Sales AI Boti ishga tushmoqda ===")

    # Konfiguratsiyani tekshirish
    issues = config.validate_config()
    if not config.BOT_TOKEN:
        logger.critical("BOT_TOKEN aniqlanmadi! Dastur to'xtatiladi.")
        sys.exit(1)

    # Holat va keshni xotiraga yuklash
    lead_state.load_state()
    knowledge.load_knowledge_cache()

    # Application qurish
    app = Application.builder().token(config.BOT_TOKEN).build()

    # 1. Admin shaxsiy chat buyruqlari
    app.add_handler(CommandHandler("start", admin_register.handle_start))
    app.add_handler(CommandHandler("status", admin_register.handle_status))
    app.add_handler(CommandHandler("test_dm", admin_register.handle_test_dm))
    app.add_handler(CommandHandler("help", admin_register.handle_help))

    # 2. Telegram Business Connection hodisalari (ulanish o'rnatilishi / bekor qilinishi)
    from telegram.ext import BusinessConnectionHandler
    app.add_handler(BusinessConnectionHandler(business.handle_business_connection))

    # 3. Telegram Business xabarlari (Chat Automation orqali kelgan xabarlar)
    business_filter = (
        filters.UpdateType.BUSINESS_MESSAGES | filters.UpdateType.EDITED_BUSINESS_MESSAGE
    )
    app.add_handler(MessageHandler(business_filter, business.handle_business_message))

    # 4. Botga to'g'ridan-to'g'ri shaxsiy chatda (@ipesalesai_bot) yozilgan xabarlar
    direct_filter = (
        (filters.TEXT | filters.CAPTION) & ~filters.COMMAND & filters.ChatType.PRIVATE
    )
    app.add_handler(MessageHandler(direct_filter, business.handle_direct_message))

    # 4. Bilim kanallari (Admin va Sales kanallari postlari)
    channel_filter = (
        filters.UpdateType.CHANNEL_POSTS | filters.UpdateType.EDITED_CHANNEL_POST
    )
    app.add_handler(MessageHandler(channel_filter, knowledge_channels.handle_knowledge_channel_post))

    # 5. Savdo varonkasi (Kanban) bosqich tugmalari va AI boshqaruvi
    app.add_handler(
        CallbackQueryHandler(funnel_buttons.handle_stage_callback, pattern=r"^stage:")
    )
    app.add_handler(
        CallbackQueryHandler(funnel_buttons.handle_toggle_ai_callback, pattern=r"^toggle_ai:")
    )

    # Xatoliklar boshqaruvchisi
    app.add_error_handler(error_handler)

    # Ishga tushirish rejimi: Webhook yoki Polling
    if config.RUN_MODE == "webhook":
        if not config.WEBHOOK_URL:
            logger.critical("RUN_MODE=webhook tanlangan, lekin WEBHOOK_URL bo'sh!")
            sys.exit(1)

        webhook_url_full = f"{config.WEBHOOK_URL}/{config.BOT_TOKEN}"
        logger.info(
            "Webhook rejimida ishga tushirilmoqda: Port=%d, URL=%s",
            config.PORT,
            webhook_url_full,
        )

        app.run_webhook(
            listen="0.0.0.0",
            port=config.PORT,
            url_path=config.BOT_TOKEN,
            webhook_url=webhook_url_full,
            secret_token=config.WEBHOOK_SECRET or None,
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=False,
        )
    else:
        logger.info("Polling rejimida ishga tushirilmoqda (allowed_updates=Update.ALL_TYPES)...")
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=False,
        )


if __name__ == "__main__":
    main()
