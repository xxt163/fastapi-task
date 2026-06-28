from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "FastAPI Task"
    debug: bool = True
    project_root_dir: str = str(Path(__file__).resolve().parent.parent.parent)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # 是否区分大小写
    )


settings = Settings()

print(f"Project root directory: {settings.project_root_dir}")
