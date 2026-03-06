import os
from dataclasses import dataclass


@dataclass
class Settings:
    database_url: str = ""
    app_env: str = "dev"


def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", ""),
        app_env=os.getenv("APP_ENV", "dev"),
    )
