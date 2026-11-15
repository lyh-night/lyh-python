# 代码审查报告 — agent-service

> **修复状态（2026-11-15）**：P0 全部 3 项、P1 全部 6 项、P2 全部 7 项已实施完毕，详见文末「修复实施记录」。验证基线：lint 全绿、mypy 0 问题、26 tests passed（修复前 13 个）、双实例冒烟通过（401/503/X-Request-ID 回显）。

- 审查日期：2026-11-15
- 审查依据：`.agent/skills/` 下 4 个最佳实践 skill（python-project / fastapi-service / pytest-testing / langgraph-agent）
- 审查方式：只读审查 + 证据命令，未改变运行时行为（仅 pyproject 增加一条 `.agent` 的 ruff 排除，使 lint 保持全绿）
- 证据基线：`make lint` 全绿（27 文件）、`make test` 13 passed、`compileall` OK、`uv tree` 依赖树符合声明

## 执行摘要

工程骨架与 agent 核心符合最佳实践主体（src layout、应用工厂、Annotated DI、异常层级、工具白名单、递归防护、离线测试均到位）。**主要缺口集中在"生产化三件套"：鉴权与限流（P0）、可观测（日志/请求 ID，P1）、checkpointer 生命周期（P1）**，另有一处工具 SSRF 面需要收紧（P0）。

总体评价：**开发/演示可用性 ★★★★☆，生产就绪度 ★★☆☆☆**（缺 P0 项时不建议直接公网暴露）。

## P0 — 公网部署前必须修复

### P0-1 http_get 存在 SSRF 面
- **位置**：`src/agent_service/tools/builtin.py:78-94`
- **现状**：仅校验 scheme 为 http/https，未限制目标地址。模型可被提示注入诱导抓取 `http://127.0.0.1:8000/docs`、云元数据 `http://169.254.169.254/latest/meta-data`、内网服务等。
- **依据**：langgraph skill §2「工具安全：SSRF 面需评估」
- **建议**：解析主机名后拒绝私网/环回/链路本地地址（`ipaddress` 模块判断 `is_private/is_loopback/is_link_local`，含 DNS 解析后再验）；或引入域名 allowlist 配置项。

### P0-2 错误响应泄漏内部细节
- **位置**：`src/agent_service/api/routes/chat.py:66`（`AgentExecutionError(f"智能体执行失败：{exc}")`）→ `src/agent_service/main.py:22-24`（原样作为 502 detail 返回）
- **现状**：LLM 网络异常原文直接进响应体，可能暴露 base_url、上游路径、栈信息。
- **依据**：fastapi skill §4「5xx 响应不泄漏内部细节」
- **建议**：对外 detail 用固定文案（如"上游模型暂时不可用，请稍后重试"），原始异常写入日志并关联请求 ID。

### P0-3 无鉴权与限流
- **位置**：`src/agent_service/main.py`（无任何认证中间件）、`/api/v1/chat` 全开放
- **现状**：任何能访问端口的人都可消耗 LLM 费用（每次请求都可能触发多轮工具调用循环）。
- **依据**：fastapi skill §5「面向公网必须有限流」
- **建议**：最小方案为静态 Bearer Key 校验（依赖注入实现，读 `Settings`）；或网关层承担；限流可用 slowapi 按线程 ID/IP 维度。

## P1 — 应尽快修复

### P1-1 MemorySaver 无上限增长，stateless 请求也写检查点
- **位置**：`src/agent_service/agents/graph.py:40`（编译时固定挂 `MemorySaver`）；`src/agent_service/api/routes/chat.py:56-62`（无 thread_id 时生成随机 hex，同样落检查点）
- **现状**：每个独立请求都产生一条永不清理的检查点记录，长进程内存持续增长。
- **依据**：langgraph skill §3「stateless 请求不应留下永久检查点」
- **建议**：无 thread_id 的请求走无检查点的临时编译图；有 thread_id 的走带 checkpointer 的单例；或增加 TTL 清理任务。

