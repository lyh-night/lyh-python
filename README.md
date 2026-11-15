# Agent Service

基于 **Python + FastAPI + LangGraph** 的对话智能体服务：DeepSeek 模型（OpenAI 兼容协议）+ 工具调用循环（agent ↔ tools）+ 会话续聊。

## 技术栈

- Python 3.12+ / [uv](https://docs.astral.sh/uv/) 依赖管理
- FastAPI + Uvicorn（应用工厂模式）
- LangGraph：`StateGraph` 编排 agent ↔ tools 循环，`MemorySaver` 支持按 `thread_id` 续聊
- langchain-openai：以 OpenAI 兼容协议接入 DeepSeek
- ruff：格式化 + lint 一体化；pytest：测试（桩模型，全程离线）

## 快速开始

```bash
uv sync                                            # 安装依赖
cp .env.example .env                               # 填写 DEEPSEEK_API_KEY
make run                                           # http://127.0.0.1:8000
```

未配置密钥时服务可正常启动，`POST /api/v1/chat` 返回 503 并提示补齐配置。

## 常用命令

| 命令 | 说明 |
| --- | --- |
| `make run` | 启动开发服务（热重载，读取 .env 的 APP_HOST/APP_PORT） |
| `make format` | ruff 格式化 + 自动修复 lint 问题 |
| `make lint` | 检查格式与 lint（提交前/CI 使用） |
| `make typecheck` | mypy 类型检查 |
| `make test` | 运行 pytest |

ruff 规则集在 `pyproject.toml` 的 `[tool.ruff]`：`E`/`F`/`I`/`UP`/`B`/`SIM`，行宽 100，双引号。

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 健康检查，返回 `{status, version}` |
| POST | `/api/v1/chat` | 对话接口 |
| GET | `/api/v1/tools` | 已注册工具清单（名称+描述） |
| GET | `/docs` | Swagger 文档 |

`POST /api/v1/chat` 请求体：

```json
{
  "message": "现在几点了",
  "thread_id": "可选；传入则按该会话续聊，不传则本次请求独立成会话"
}
```

响应体：

```json
{
  "reply": "现在是北京时间 21:35 …",
  "tool_trace": [{ "tool": "get_current_time", "args": {}, "result": "…" }],
  "usage": { "total_tokens": 512 }
}
```

### 错误码

| 状态码 | 场景 |
| --- | --- |
| 401 | 已配置 `API_AUTH_TOKEN` 但请求未携带/携带错误的 Bearer Token |
| 422 | message 为空/全空白等输入校验失败 |
| 429 | 触发限流（`RATE_LIMIT_PER_MINUTE`，默认 30 次/分钟/客户端） |
| 500 | Agent 循环超出递归上限（`AGENT_RECURSION_LIMIT`，默认 25） |
| 502 | LLM 网络/超时等上游执行错误（响应为固定文案，原始异常仅入日志） |
| 503 | 未配置 `DEEPSEEK_API_KEY` |

### 安全

- **鉴权**：`API_AUTH_TOKEN` 非空时所有 `/api/v1/chat` 请求需携带 `Authorization: Bearer <token>`；留空则关闭鉴权（仅限本地开发，启动时打 WARNING）
- **限流**：进程内滑动窗口（单实例）；多实例部署请换网关层或 Redis 实现
- **SSRF 防护**：`http_get` 工具拒绝环回/私网/链路本地/保留地址，重定向逐跳复检
- **信息不外泄**：5xx 响应为固定文案，原始异常仅写入日志（可按响应头 `X-Request-ID` 关联）

## 架构

```
POST /api/v1/chat
      │
      ▼
┌─ LangGraph（MemorySaver 按 thread_id 检查点）─────────────┐
│  START → agent（ChatOpenAI→DeepSeek，bind_tools）          │
│              │ 含 tool_calls                               │
│              ▼                                             │
│            tools（ToolNode：time/calculator/http_get）      │
│              │ 工具结果回传                                 │
│              └──→ agent …（无 tool_calls 时 → END）         │
└────────────────────────────────────────────────────────────┘
      │
      ▼
ChatResponse{reply, tool_trace, usage}
```

- 工具执行异常不会打断请求：`ToolNode(handle_tool_errors=True)` 将错误作为消息回传，模型可自行调整重试。
- **双图设计**：带 `thread_id` 的请求走挂 `MemorySaver` 的 stateful 图（按会话续聊）；不带则走无检查点的 stateless 图，不在内存中留下任何会话记录。会话历史重启即失，生产多实例需替换为持久化 checkpointer。
- `tool_trace` 由消息序列按 `tool_call_id` 配对还原，便于前端展示调用过程。
- 每个响应携带 `X-Request-ID`（可由客户端透传），与服务端日志关联。

## 目录结构

```
src/agent_service/
├── main.py          # create_app() 应用工厂 + 全局异常处理（503/502/500）
├── core/            # config、logging、errors
├── schemas/         # 请求/响应 DTO（chat.py）
├── llm/model.py     # ChatOpenAI → DeepSeek（build_chat_model / get_chat_model）
├── tools/
│   ├── registry.py  # 工具注册中心
│   └── builtin.py   # 内置工具：get_current_time / calculator / http_get
├── agents/graph.py  # StateGraph 编排（build_agent_graph / get_agent_graph）
└── api/             # deps 依赖注入 + routes（health、chat）
```

## 新增工具指南

1. 在 `src/agent_service/tools/builtin.py` 用 `@tool` 编写函数，并加入 `BUILTIN_TOOLS` 列表；
2. `register_builtin_tools()` 自动注册（幂等），智能体与 `GET /api/v1/tools` 立即生效，其余模块零改动；
3. 在 `tests/test_tools.py` 补充对应用例。

## 环境变量

见 `.env.example`。注意：`.env` 在进程启动时读取，修改后需重启服务（`uvicorn --reload` 只监听代码变更）。

## Docker

```bash
docker build -t agent-service .
docker run --rm -p 8000:8000 --env DEEPSEEK_API_KEY=sk-xxx agent-service
```

## 路线图

- [x] M1 工程骨架 + 格式化/lint 工具链
- [x] M2 LLM 接入（langchain-openai 指向 DeepSeek）
- [x] M3 LangGraph 工具调用循环 + 内置工具 + tool_trace + 会话续聊
- [x] M4 错误处理（503/502/500/422）+ 离线测试 + Dockerfile
- [x] M4.5 安全加固：Bearer 鉴权、限流、SSRF 防护、错误信息脱敏、请求 ID/访问日志、mypy + CI（CI/CD 与安全审查详见 `REVIEW.md`）
- [ ] M5 SSE 流式输出（`graph.stream(stream_mode="messages")` 已预留）
- [ ] M6 会话持久化（MemorySaver → SQLite/Postgres checkpointer）
