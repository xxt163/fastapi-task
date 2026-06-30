# fastapi-task

FastAPI 任务执行框架 — 将 Python 脚本放入 `tasks/` 目录即可通过 HTTP API 发现并执行，支持任务失败邮件通知和 JSON 格式日志。

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
│   │   └── logger.py       # JSON 日志（按天分目录，独立文件）
│   ├── schemas/
│   │   └── task_schemas.py # 请求/响应 Pydantic 模型
│   ├── services/
│   │   ├── email.py        # SMTP 邮件发送（附件分块读取，支持 SSL/STARTTLS）
│   │   └── task_loader.py  # 任务动态加载 + 任务列表 TTL 缓存
│   └── main.py             # FastAPI 应用入口
├── tasks/                  # 任务脚本目录（按 flow 分子目录）
│   └── demo/
│       └── read_excel.py   # 示例：pandas 读取 Excel
├── scripts/                # Windows 服务管理脚本
│   ├── create_service.ps1  # 安装为 Windows 服务（NSSM）
│   └── remove_service.ps1  # 卸载 Windows 服务
├── run_dev.py              # 开发启动（127.0.0.1:8000，热重载）
├── run_prod.py             # 生产启动（0.0.0.0:8000，读取 settings）
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
pip install fastapi[standard]
pip install -r requirements.txt
```

### 2. 配置 .env

在项目根目录创建 `.env` 文件：

```bash
# 基础配置
APP_NAME=FastAPI Task
DEBUG=false
LOG_LEVEL=INFO

# 任务列表缓存 TTL（秒），默认 30
TASK_LIST_CACHE_TTL=30

# 生产启动工作进程数（Windows 上必须为 1）
WORKERS=1

# SMTP 邮件通知（任务失败时发送，不配置则跳过）
SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_USER=your@example.com
SMTP_PASSWORD=your_password
SMTP_TO=admin@example.com
SMTP_USE_SSL=true
SMTP_STARTTLS=true
```

### 3. 启动服务

```bash
# 开发模式（热重载）
python run_dev.py

# 生产模式
python run_prod.py
```

服务运行在 `http://127.0.0.1:8000`（开发）或 `http://0.0.0.0:8000`（生产）。

## API 接口

### 健康检查

```http
GET /health
```

响应：

```json
{"status": "healthy"}
```

### 获取任务列表

```http
GET /task/list
```

扫描 `tasks/` 目录，返回所有有效任务。带 30 秒 TTL 缓存（可通过 `TASK_LIST_CACHE_TTL` 调整）：

```json
{
  "tasks": [
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
  "task": "read_excel",
  "data": {
    "file_path": "D:/data/report.xlsx"
  }
}
```

成功响应：

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "flow": "demo",
  "task": "read_excel",
  "status": "success",
  "result": { ... },
  "error": null,
  "duration_ms": 1250
}
```

失败响应：

```json
{
  "task_id": "a1b2c3d4-...",
  "flow": "demo",
  "task": "read_excel",
  "status": "failed",
  "result": null,
  "error": "Traceback ...",
  "duration_ms": 520
}
```

## 编写任务

在 `tasks/<flow>/` 下创建 `.py` 文件，实现 `run(data)` 函数即可：

```python
# tasks/demo/hello.py

def run(data: dict):
    name = data.get("name", "World")
    return {"message": f"Hello, {name}!"}
```

命名规则：

| 项目 | 规则 | 示例 |
|------|------|------|
| flow（目录名） | 小写字母开头，仅含小写字母和数字 | `demo`, `etl_v1` ❌ |
| task（文件名） | 小写字母开头，可含字母、数字、下划线 | `read_excel`, `parse_pdf` |

## 日志

日志按天分目录，JSON 格式：

```
logs/
└── 2026-06-30/
    ├── service.log              # 服务级日志（当天追加写入）
    ├── email.log                # 邮件服务日志
    └── demo/
        └── read_excel-143025.log  # 每次任务执行独立文件
```

每行一条 JSON，包含 `time`、`level`、`logger`、`msg`，以及可选的 `task_id`、`error`、`duration_ms` 等字段。

## 邮件通知

任务执行失败时自动发送 HTML 邮件通知。

- 配置 `.env` 中的 SMTP 参数即可启用
- 未配置时静默跳过，不影响任务执行
- 支持 SSL（端口 465）和 STARTTLS（端口 587）
- 附件大小限制 50MB，超过抛出 `ValueError`

## Windows 服务部署

使用 NSSM 将应用注册为 Windows 服务：

```powershell
# 安装服务（需要管理员权限）
.\scripts\create_service.ps1

# 卸载服务
.\scripts\remove_service.ps1
```

服务配置为自动启动、失败自动重启，可选每日定时重启（默认凌晨 3:00）。

## 注意事项

- **Windows 上 `WORKERS` 必须设为 1**（uvicorn 多进程依赖 `fork`，Windows 不支持）
- 任务通过 `importlib` 动态加载，首次调用会触发模块 import，后续调用命中缓存，几乎零开销
- 任务在独立线程中执行，不会阻塞事件循环

## 依赖

| 包 | 用途 |
|---|---|
| `fastapi[standard]` >= 0.138.1 | Web 框架（含 uvicorn、pydantic） |
| `pydantic-settings` | .env 配置管理 |
| `requests` | HTTP 客户端（任务脚本使用） |
| `pandas` / `openpyxl` / `xlrd` | Excel 数据处理 |
| `pypdf` | PDF 文件处理 |

- Python >= 3.10
- 包管理器：`uv`（推荐）

## License

MIT
