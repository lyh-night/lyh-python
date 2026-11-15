# Agent Service

基于 **Python + FastAPI** 的对话智能体服务骨架。智能体核心（LangGraph 工具调用循环 + DeepSeek 模型）将在后续里程碑接入，当前工程已具备完整的分层结构与格式化/lint 工具链。

## 技术栈

- Python 3.12+ / [uv](https://docs.astral.sh/uv/) 依赖管理
- FastAPI + Uvicorn（应用工厂模式）
- pydantic-settings 配置管理（`.env` 注入）
- ruff：格式化 + lint 一体化；pytest：测试

## 快速开始

```bash
uv sync     # 安装依赖（自动创建 .venv）
make run    # 启动开发服务，默认 http://127.0.0.1:8000
```

环境变量：复制 `.env.example` 为 `.env` 按需修改；`.env` 不入库，`DEEPSEEK_API_KEY` 在 M2 接入后生效。

## 常用命令

| 命令 | 说明 |
| --- | --- |
| `make run` | 启动开发服务（热重载） |
| `make format` | ruff 格式化 + 自动修复 lint 问题 |
| `make lint` | 检查格式与 lint（提交前/CI 使用） |
| `make test` | 运行 pytest |

ruff 规则集在 `pyproject.toml` 的 `[tool.ruff]` 配置：`E`/`F`/`I`/`UP`/`B`/`SIM`，行宽 100，双引号。

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 健康检查，返回 `{status, version}` |
| POST | `/api/v1/chat` | 对话接口（骨架阶段返回 501，契约已定义） |
| GET | `/docs` | Swagger 文档 |

`POST /api/v1/chat` 请求体：

```json
{
  "message": "现在几点了",
  "thread_id": "可选，传入则服务端按会话续聊"
}
```

响应体（核心接入后）：

```json
{
  "reply": "智能体最终回复",
  "tool_trace": [{ "tool": "工具名", "args": {}, "result": "执行结果" }],
  "usage": { "total_tokens": 0 }
}
```

## 目录结构

```
src/agent_service/
├── main.py          # create_app() 应用工厂
├── core/            # config（pydantic-settings）、logging
├── schemas/         # 请求/响应 DTO（chat.py）
├── llm/             # 模型构建（桩，M2 实现）
├── tools/           # 工具注册中心（registry.py，M3 增加内置工具）
├── agents/          # LangGraph 图（桩，M3 实现）
└── api/             # deps 依赖注入 + routes 路由
```

## 新增工具指南（M3 接入后）

1. 在 `src/agent_service/tools/builtin.py` 用 `@tool` 编写函数；
2. 调用 `registry.register_tool()` 注册；
3. 智能体与 `/api/v1/tools` 查询自动生效，其余模块零改动。

## 路线图

- [x] M1 工程骨架 + 格式化/lint 工具链（当前）
- [ ] M2 LLM 接入（langchain-openai 指向 DeepSeek）
- [ ] M3 LangGraph 工具调用循环 + 内置工具 + tool_trace
- [ ] M4 SSE 流式输出 / 会话持久化
- [ ] M5 Docker 与部署
