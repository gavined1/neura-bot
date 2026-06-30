from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Telegram
    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")

    # Webhook
    webhook_url: str = Field(alias="WEBHOOK_URL")

    # Supabase
    supabase_url: str = Field(alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(alias="SUPABASE_SERVICE_ROLE_KEY")

    # LLM API
    llm_api_url: str = Field(default="https://openrouter.ai/api/v1/chat/completions", alias="LLM_API_URL")
    llm_api_key: str = Field(alias="LLM_API_KEY")
    llm_model: str = Field(default="openai/gpt-4o-mini", alias="LLM_MODEL")

    # Optional bot identity
    bot_name: str = Field(default="Neura", alias="BOT_NAME")
    bot_system_prompt: str = Field(
        default=(
            "You are Neura, a helpful, concise, and friendly AI assistant. "
            "Be concise but helpful. Use markdown formatting when appropriate."
        ),
        alias="BOT_SYSTEM_PROMPT",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()