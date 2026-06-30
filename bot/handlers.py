import logging
import uuid

from telegram import (
    Update,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from telegram.ext import (
    ContextTypes,
    filters,
    CommandHandler,
    MessageHandler,
    InlineQueryHandler,
)

from .ai import get_reply

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    if update.message:
        await update.message.reply_text(
            f"Hi! I'm {context.bot_data.get('bot_name', 'Neura')}. "
            "Send me a message and I'll reply."
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular text messages."""
    if not update.message or not update.message.text:
        return

    user_id = update.message.from_user.id
    group_id = update.message.chat_id
    text = update.message.text

    try:
        reply = await get_reply(user_id, group_id, text)
        await update.message.reply_text(reply)
    except Exception as e:
        logger.exception("Message handler error for user=%s group=%s", user_id, group_id)
        if update.message:
            await update.message.reply_text("Something went wrong. Please try again.")


async def handle_inline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline queries."""
    if not update.inline_query:
        return

    user_id = update.inline_query.from_user.id
    query = update.inline_query.query.strip()

    # Empty query returns nothing
    if not query:
        await update.inline_query.answer([], cache_time=0, is_personal=True)
        return

    # Use group_id=0 as sentinel for inline queries (isolated from chat history)
    try:
        reply = await get_reply(user_id, 0, query)

        result = InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title="Neura",
            input_message_content=InputTextMessageContent(reply),
        )
        await update.inline_query.answer([result], cache_time=0, is_personal=True)
    except Exception as e:
        logger.exception("Inline handler error for user=%s", user_id)
        # Return empty results on error
        await update.inline_query.answer([], cache_time=0, is_personal=True)


# Handler list for easy registration in main.py
handlers = [
    CommandHandler("start", start),
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
    InlineQueryHandler(handle_inline),
]