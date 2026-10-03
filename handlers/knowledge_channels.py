import logging
from telegram import Update
from telegram.ext import ContextTypes

import config
import knowledge

logger = logging.getLogger(__name__)


async def handle_knowledge_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Admin va Sales bilim kanallariga tushgan yangi yoki
    tahrirlangan postlarni tinglaydi va bilim keshini yangilaydi.
    """
    post = update.channel_post or update.edited_channel_post
    if not post:
        return

    chat_id = post.chat.id
    message_id = post.message_id
    text = post.text or post.caption or ""

    if not text.strip():
        logger.info("Bilim kanalida matnsiz post keldi (Chat=%s, MsgId=%s).", chat_id, message_id)
        return

    if config.ADMIN_KNOWLEDGE_CHANNEL_ID and chat_id == config.ADMIN_KNOWLEDGE_CHANNEL_ID:
        knowledge.append_knowledge("admin", message_id, text)
        logger.info("Admin bilim kanali yangilandi: Post ID %s, Uzunlik: %d", message_id, len(text))

    elif config.SALES_KNOWLEDGE_CHANNEL_ID and chat_id == config.SALES_KNOWLEDGE_CHANNEL_ID:
        knowledge.append_knowledge("sales", message_id, text)
        logger.info("Sales bilim kanali yangilandi: Post ID %s, Uzunlik: %d", message_id, len(text))

    else:
        logger.debug("Boshqa kanaldan post keldi (Chat ID %s), e'tiborsiz qoldirildi.", chat_id)
