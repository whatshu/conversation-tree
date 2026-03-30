from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CT_", extra="ignore")

    api_token: str = Field(default="change-me-local-token")
    openai_base_url: str = Field(default="https://api.openai.com/v1")
    openai_api_key: str = Field(default="change-me")
    openai_model: str = Field(default="gpt-4.1-mini")
    summary_model: str = Field(default="gpt-4.1-mini")
    database_url: str = Field(default="sqlite:///./conversation-tree.db")
    langgraph_database_url: str = Field(default="sqlite:///./conversation-tree-langgraph.db")
    log_level: str = Field(default="INFO")
    request_timeout_seconds: int = Field(default=60)
    max_prompt_chars: int = Field(default=16_000)
    enable_mock_provider: bool = Field(default=True)
    bind_host: str = Field(default="127.0.0.1")
    bind_port: int = Field(default=8000)
    service_role: str = Field(default="api")
    worker_poll_interval_seconds: float = Field(default=2.0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
