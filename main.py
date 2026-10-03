import html
import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import uvicorn

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


def create_application() -> Application:
    """Telegram bot Application ob'ektini quradi va barcha handlerlarni ulaydi."""
    app_builder = Application.builder().token(config.BOT_TOKEN)
    built_app = app_builder.build()

    # 1. Admin shaxsiy chat buyruqlari
    built_app.add_handler(CommandHandler("start", admin_register.handle_start))
    built_app.add_handler(CommandHandler("status", admin_register.handle_status))
    built_app.add_handler(CommandHandler("test_dm", admin_register.handle_test_dm))
    built_app.add_handler(CommandHandler("help", admin_register.handle_help))

    # 2. Telegram Business Connection hodisalari (ulanish o'rnatilishi / bekor qilinishi)
    from telegram.ext import BusinessConnectionHandler
    built_app.add_handler(BusinessConnectionHandler(business.handle_business_connection))

    # 3. Telegram Business xabarlari (Chat Automation orqali kelgan xabarlar)
    business_filter = (
        filters.UpdateType.BUSINESS_MESSAGES | filters.UpdateType.EDITED_BUSINESS_MESSAGE
    )
    built_app.add_handler(MessageHandler(business_filter, business.handle_business_message))

    # 4. Botga to'g'ridan-to'g'ri shaxsiy chatda (@ipesalesai_bot) yozilgan xabarlar
    direct_filter = (
        (filters.TEXT | filters.CAPTION) & ~filters.COMMAND & filters.ChatType.PRIVATE
    )
    built_app.add_handler(MessageHandler(direct_filter, business.handle_direct_message))

    # 5. Bilim kanallari (Admin va Sales kanallari postlari)
    channel_filter = (
        filters.UpdateType.CHANNEL_POSTS | filters.UpdateType.EDITED_CHANNEL_POST
    )
    built_app.add_handler(MessageHandler(channel_filter, knowledge_channels.handle_knowledge_channel_post))

    # 6. Savdo varonkasi (Kanban) bosqich tugmalari va AI boshqaruvi
    built_app.add_handler(
        CallbackQueryHandler(funnel_buttons.handle_stage_callback, pattern=r"^stage:")
    )
    built_app.add_handler(
        CallbackQueryHandler(funnel_buttons.handle_toggle_ai_callback, pattern=r"^toggle_ai:")
    )

    # Xatoliklar boshqaruvchisi
    built_app.add_error_handler(error_handler)
    return built_app


# Global Telegram Application ob'ekti
ptb_app: Application | None = None


@asynccontextmanager
async def lifespan(fastapi_instance: FastAPI):
    """FastAPI Lifespan: Server start bo'lganda botni ishga tushiradi, to'xtaganda resurslarni yopadi."""
    global ptb_app
    logger.info("=== IPE School Reception + Sales AI Boti ishga tushmoqda ===")

    # Konfiguratsiyani tekshirish
    config.validate_config()
    if not config.BOT_TOKEN:
        logger.critical("BOT_TOKEN aniqlanmadi! Bot ishga tushirilmaydi.")
        yield
        return

    # Holat va keshni xotiraga yuklash
    lead_state.load_state()
    knowledge.load_knowledge_cache()

    # Application qurish va ishga tushirish
    ptb_app = create_application()
    await ptb_app.initialize()
    await ptb_app.start()

    # Ishga tushirish rejimi: Webhook yoki Polling
    if config.RUN_MODE == "webhook":
        if not config.WEBHOOK_URL:
            logger.warning(
                "RUN_MODE=webhook tanlangan, lekin WEBHOOK_URL bo'sh! Avtomatik ravishda Polling rejimiga o'tilmoqda..."
            )
            try:
                await ptb_app.bot.delete_webhook(drop_pending_updates=False)
            except Exception as e:
                logger.warning("delete_webhook ogohlantirish: %s", e)

            await ptb_app.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=False,
            )
            logger.info("Polling muvaffaqiyatli ishga tushirildi.")
        else:
            webhook_url_full = f"{config.WEBHOOK_URL}/{config.BOT_TOKEN}"
            logger.info(
                "Webhook rejimida ishga tushirilmoqda: Port=%d, URL=%s",
                config.PORT,
                webhook_url_full,
            )
            await ptb_app.bot.set_webhook(
                url=webhook_url_full,
                secret_token=config.WEBHOOK_SECRET or None,
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=False,
            )
            logger.info("Telegram Webhook muvaffaqiyatli o'rnatildi.")
    else:
        logger.info("Polling rejimida ishga tushirilmoqda (allowed_updates=Update.ALL_TYPES)...")
        try:
            await ptb_app.bot.delete_webhook(drop_pending_updates=False)
        except Exception as e:
            logger.warning("delete_webhook ogohlantirish: %s", e)

        await ptb_app.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=False,
        )
        logger.info("Polling muvaffaqiyatli boshlandi. Render uchun Web server faol.")

    yield

    logger.info("Server to'xtatilmoqda...")
    if ptb_app:
        if config.RUN_MODE == "webhook" and config.WEBHOOK_URL:
            try:
                await ptb_app.bot.delete_webhook()
            except Exception as e:
                logger.warning("delete_webhook to'xtatishda xatolik: %s", e)
        else:
            if ptb_app.updater and ptb_app.updater.running:
                await ptb_app.updater.stop()

        if ptb_app.running:
            await ptb_app.stop()
        await ptb_app.shutdown()
        logger.info("Bot to'liq to'xtatildi.")


