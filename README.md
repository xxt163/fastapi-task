# fastapi-task

FastAPI 任务执行框架 — 将 Python 脚本放入 `tasks/` 目录即可通过 HTTP API 发现并执行，支持任务失败邮件通知、SMB 网络共享盘自动挂载和 JSON 格式日志。

## 项目结构

```
fastapi-task/
├── app/
│   ├── api/                # API 路由
│   │   ├── health.py       # GET /health
│   │   └── task.py         # GET /task/list, POST /task/run
│   ├── core/
│   │   ├── config.py       # 配置（基于 .env，pydantic-settings）
│   │   ├── exceptions.py   # 自定义异常
│   │   ├── logger.py       # JSON 日志（按天分目录，午夜自动切换文件）
│   │   └── smb_mount.py    # SMB 网络共享盘挂载/卸载工具
│   ├── schemas/
│   │   └── task_schemas.py # 请求/响应 Pydantic 模型
│   ├── services/
│   │   ├── email.py        # SMTP 邮件发送
│   │   └── task_loader.py  # 任务动态加载 + 任务列表 TTL 缓存
│   └── main.py             # FastAPI 应用入口 + lifespan
├── tasks/                  # 任务脚本目录（按 flow 分子目录）
│   └── demo/
│       ├── read_excel.py   # 示例：pandas 读取 Excel
│       └── read_text.py    # 示例：读取文本文件
├── scripts/                # Windows 服务管理脚本
│   ├── create_service.ps1  # 安装为 Windows 服务（NSSM）
│   └── remove_service.ps1  # 卸载 Windows 服务
├── run_dev.py              # 开发启动（127.0.0.1:8000，热重载）
├── run_prod.py             # 生产启动（0.0.0.0:8000）
├── pyproject.toml
├── requirements.txt
├── uv.lock                 # uv 依赖锁定文件
└── .python-version         # Python 3.10
```

## 快速开始

### 1. 安装依赖

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### 2. 配置 .env

```bash
cp .env.example .env
```

编辑 `.env`，按需配置：

```bash
# 基础配置
APP_NAME=FastAPI Task
APP_HOST=127.0.0.1
APP_PORT=8000
DEBUG=false
LOG_LEVEL=INFO
WORKERS=1

# 任务列表缓存 TTL（秒）
TASK_LIST_CACHE_TTL=30

# 任务执行限制
TASK_TIMEOUT_SECONDS=3600     # 单个任务最大执行时间（秒），超时返回错误
TASK_MAX_CONCURRENCY=5        # 最大并发任务数，超限返回 503

# SMTP 邮件通知（任务失败时发送，不配置则跳过）
SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_USER=your@example.com
SMTP_PASSWORD=your_password
SMTP_TO=admin@example.com
SMTP_USE_SSL=true
SMTP_STARTTLS=false

# SMB 网络共享盘（Windows 服务自动挂载，非 Windows 或留空则跳过）
SMB_DRIVE_LETTER=F:
SMB_SHARE_PATH=\\192.168.1.100\data
SMB_USERNAME=userl
SMB_PASSWORD=
```

> `.env` 已 `.gitignore`，请勿提交到仓库。

### 3. 启动服务

```bash
# 开发模式（热重载，127.0.0.1:8000）
python run_dev.py

# 生产模式
python run_prod.py
```

## API 接口

### 健康检查

```http
GET /health
```

```json
{
  "status": "healthy",
  "checks": {
    "tasks_dir": "ok",
    "smb_mount": "ok"
  }
}
```

> 返回 `"status": "degraded"` 表示部分依赖异常（如 SMB 未挂载），客户端可据此做容灾切换。

### 获取任务列表

```http
GET /task/list
```

扫描 `tasks/` 目录，返回所有有效任务。带 30 秒 TTL 缓存：

```json
{
  "tasks": [
    {"flow": "demo", "task": "read_text", "path": "tasks/demo/read_text.py"},
    {"flow": "demo", "task": "read_excel", "path": "tasks/demo/read_excel.py"}
  ]
}
```

> 以 `_` 或 `.` 开头的目录/文件会被忽略。

### 执行任务

```http
POST /task/run
Content-Type: application/json

{
  "flow": "demo",
  "task": "read_text",
  "data": {
    "file_path": "F:/test.txt"
  }
}
```

