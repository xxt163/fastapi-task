# fastapi-task

FastAPI 任务执行框架 — 通过 HTTP API 动态发现并执行 Python 任务脚本，支持任务失败邮件通知和 JSON 格式日志。

## 项目结构

```
fastapi-task/
├── app/
│   ├── api/                # API 路由层
│   │   ├── health.py       # 健康检查接口
│   │   └── task.py         # 任务列表 & 执行接口
│   ├── core/
│   │   ├── config.py       # 应用配置（基于 .env）
│   │   ├── exceptions.py   # 自定义异常
│   │   └── logger.py       # JSON 日志模块
│   ├── schemas/
│   │   └── task_schemas.py # 请求/响应模型
│   ├── services/
│   │   ├── email.py        # 邮件发送服务
│   │   └── task_loader.py  # 任务模块动态加载器
│   └── main.py             # FastAPI 应用入口
├── tasks/                  # 任务脚本目录（按 flow 分子目录）
│   └── demo/
│       └── read_excel.py   # 示例：读取 Excel 文件
├── logs/                   # 日志输出目录
├── run_dev.py              # 开发环境启动脚本
├── pyproject.toml
└── requirements.txt
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

```bash
python run_dev.py
```

服务默认运行在 `http://127.0.0.1:8000`，支持热重载（reload）。

### 配置 .env

在项目根目录创建 `.env` 文件：

```bash
# 基础配置
APP_NAME=FastAPI Task
DEBUG=true
LOG_LEVEL=INFO

# SMTP 邮件通知（任务失败时发送，不配置则跳过）
SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_USER=your@example.com
SMTP_PASSWORD=your_password
SMTP_FROM=noreply@example.com
SMTP_TO=admin@example.com
SMTP_USE_SSL=true
```

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

自动扫描 `tasks/` 目录，返回所有有效任务：

```json
{
  "tasks": [
    {"flow": "demo", "task": "read_excel", "path": "tasks/demo/read_excel.py"}
  ]
}
```

> 以 `_` 或 `.` 开头的目录/文件会被自动排除。

### 执行任务

```http
POST /task/run
Content-Type: application/json

{
  "flow": "demo",
  "task": "read_excel",
  "data": {
    "file_path": "/path/to/file.xlsx"
  }
}
```

响应：

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

## 编写任务

在 `tasks/<flow>/` 目录下创建 `.py` 文件，实现 `run(data)` 函数：

```python
# tasks/demo/hello.py

def run(data: dict):
    name = data.get("name", "World")
    return {"message": f"Hello, {name}!"}
```

规则：

- 每个任务文件必须包含 `run(data)` 函数，接收一个 `dict` 参数，返回可序列化的结果
- 文件名即任务名（不含 `.py`），目录名即 flow 名
- flow 名只能包含小写字母和数字，task 名可额外包含下划线

## 日志

日志按天分目录存储为 JSON 格式：

```
logs/
└── 2026-06-29/
    ├── service.log       # 服务级日志（追加写入）
    ├── email.log         # 邮件服务日志
    └── demo/
        └── read_excel-143025.log   # 每次任务执行独立文件
```

## 邮件通知

任务执行失败时自动发送邮件通知，需要配置 `.env` 中的 SMTP 参数。未配置时静默跳过。

## 依赖

- Python >= 3.10
- FastAPI >= 0.100.0
- Uvicorn >= 0.20.0
- pydantic-settings >= 2.0.0
- pandas / openpyxl / xlrd / pypdf（任务脚本可按需使用）

## License

MIT
