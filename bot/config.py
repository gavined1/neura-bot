import hashlib

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    BOT_TOKEN: str
    WEBHOOK_URL: str

    # Optional. If set, used as a TOTP-style pepper when deriving the
    # secret_token we register with Telegram + verify on inbound webhooks.
    # If absent, the secret is derived from BOT_TOKEN alone (still works,
    # just less isolated if BOT_TOKEN leaks to logs).
    WEBHOOK_SECRET_PEPPER: str | None = None

    SUPABASE_URL: str
    SUPABASE_KEY: str

    LLM_API_BASE: str
    LLM_API_KEY: str
    LLM_MODEL: str = "deepseek-v4"

    HISTORY_LIMIT: int = 10
    HISTORY_CHAR_BUDGET: int = 6000          # rough cap on history text per request
    HISTORY_CACHE_TTL_SECONDS: int = 30      # in-memory cache TTL to avoid hitting Supabase every turn
    LLM_TIMEOUT_SECONDS: float = 30.0
    LLM_MAX_RETRIES: int = 2

    # Backpressure / fairness
    LLM_MAX_CONCURRENT: int = 20             # global cap on simultaneous LLM calls
    PER_USER_MAX_CONCURRENT: int = 2         # fairness: one user can have this many in flight

    PORT: int = 8080

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def webhook_url(self) -> str:
        return self.WEBHOOK_URL.rstrip("/")

    @property
    def llm_api_base(self) -> str:
        return self.LLM_API_BASE.rstrip("/")

    @property
    def webhook_secret(self) -> str:
        """
        Deterministic webhook secret_token sent to Telegram and required on
        inbound updates. We hash BOT_TOKEN (+ optional pepper) so the secret
        stored at Telegram is opaque, but never exists in plaintext outside
        of .env. >=16 chars as Telegram requires.
        """
        seed = (self.BOT_TOKEN + ":" + (self.WEBHOOK_SECRET_PEPPER or "neura")).encode()
        digest = hashlib.sha256(seed).hexdigest()  # 64 chars
        return digest[:32]


try:
    config = Settings()
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        f"Missing or invalid environment configuration: {exc}\n"
        "Check that BOT_TOKEN, WEBHOOK_URL, SUPABASE_URL, "
        "SUPABASE_KEY, LLM_API_BASE, LLM_API_KEY are all set."
    )
