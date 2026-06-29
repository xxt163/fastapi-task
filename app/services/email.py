"""邮件发送服务"""

import asyncio
import os
import smtplib
from datetime import datetime, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings
from app.core.logger import get_service_logger

logger = get_service_logger()


def send_email(
    subject: str,
    body: str,
    *,
    to: str | None = None,
    cc: str | None = None,
    from_addr: str | None = None,
    html: bool = False,
    attachments: list[str] | None = None,
    host: str | None = None,
    port: int | None = None,
    user: str | None = None,
    password: str | None = None,
    use_ssl: bool | None = None,
) -> None:
    """
    发送邮件

    参数:
        subject:     邮件主题
        body:        邮件正文（纯文本或 HTML）
        to:          收件人，逗号分隔多个；默认使用 .env SMTP_TO
        cc:          抄送，逗号分隔多个；可选
        from_addr:   发件人；默认使用 .env SMTP_FROM
        html:        正文是否为 HTML，默认 False（纯文本）
        attachments: 附件文件路径列表
        host:        SMTP 服务器；默认使用 .env SMTP_HOST
        port:        SMTP 端口；默认使用 .env SMTP_PORT
        user:        SMTP 用户名；默认使用 .env SMTP_USER
        password:    SMTP 密码；默认使用 .env SMTP_PASSWORD
        use_ssl:     是否使用 SSL；默认使用 .env SMTP_USE_SSL

    异常:
        如果 SMTP 未配置，抛出 ValueError
        发送失败抛出 SMTPException 等异常
    """
    _host = host or settings.smtp_host
    _port = port if port is not None else settings.smtp_port
    _user = user or settings.smtp_user
    _password = password or settings.smtp_password
    _from = from_addr or settings.smtp_from or settings.smtp_user
    _to = to or settings.smtp_to
    _use_ssl = use_ssl if use_ssl is not None else settings.smtp_use_ssl

    if not all([_host, _user, _to]):
        raise ValueError("SMTP 未配置，请在 .env 中设置 SMTP_HOST/SMTP_USER/SMTP_TO")

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = _from
    msg["To"] = _to
    if cc:
        msg["Cc"] = cc

    subtype = "html" if html else "plain"
    msg.attach(MIMEText(body, subtype, "utf-8"))

    if attachments:
        for file_path in attachments:
            with open(file_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
            part["Content-Disposition"] = (
                f'attachment; filename="{os.path.basename(file_path)}"'
            )
            msg.attach(part)

    if _use_ssl:
        with smtplib.SMTP_SSL(_host, _port, timeout=15) as server:
            server.login(_user, _password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(_host, _port, timeout=15) as server:
            server.login(_user, _password)
            server.send_message(msg)


async def send_task_failure_email(
    task_id: str,
    flow: str,
    task: str,
    error: str,
    duration_ms: int,
) -> None:
    """异步发送任务失败通知邮件"""
    to = settings.smtp_to
    host = settings.smtp_host
    user = settings.smtp_user

    if not all([host, user, to]):
        return

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    subject = f"[任务失败] {flow}/{task}"

    body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: 'Microsoft YaHei', Arial, sans-serif; color: #333;">
  <h2 style="color: #d32f2f;">任务执行失败</h2>
  <table style="border-collapse: collapse; width: 100%; max-width: 500px;">
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5; width: 100px;">Task ID</td><td style="padding: 8px; border: 1px solid #ddd;">{task_id}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">Flow</td><td style="padding: 8px; border: 1px solid #ddd;">{flow}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">Task</td><td style="padding: 8px; border: 1px solid #ddd;">{task}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">耗时</td><td style="padding: 8px; border: 1px solid #ddd;">{duration_ms} ms</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">时间</td><td style="padding: 8px; border: 1px solid #ddd;">{now}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">错误信息</td><td style="padding: 8px; border: 1px solid #ddd; color: #d32f2f;">{error}</td></tr>
  </table>
  <p style="color: #999; font-size: 12px; margin-top: 20px;">此邮件由 FastAPI Task 系统自动发送</p>
</body>
</html>"""

    try:
        await asyncio.to_thread(send_email, subject=subject, body=body, html=True)
        logger.info(
            "Email notification sent", extra={"task_id": task_id, "recipients": to}
        )
    except Exception as e:
        logger.error(
            "Failed to send email notification",
            extra={"task_id": task_id, "error": str(e)},
        )
