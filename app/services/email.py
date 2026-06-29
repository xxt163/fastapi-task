"""邮件发送服务"""

import asyncio
import html
import os
import smtplib
import socket
from datetime import datetime, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings
from app.core.logger import get_service_logger


def _get_logger():
    return get_service_logger()


def send_email(
    subject: str,
    body: str,
    *,
    to: str | None = None,
    cc: str | None = None,
    from_addr: str | None = None,
    is_html: bool = False,
    attachments: list[str] | None = None,
    host: str | None = None,
    port: int | None = None,
    user: str | None = None,
    password: str | None = None,
) -> None:
    """
    发送邮件，发送失败时抛出异常
    """
    _host = host or settings.smtp_host
    _port = port if port is not None else settings.smtp_port
    _user = user or settings.smtp_user
    _password = password or settings.smtp_password
    _from = from_addr or settings.smtp_from or _user
    _to = to or settings.smtp_to

    if not all([_host, _user, _to]):
        raise ValueError("SMTP 未配置，请在 .env 中设置 SMTP_HOST/SMTP_USER/SMTP_TO")

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = _from
    msg["To"] = _to
    if cc:
        msg["Cc"] = cc

    msg.attach(MIMEText(body, "html" if is_html else "plain", "utf-8"))

    if attachments:
        for file_path in attachments:
            with open(file_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
            part["Content-Disposition"] = (
                f'attachment; filename="{os.path.basename(file_path)}"'
            )
            msg.attach(part)

    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(_host, _port, timeout=15) as server:
                server.login(_user, _password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(_host, _port, timeout=15) as server:
                server.login(_user, _password)
                server.send_message(msg)
    except (
        smtplib.SMTPConnectError,
        smtplib.SMTPAuthenticationError,
        smtplib.SMTPException,
    ) as e:
        raise RuntimeError(f"SMTP 错误: {e}")
    except socket.timeout:
        raise TimeoutError("SMTP 连接超时")
    except (socket.gaierror, ConnectionRefusedError) as e:
        raise ConnectionError(f"SMTP 网络错误: {e}")


async def send_task_failure_email(
    task_id: str,
    flow: str,
    task: str,
    error: str,
    duration_ms: int,
) -> None:
    """发送任务失败通知邮件，失败时仅记录日志"""
    if not all([settings.smtp_host, settings.smtp_user, settings.smtp_to]):
        _get_logger().warning(
            "SMTP not configured, skipping email notification",
            extra={"task_id": task_id},
        )
        return

    body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: 'Microsoft YaHei', Arial, sans-serif; color: #333;">
  <h2 style="color: #d32f2f;">任务执行失败</h2>
  <table style="border-collapse: collapse; width: 100%; max-width: 500px;">
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5; width: 100px;">Task ID</td><td style="padding: 8px; border: 1px solid #ddd;">{html.escape(task_id)}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">Flow</td><td style="padding: 8px; border: 1px solid #ddd;">{html.escape(flow)}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">Task</td><td style="padding: 8px; border: 1px solid #ddd;">{html.escape(task)}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">耗时</td><td style="padding: 8px; border: 1px solid #ddd;">{duration_ms} ms</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">时间</td><td style="padding: 8px; border: 1px solid #ddd;">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">错误信息</td><td style="padding: 8px; border: 1px solid #ddd; color: #d32f2f;">{html.escape(error)}</td></tr>
  </table>
  <p style="color: #999; font-size: 12px; margin-top: 20px;">此邮件由 FastAPI Task 系统自动发送</p>
</body>
</html>"""

    try:
        await asyncio.to_thread(
            send_email, subject=f"[任务失败] {flow}/{task}", body=body, is_html=True
        )
        _get_logger().info(
            "Email notification sent",
            extra={"task_id": task_id, "to": settings.smtp_to},
        )
    except Exception as e:
        _get_logger().error(
            "Failed to send email", extra={"task_id": task_id, "error": str(e)}
        )
