from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://mosquito:change_me@db:5432/mosquito"
    redis_url: str = "redis://redis:6379/0"
    admin_token: str = "change_me_admin_token"
    allow_admin_token: bool = True

    admin_username: str = "admin"
    admin_password: str | None = None

    session_secret: str = "change_me_session_secret"
    session_max_age_seconds: int = 60 * 60 * 12  # 12 hours
    cookie_secure: bool = False

    model_path: str = "/app/models/saved/best_model.pth"
    upload_dir: str = "/app/data/uploads"
    log_dir: str = "/app/logs"


settings = Settings()