# FastAPI ilovasi
fastapi_app = FastAPI(
    title="IPE School Sales AI Bot",
    description="Render Web Service uchun FastAPI + Uvicorn server",
    lifespan=lifespan,
)


@fastapi_app.get("/")
@fastapi_app.get("/health")
async def health_check():
    """Render port scanner va uptime monitoring uchun health check endpoint."""
    is_running = ptb_app.running if (ptb_app and hasattr(ptb_app, "running")) else False
    return {
        "status": "ok",
        "service": "IPE School Reception + Sales AI Bot",
        "mode": config.RUN_MODE,
        "bot_running": is_running,
    }


@fastapi_app.get("/{token}")
async def token_get_check(token: str):
    """Browser yoki GET so'rovlari uchun webhook holatini tekshirish."""
    if token == config.BOT_TOKEN:
        return {"status": "ok", "message": "Bot webhook endpoint is ready"}
    raise HTTPException(status_code=404, detail="Not found")


@fastapi_app.post("/webhook")
async def telegram_webhook_alt(request: Request):
    """Muqobil /webhook endpointi."""
    if not ptb_app:
        raise HTTPException(status_code=503, detail="Bot hali to'liq ishga tushmagan")

    if config.WEBHOOK_SECRET:
        secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret_header != config.WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Noto'g'ri secret token")

    try:
        data = await request.json()
        update = Update.de_json(data=data, bot=ptb_app.bot)
        await ptb_app.update_queue.put(update)
    except Exception as e:
        logger.error("Webhook update qabul qilishda xatolik: %s", e)
        return Response(status_code=400)

    return Response(status_code=200)


@fastapi_app.post("/{token}")
async def telegram_webhook(token: str, request: Request):
    """Telegram Webhook update'larini qabul qilish va PTB navbatiga uzatish."""
    if not ptb_app:
        raise HTTPException(status_code=503, detail="Bot hali to'liq ishga tushmagan")
    if token != config.BOT_TOKEN:
        raise HTTPException(status_code=403, detail="Ruxsat berilmagan token")

    if config.WEBHOOK_SECRET:
        secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret_header != config.WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Noto'g'ri secret token")

    try:
        data = await request.json()
        update = Update.de_json(data=data, bot=ptb_app.bot)
        await ptb_app.update_queue.put(update)
    except Exception as e:
        logger.error("Webhook update qabul qilishda xatolik: %s", e)
        return Response(status_code=400)

    return Response(status_code=200)



# ASGI serverlar (masalan: uvicorn main:app) uchun alias
app = fastapi_app


def main() -> None:
    """Uvicorn web serverini ishga tushirish."""
    logger.info("=== IPE School Reception + Sales AI Boti ishga tushmoqda ===")

    # Konfiguratsiyani tekshirish
    config.validate_config()
    if not config.BOT_TOKEN:
        logger.critical("BOT_TOKEN aniqlanmadi! Dastur to'xtatiladi.")
        sys.exit(1)

    port = int(os.getenv("PORT", config.PORT or 8080))
    logger.info("Uvicorn server ishga tushirilmoqda. Host: 0.0.0.0, Port: %d", port)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
