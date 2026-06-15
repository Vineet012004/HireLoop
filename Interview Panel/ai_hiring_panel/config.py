from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    groq_api_key: str = ""
    database_url: str = "sqlite:///./hiring_panel.db"
    secret_key: str = "change-me-in-production"
    groq_model: str = "llama-3.3-70b-versatile"
    max_questions_per_round: int = 5

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
