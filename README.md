# FastAPI Task

FastAPI Task 是一个轻量级的任务执行框架。你可以把 Python 脚本放进任务目录中，通过 HTTP API 自动发现、执行并获取结果，同时支持日志采集、失败告警、SMB 挂载和并发控制。

## 为什么使用它

- 通过目录结构自动发现任务脚本，无需额外注册
- 提供简洁的 HTTP 接口：健康检查、任务列表、任务执行
- 支持任务超时、并发限制和失败邮件通知
- 任务脚本仅需实现 `run(data)`，输出日志时直接使用 `print()`
- 适合批处理脚本、数据处理任务、自动化流程接入

## 功能特性

- 动态加载任务：从 `tasks/` 目录自动发现任务
- 任务执行接口：`GET /task/list` 和 `POST /task/run`
- 并发控制：通过环境变量限制同时执行的任务数
- 超时控制：任务执行超时后返回错误，但线程继续运行
- 统一日志：将任务输出转为 JSON 日志，按天切分
- 可选邮件通知：任务失败时自动发送邮件
- 可选 SMB 挂载：适用于 Windows 服务场景

## 项目结构

```text
fastapi-task/
├── app/
│   ├── api/                # API 路由
│   ├── core/               # 配置、日志、SMB 挂载
│   ├── schemas/            # Pydantic 模型
│   ├── services/           # 邮件、任务加载
│   └── main.py             # FastAPI 应用入口
├── tasks/                  # 任务脚本目录
│   └── demo/
│       ├── read_excel.py
│       └── read_file.py
├── scripts/                # Windows 服务脚本
├── run_dev.py              # 开发模式启动
├── run_prod.py             # 生产模式启动
├── pyproject.toml
├── requirements.txt
└── README.md
```

## 快速开始

### 1. 环境要求

- Python 3.10+
- 推荐使用 `uv`，也可以使用 `pip`

### 2. 安装依赖

```bash
uv sync
```

如果你使用 `pip`：

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，至少确认以下配置：

```env
APP_NAME=FastAPI Task
APP_HOST=127.0.0.1
APP_PORT=8000
DEBUG=false
LOG_LEVEL=INFO
WORKERS=1

TASK_LIST_CACHE_TTL=30
TASK_TIMEOUT_SECONDS=3600
TASK_MAX_CONCURRENCY=5
```

如需启用邮件或 SMB 挂载，请继续配置相应项。

### 4. 启动服务

开发模式：

```bash
python run_dev.py
```

生产模式：

```bash
python run_prod.py
```

启动后访问：

```text
http://127.0.0.1:8000/health
```

## API 接口

### 健康检查

```http
GET /health
```

响应示例：

```json
{
  "status": "healthy",
  "checks": {
    "tasks_dir": "ok",
    "smb_mount": "ok"
  }
}
```

### 获取任务列表

```http
GET /task/list
```

### 执行任务

```http
POST /task/run
Content-Type: application/json
```

请求体示例：

```json
{
  "flow": "demo",
  "task": "read_file",
  "data": {
    "file_path": "F:/test.txt"
  }
}
```

## 编写任务

在 `tasks/<flow>/` 目录下创建 `.py` 文件，并实现 `run(data)` 函数即可：

```python
# tasks/demo/hello.py

def run(data: dict):
    name = data.get("name", "World")
    print(f"收到请求: name={name}")
    return {"message": f"Hello, {name}!"}
```

服务端会自动捕获你的 `print()` 输出，并写入 JSON 日志。

## 日志

日志默认按天切分，保存在 `logs/` 目录下，格式为 JSON Lines，便于接入日志系统或后续分析。

## 配置说明

项目主要支持以下环境变量：

- `APP_*`：服务地址、端口、名称
- `TASK_*`：任务缓存、超时、并发数
- `SMTP_*`：邮件通知配置
- `SMB_*`：Windows 场景下的共享盘挂载配置

## Windows 服务部署

如果你希望把服务部署为 Windows 服务：

```powershell
./scripts/create_service.ps1
```

卸载：

```powershell
./scripts/remove_service.ps1
```

## 贡献指南

欢迎提交 Issue 或 Pull Request。

建议步骤：

1. Fork 本仓库
2. 创建功能分支
3. 提交变更并说明目的
4. 发起 Pull Request

## 许可证

本项目基于 Apache 2.0 许可证开源。
