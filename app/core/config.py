from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "FastAPI Task"
    debug: bool = True
    log_level: str = "INFO"
    project_root_dir: str = str(Path(__file__).resolve().parent.parent.parent)

    # SMTP 邮件通知（任务失败时发送通知，不配置则跳过）
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_to: str = ""
    smtp_use_ssl: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # 是否区分大小写
    )


settings = Settings()
