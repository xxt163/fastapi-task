"""
Task 服务调度客户端 —— 先 /health 检查存活，再调用任务，支持多服务容灾。

用法:
    python client.py <flow> <task> [data_json]
    python client.py demo read_excel
    python client.py demo read_excel '{"file_path":"/tmp/test.xlsx"}'
"""

import json
import sys
import requests

SERVERS = [
    "http://127.0.0.1:8000",
    # "http://10.0.0.2:8000",   # 备机
]


def run_task(flow: str, task: str, data: dict | None = None) -> dict:
    """遍历 SERVERS，选第一个健康的节点执行任务"""
    data = data or {}
    last_error: Exception | None = None

    for server in SERVERS:
        base = server.rstrip("/")
        print(f"[{base}] 检查服务 ... ", end="")

        # 1. 健康检查
        try:
            resp = requests.get(f"{base}/health", timeout=5)
            resp.raise_for_status()
            print("在线")
        except requests.RequestException as e:
            print(f"离线 ({e})")
            last_error = e
            continue

        # 2. 执行任务
        print(f"[{base}] 执行: {flow}/{task}")
        try:
            resp = requests.post(
                f"{base}/task/run",
                json={"flow": flow, "task": task, "data": data},
                timeout=600,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"[{base}] 调用失败: {e}")
            last_error = e
            continue

    raise ConnectionError(f"所有 {len(SERVERS)} 个服务均不可达") from last_error


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python client.py <flow> <task> [data_json]", file=sys.stderr)
        sys.exit(1)

    flow = sys.argv[1]
    task = sys.argv[2]
    data = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}

    try:
        result = run_task(flow, task, data)
    except ConnectionError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(2)
    except requests.Timeout:
        print("请求超时", file=sys.stderr)
        sys.exit(2)

    print(f"\ntask_id: {result['task_id']}")
    print(f"状态:    {result['status']}  ({result['duration_ms']}ms)")
    if result["status"] == "failed":
        print(f"错误:\n{result['error'][:1000]}")
        sys.exit(1)
    else:
        print(f"结果:\n{json.dumps(result['result'], ensure_ascii=False)}")