成功响应：

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "flow": "demo",
  "task": "read_text",
  "status": "success",
  "result": "文件内容...",
  "error": null,
  "duration_ms": 320
}
```

失败响应：

```json
{
  "task_id": "a1b2c3d4-...",
  "flow": "demo",
  "task": "read_text",
  "status": "failed",
  "result": null,
  "error": "Traceback ...",
  "duration_ms": 150
}
```

> **超时与并发**：任务超时和并发数可通过 `.env` 中的 `TASK_TIMEOUT_SECONDS`（默认 3600s）和 `TASK_MAX_CONCURRENCY`（默认 5）配置。超时后 HTTP 立即返回错误但后台线程继续运行；并发满时返回 503。

## 编写任务

在 `tasks/<flow>/` 下创建 `.py` 文件，实现 `run(data)` 函数，用 `print()` 输出日志即可：

```python
# tasks/demo/hello.py

def run(data: dict):
    name = data.get("name", "World")
    print(f"收到请求: name={name}")
    print("处理完成")
    return {"message": f"Hello, {name}!"}


if __name__ == "__main__":
    # 直接运行即可调试，无需任何 import
    print(run({"name": "FastAPI"}))
```

> **只需 `print()`**，无需 import 任何 logging 模块。服务模式自动将 `print()` 输出转为 JSON 日志；IDE 直接点击运行即可在终端看到输出。

## 日志

日志按天分目录，午夜自动切换文件，全部 JSON 格式（北京时间 UTC+8）：

```
logs/
└── 2026-07-08/
    ├── startup.log               # 服务启停日志
    ├── email.log                 # 邮件服务日志
    ├── access.log                # HTTP 请求日志（uvicorn.access）
    ├── uvicorn.log               # uvicorn 运行日志
    └── demo/
        ├── read_text-153001-a1b2c3d4.log  # 每次任务执行独立文件
        └── read_text-153002-e5f6g7h8.log  # 并发请求不串日志
```

每行一条 JSON，`extra` 传入的字段自动输出。示例：

```json
{"time":"2026-07-08T15:30:00+08:00","level":"INFO","logger":"tasks.demo.read_text.a1b2c3d4","msg":"开始读取文件","file_path":"F:/test.txt"}
```

## SMB 网络共享盘

Windows 服务运行在 Session 0，无法看到用户桌面手动映射的盘符。配置 `.env` 中的 `SMB_*` 后，服务启动时自动在 Session 0 内挂载指定盘符，停止时自动断开。

- 不影响用户桌面会话中的同名盘符
- 非 Windows 环境或留空则静默跳过
- 生产模式每次启动强制重挂，开发模式已存在则跳过

## 邮件通知

- 任务执行失败时自动发送 HTML 邮件通知
- 配置 `.env` 中的 SMTP 参数即可启用，未配置时静默跳过
- 支持 SSL（端口 465）和 STARTTLS（端口 587）

## Windows 服务部署

```powershell
# 安装服务（需要管理员权限）
.\scripts\create_service.ps1

# 卸载服务
.\scripts\remove_service.ps1
```

服务配置为自动启动、失败自动重启，可选每日定时重启（默认凌晨 3:00）。

## 注意事项

- 开发模式（`run_dev.py`）强制 `DEBUG=true` 并监听 `app/`、`tasks/` 变更，任务模块每次请求重新加载
- **Windows 上 `WORKERS` 必须为 1**（`run_prod.py` 会自动降级）
- 任务通过 `importlib` 动态加载，首次调用触发 import，后续命中缓存
- 任务在独立线程中执行，不阻塞事件循环；`asyncio.wait_for()` 超时后 HTTP 返回错误但**线程继续运行**
- 并发任务数由 `TASK_MAX_CONCURRENCY` 限制（默认 5），超限返回 503；合理设置可防止线程池耗尽
- 任务脚本只需 `print()`，服务端自动将输出转为 JSON 日志，并发请求日志隔离
- `/health` 端点会检查 `tasks/` 目录和 SMB 挂载状态，返回 `healthy` 或 `degraded`
- 每日定时重启（NSSM）会强制终止正在执行的任务，将重启时间设在业务低谷期

## 依赖

| 包 | 用途 |
|---|---|
| `fastapi[standard]` >= 0.138.1 | Web 框架（含 uvicorn、pydantic、pydantic-settings） |
| `requests` | HTTP 客户端 |
| `pandas` / `openpyxl` / `xlrd` / `xlsxwriter` | Excel 数据处理 |
| `pypdf` | PDF 文件处理 |

- Python >= 3.10
- 包管理器：`uv`（推荐）

## License

MIT
