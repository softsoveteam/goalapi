from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "SOFTSOVE Portal API"
    secret_key: str = "softsove-dev-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    database_url: str = f"sqlite:///{DATA_DIR / 'app.db'}"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    seed_admin_email: str = "admin@softsove.com"
    seed_admin_password: str = "admin123"
    seed_admin_name: str = "SOFTSOVE Owner"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
