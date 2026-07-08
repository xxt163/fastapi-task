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

    # SMB / 网络共享盘配置
    # Windows 服务运行在 Session 0，看不到用户桌面会话的盘符映射。
    # 配置后，服务启动时会自动在 Session 0 内挂载指定盘符。
    smb_drive_letter: str = ""  # 盘符，如 "F:"（冒号必填）
    smb_share_path: str = ""  # UNC 路径，如 "\\\\192.168.1.100\\data"
    smb_username: str = ""  # SMB 认证用户名
    smb_password: str = ""  # SMB 认证密码

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # 是否区分大小写
    )


settings = Settings()
