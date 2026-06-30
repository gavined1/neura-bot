import logging
import uuid

from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ContextTypes

from bot.ai import generate_ai_reply, generate_inline_reply

logger = logging.getLogger("neura.handlers")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hey, I'm Neura. Mention me or just message me here and I'll help out."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if not update.message or not update.message.text:
            return

        user_id = update.message.from_user.id
        group_id = update.message.chat_id
        text = update.message.text

        reply = await generate_ai_reply(user_id, group_id, text)
        await update.message.reply_text(reply)
    except Exception:
        logger.exception("handle_message failed")
        try:
            await update.message.reply_text(
                "Something went wrong on my end. Try again in a bit."
            )
        except Exception:
            pass


async def handle_inline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.inline_query.query.strip()
        if not query:
            return

        user_id = update.inline_query.from_user.id
        reply = await generate_inline_reply(user_id, query)

        result = InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title=query[:60],
            description=reply[:100],
            input_message_content=InputTextMessageContent(reply),
        )
        await update.inline_query.answer([result], cache_time=0, is_personal=True)
    except Exception:
        logger.exception("handle_inline failed")
