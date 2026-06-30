import os


class Config:
    BOT_TOKEN: str = os.environ["BOT_TOKEN"]
    WEBHOOK_URL: str = os.environ["WEBHOOK_URL"].rstrip("/")
    PORT: int = int(os.environ.get("PORT", 8080))

    SUPABASE_URL: str = os.environ["SUPABASE_URL"]
    SUPABASE_KEY: str = os.environ["SUPABASE_KEY"]

    LLM_API_BASE: str = os.environ["LLM_API_BASE"].rstrip("/")
    LLM_API_KEY: str = os.environ["LLM_API_KEY"]
    LLM_MODEL: str = os.environ.get("LLM_MODEL", "deepseek-v4")

    HISTORY_LIMIT: int = int(os.environ.get("HISTORY_LIMIT", 10))


config = Config()
