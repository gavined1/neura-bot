import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application

from bot.config import settings
from bot.handlers import handlers

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Build the PTB Application
application = (
    Application.builder()
    .token(settings.telegram_bot_token)
    .build()
)

# Register handlers
for handler in handlers:
    application.add_handler(handler)

# Store bot name for handlers
application.bot_data["bot_name"] = settings.bot_name


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    # Startup
    logger.info("Starting bot...")
    await application.initialize()
    await application.bot.set_webhook(
        url=f"{settings.webhook_url}/webhook",
        drop_pending_updates=True,
    )
    logger.info("Webhook set to %s/webhook", settings.webhook_url)

    yield

    # Shutdown
    logger.info("Shutting down bot...")
    await application.shutdown()


app = FastAPI(lifespan=lifespan)


@app.get("/")
@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "alive"}


@app.post("/webhook")
async def webhook(request: Request) -> Response:
    """Telegram webhook endpoint."""
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
    except Exception as e:
        logger.exception("Webhook error: %s", e)
    return Response(status_code=200)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)