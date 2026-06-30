from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    BOT_TOKEN: str
    WEBHOOK_URL: str
    WEBHOOK_SECRET: str = Field(min_length=8, max_length=256)

    SUPABASE_URL: str
    SUPABASE_KEY: str

    LLM_API_BASE: str
    LLM_API_KEY: str
    LLM_MODEL: str = "deepseek-v4"

    HISTORY_LIMIT: int = 10
    HISTORY_CHAR_BUDGET: int = 6000  # rough cap on history text sent per request
    LLM_TIMEOUT_SECONDS: float = 30.0
    LLM_MAX_RETRIES: int = 2

    PORT: int = 8080

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def webhook_url(self) -> str:
        return self.WEBHOOK_URL.rstrip("/")

    @property
    def llm_api_base(self) -> str:
        return self.LLM_API_BASE.rstrip("/")


try:
    config = Settings()
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        f"Missing or invalid environment configuration: {exc}\n"
        "Check that BOT_TOKEN, WEBHOOK_URL, WEBHOOK_SECRET, SUPABASE_URL, "
        "SUPABASE_KEY, LLM_API_BASE, LLM_API_KEY are all set."
    )