import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    InlineQueryHandler,
    MessageHandler,
    filters,
)

from bot.config import config
from bot.handlers import handle_inline, handle_message, start_command
from bot.ai import init_http_client, close_http_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("neura.main")

telegram_app = (
    Application.builder()
    .token(config.BOT_TOKEN)
    .concurrent_updates(True)
    .build()
)
telegram_app.add_handler(CommandHandler("start", start_command))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
telegram_app.add_handler(InlineQueryHandler(handle_inline))


async def _register_webhook() -> None:
    """Best-effort webhook registration. Failure is logged, not raised, so
    Railway's healthcheck still flips to green and we can let a later call
    (or manual retry) re-register the URL."""
    url = f"{config.webhook_url}/webhook"
    try:
        await telegram_app.bot.set_webhook(
            url=url,
            secret_token=config.webhook_secret,
            allowed_updates=["message", "inline_query"],
            drop_pending_updates=True,
        )
        logger.info("Webhook registered at %s (secret enabled)", url)
    except Exception:
        logger.exception("set_webhook failed; continuing so health stays green")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_http_client()
    await telegram_app.initialize()
    await _register_webhook()
    await telegram_app.start()
    yield
    await telegram_app.stop()
    await telegram_app.shutdown()
    await close_http_client()
    logger.info("Telegram application shut down")


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root() -> dict:
    return {"status": "alive", "service": "neura"}


@app.get("/health")
async def health() -> dict:
    """
    Cheap, dependency-free health endpoint for Railway / uptime monitors.
    Always returns 200 — if the app process is alive enough to reply,
    we're healthy. Deeper checks belong in a separate /readyz.
    """
    return {"ok": True}


@app.post("/webhook")
async def webhook(request: Request) -> Response:
    # Telegram sends the secret_token we registered in the X-Telegram-Bot-Api-Secret-Token
    # header. Constant-time compare avoids timing attacks on the secret.
    provided = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not provided or not _secrets_equal(provided, config.webhook_secret):
        logger.warning("Rejected webhook call with bad/missing secret token")
        return Response(status_code=status.HTTP_403_FORBIDDEN)

    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        if update is None:
            return Response(status_code=status.HTTP_400_BAD_REQUEST)
        await telegram_app.update_queue.put(update)
    except Exception:
        logger.exception("Failed to process update")
        # 200 anyway — Telegram will retry on 5xx, we don't want duplicate
        # processing for a soft failure. Logs are the source of truth.
    return Response(status_code=status.HTTP_200_OK, content='{"ok":true}')


def _secrets_equal(a: str, b: str) -> bool:
    import hmac
    return hmac.compare_digest(a.encode(), b.encode())
