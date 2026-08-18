from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR = DATA_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "SOFTSOVE Portal API"
    secret_key: str = "softsove-dev-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    database_url: str = f"sqlite:///{DATA_DIR / 'app.db'}"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://task.softsove.com,https://task.softsove.com,https://goal.softsove.life,https://goal-v1.softsove.life"
    app_public_url: str = "http://task.softsove.com"
    app_timezone: str = "Asia/Kolkata"
    job_secret: str = ""
    upload_dir: str = str(UPLOADS_DIR)
    max_upload_bytes: int = 15 * 1024 * 1024

    seed_admin_email: str = "admin@softsove.com"
    seed_admin_password: str = "admin123"
    seed_admin_name: str = "SOFTSOVE Owner"
    seed_manager_email: str = "manager@softsove.com"
    seed_manager_password: str = "manager123"
    seed_manager_name: str = "SOFTSOVE Manager"

    admin_whatsapp: str = ""
    interakt_api_key: str = ""
    interakt_template_task: str = "teamtask"
    interakt_template_done: str = "task_completed"
    interakt_template_reminder: str = "task_reminder"
    interakt_template_warning: str = "task_warning"
    interakt_template_digest: str = "daily_digest"
    interakt_language: str = "en"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    @property
    def cors_origin_list(self):
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
