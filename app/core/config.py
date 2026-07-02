from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "FastAPI Task"
    app_host: str = "127.0.0.1"
    app_port: int = 8000

    debug: bool = False
    log_level: str = "INFO"
    project_root_dir: str = str(Path(__file__).resolve().parent.parent.parent)

    task_list_cache_ttl: int = 30  # 缓存任务列表的 TTL（秒）

    # SMTP 邮件通知（任务失败时发送通知，不配置则跳过）
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_to: str = ""
    smtp_use_ssl: bool = True
    smtp_starttls: bool = False

    workers: int = 1  # 工作进程数

    # 网络共享盘挂载（解决 Session 0 无法访问映射驱动器的问题）
    net_share_remote: str = ""  # \\hostname\data
    net_share_drive: str = ""  # F:
    net_share_user: str = ""  # 域账号
    net_share_password: str = ""  # 密码

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # 是否区分大小写
    )


settings = Settings()
