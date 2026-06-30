import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, MessageHandler, InlineQueryHandler, CommandHandler, filters

from bot.config import config
from bot.handlers import handle_message, handle_inline, start_command

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("neura.main")

telegram_app = Application.builder().token(config.BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start_command))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
telegram_app.add_handler(InlineQueryHandler(handle_inline))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await telegram_app.initialize()
    webhook_url = f"{config.WEBHOOK_URL}/webhook"
    await telegram_app.bot.set_webhook(url=webhook_url)
    logger.info("Webhook registered at %s", webhook_url)
    await telegram_app.start()

    yield

    await telegram_app.stop()
    await telegram_app.shutdown()
    logger.info("Telegram application shut down")


app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
    except Exception:
        logger.exception("Failed to process update")
    return {"ok": True}


@app.get("/")
async def health():
    return {"status": "alive"}
