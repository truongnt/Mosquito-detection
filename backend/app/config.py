from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())

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

    @field_validator("cookie_secure", "allow_admin_token", mode="before")
    @classmethod
    def _parse_boolish(cls, v):
        if isinstance(v, bool):
            return v
        if v is None:
            return v
        if isinstance(v, str):
            s = v.strip().lower()
            s = s.split("#", 1)[0].strip()
            s = s.split("(", 1)[0].strip()
            s = s.split(None, 1)[0].strip() if s else s
            if s in {"1", "true", "yes", "y", "on"}:
                return True
            if s in {"0", "false", "no", "n", "off"}:
                return False
        raise ValueError("Invalid boolean")


settings = Settings()