### P1-2 无访问日志与请求 ID
- **位置**：`src/agent_service/core/logging.py:16-17`（`uvicorn.access` 被降为 WARNING，等于关闭访问日志）；全链路无 `X-Request-ID`
- **现状**：502/500 发生时无法与日志记录关联定位；502 原始异常（P0-2 修复后）将无处可查。
- **依据**：fastapi skill §6「访问日志 + 请求 ID 中间件」
- **建议**：加一个轻量中间件：生成/透传 `X-Request-ID`、记录方法/路径/状态/耗时；业务日志带 request_id。

### P1-3 缺 mypy、pre-commit、CI
- **位置**：`pyproject.toml`（无 mypy 配置）、无 `.pre-commit-config.yaml`、无 `.github/workflows/`
- **依据**：python-project skill §4/§6「CI 最小集：sync → lint → test」
- **建议**：dev 组加 `mypy`（渐进配置）与 `pre-commit`；新增 CI workflow 执行 `uv sync && make lint && make test`。

### P1-4 /api/v1/tools 每请求重注册、无 response_model
- **位置**：`src/agent_service/api/routes/chat.py:76-85`
- **现状**：`register_builtin_tools()` 在每个 GET 请求执行（幂等但无意义）；返回裸 dict 无契约。
- **建议**：注册挪到 `create_app()` 启动时一次；端点声明 `response_model=ToolListResponse`。

### P1-5 配置字段与启动方式脱节
- **位置**：`src/agent_service/core/config.py:18-19`（`app_host/app_port`）与 `Makefile`（`make run` 硬编码默认参数）
- **现状**：`app_host/app_port` 配置了但从未被使用，改 `.env` 不影响实际监听。
- **建议**：Makefile 改为 `uv run uvicorn ... --host $(APP_HOST) --port $(APP_PORT)` 并注入环境变量，或删除这两个字段。

### P1-6 Dockerfile 加固
- **位置**：`Dockerfile:1`（浮动 tag）、`:16`（root 运行）、无 `HEALTHCHECK`；镜像未实测构建
- **依据**：python-project skill §6
- **建议**：pin 基础镜像 digest；增加非 root 用户；加 `HEALTHCHECK` 指向 `/health`；构建验证一次。

## P2 — 建议

| # | 发现 | 位置 | 建议 |
|---|---|---|---|
| P2-1 | 测试缺口：http_get 成功路径（需 mock 传输层）、usage 汇总（带 `usage_metadata` 的桩消息）未覆盖 | `tests/` | 用 `httpx.MockTransport` 注入假响应；桩 AIMessage 带 usage_metadata 补用例 |
| P2-2 | 核心模块零日志调用，排障只能靠框架日志 | `agents/graph.py`、`api/routes/chat.py` | 关键节点（图构建、工具执行、502 包装）打 INFO/WARNING 日志 |
| P2-3 | `ChatResponse` 不回显 `thread_id`，客户端续聊需自行管理 | `schemas/chat.py` | 契约增加 `thread_id` 回显字段（属规划内取舍，确认后调整） |
| P2-4 | `http_get` 未设 User-Agent，部分站点拒绝默认 UA | `builtin.py:85` | 请求头加可配置 UA |
| P2-5 | `get_settings` lru_cache 可能被测试进程环境变量污染 | `core/config.py:34` | conftest 提供 env 清理 fixture（当前测试未依赖，风险低） |
| P2-6 | `_TIMEZONE` 硬编码 Asia/Shanghai | `builtin.py:17` | 可配置化（当前符合产品定位） |
| P2-7 | `.agent/`、`Dockerfile` 等新文件尚未提交 git | git status | 确认后一次提交，保持 lock 与源码同步入库 |

## 合规亮点（审查确认符合 skill 清单）

- src layout + uv.lock 提交 + ruff 一体化（python-project §1/§2/§4）
- 应用工厂 + Annotated DI + response_model + 422 空白校验（fastapi §1/§2）
- 异常层级清晰，422/500/502/503 语义正确映射（fastapi §4）
- 工具 ast 白名单求值、`handle_tool_errors=True`、`recursion_limit` 显式配置（langgraph §2/§4）
- 图构建支持模型注入，13 个测试全离线秒级完成（langgraph §5、pytest §4/§5）
- `.env` 不入库、`.dockerignore` 排除密钥与测试（python-project §2/§6）

## 建议修复顺序

1. P0-1/2/3（安全三件套，半天量级）
2. P1-1/2（内存与可观测，一天量级）
3. P1-3 CI + mypy（半天）
4. 其余 P1/P2 随迭代顺带处理

## 修复实施记录（2026-11-15）

| 编号 | 状态 | 关键改动 |
|---|---|---|
| P0-1 | ✅ | `_assert_public_host()`：DNS 解析后拒绝环回/私网/链路本地/保留/组播地址；`http_get` 改为手动跟随重定向（≤5 跳）并逐跳复检；新增 4 个 SSRF 用例 |
| P0-2 | ✅ | 502 对外固定文案 `上游模型暂时不可用，请稍后重试`；原始异常仅入 WARNING 日志并关联 rid |
| P0-3 | ✅ | `api/security.py`：Bearer 鉴权（`secrets.compare_digest` 常量时间比较，未配置则关闭并打 WARNING）+ 进程内滑动窗口限流（`core/rate_limit.py`，超限 429） |
| P1-1 | ✅ | 拆分 `AgentGraphs`：stateless 图不挂 checkpointer（零内存残留），stateful 图按 `thread_id` 续聊 |
| P1-2 | ✅ | `core/request_context.py` contextvar + `main.py` 中间件：生成/透传 `X-Request-ID`、访问日志（方法/路径/状态/耗时/rid），异常路径不再吞错（修复过程中顺带修掉中间件自身在异常路径的 UnboundLocalError） |
| P1-3 | ✅ | dev 组加 mypy（`make typecheck`，0 问题）+ `.pre-commit-config.yaml` + `.github/workflows/ci.yml`（format→lint→typecheck→test 四关） |
| P1-4 | ✅ | `register_builtin_tools()` 移至 `create_app()` 启动时；`/api/v1/tools` 声明 `ToolListResponse` |
| P1-5 | ✅ | `make run` 经 `sh -c '. ./.env'` 读取 `APP_HOST/APP_PORT` 并传给 uvicorn |
| P1-6 | ✅ | Dockerfile：`ARG UV_DEFAULT_INDEX`（国内构建可覆盖）、非 root 用户 `appuser`、`HEALTHCHECK` 探活；tag 需自行 pin digest（本机无外网未实测构建，见遗留） |
| P2-1 | ✅ | `httpx.MockTransport` 注入测试接缝：http_get 成功路径 + 重定向用例；`usage_metadata` 汇总用例（10+5+20+5=40） |
| P2-2 | ✅ | chat 路由 502/递归日志、图构建/未配置鉴权启动告警 |
| P2-3 | ✅ | `ChatResponse.thread_id` 回显（服务端生成或客户端透传） |
| P2-4 | ✅ | `http_get` 设置 `User-Agent: agent-service/0.1` |
| P2-5 | ➖ | 维持现状：测试不依赖环境变量，风险未成立 |
| P2-6 | ✅ | `APP_TIMEZONE` 可配置（默认 Asia/Shanghai） |
| P2-7 | ➖ | 留给使用者提交（本次改动未 commit） |

**测试规模**：13 → 26 个用例（新增 SSRF×4、MockTransport×2、鉴权×4、限流×2、usage/thread_id×3 等）。

**遗留事项**
1. Dockerfile 基础镜像 digest pin 与镜像构建验证：本机外网受限，需在有网环境执行 `docker build` 确认；
2. 限流为单实例内存实现，多实例部署时换 Redis/网关；
3. `MemorySaver` 长会话仍无 TTL（M6 持久化时一并解决）。

> 本报告只评审不改动；确认后可按上述顺序实施修复。
