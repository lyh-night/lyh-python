---
name: langgraph-agent-best-practices
description: LangGraph 智能体最佳实践：状态与 reducer、工具调用循环、checkpointer 选型、防失控与可测试性。适用于 agent 设计与审查。
---

# LangGraph 智能体最佳实践

## 1. 图与状态设计

**检查清单**

- [ ] 优先 `MessagesState` + `add_messages` reducer 处理对话历史；自定义状态字段要有明确 reducer
- [ ] ⚠️ `add_messages` 按消息 id **upsert**（同 id 替换而非追加）：任何循环产出消息的组件（含测试桩）必须保证 id 唯一，否则循环提前终止
- [ ] 节点函数只做一件事：`agent` 产出模型消息、`tools` 执行工具；条件边用内置 `tools_condition` 而非手写判断
- [ ] 编译期（`compile()`）与运行期（`invoke(config=...)`）配置分离：`recursion_limit`、`thread_id` 属于运行期

## 2. 工具调用循环

**检查清单**

- [ ] `llm.bind_tools(tools)` 后再入图；工具注册中心集中管理，幂等注册
- [ ] `ToolNode(..., handle_tool_errors=True)`：工具异常转为错误消息回传模型自纠错，而不是让整个请求 5xx
- [ ] 工具设计四要素：描述性 docstring（即工具描述）、显式输入 schema、超时与大小上限、可幂等重试
- [ ] 工具安全：危险操作白名单（如禁 `eval`）、URL 协议校验、SSRF 面（内网地址）需评估、结果截断防上下文爆炸

## 3. Checkpointer 与会话

**检查清单**

- [ ] 选型：开发/演示用 `MemorySaver`（进程内，重启即失且无上限增长）；生产用 `SqliteSaver`/`PostgresSaver`
- [ ] stateless 请求与有状态请求分开处理：无 thread_id 的请求不应留下永久检查点（TTL 清理或随机线程 + 过期）
- [ ] `thread_id` 是会话边界：鉴权时校验归属，防止跨用户读取历史

## 4. 防失控（必须）

**检查清单**

- [ ] `recursion_limit` 显式配置并映射为明确错误响应（不裸 500 崩栈）
- [ ] 模型调用超时（`timeout`）+ 有限重试（`max_retries`）必配
- [ ] 单轮 token 预算/工具调用次数上限可配置，防提示注入导致的循环与费用失控

## 5. 可测试性与可观测

**检查清单**

- [ ] 图构建函数接受模型注入参数（`build_agent_graph(model=None)`），测试传桩模型
- [ ] 桩模型实现 `bind_tools` 并模拟真实行为（消息 id 唯一、脚本化 tool_calls）
- [ ] 工具轨迹可还原：按 `tool_call_id` 配对 AIMessage.tool_calls ↔ ToolMessage，供前端展示与审计
- [ ] 用量统计（`usage_metadata.total_tokens`）逐轮累加并上报；可观测接入 callbacks/LangSmith
- [ ] 流式输出预留：`graph.stream(..., stream_mode="messages")` 与 API 层 SSE 解耦演进

## 6. 部署形态

**检查清单**

- [ ] 编译后的图单例复用（`lru_cache`），但注意配置更新需重启（或引入失效机制）
- [ ] 阻塞式 `graph.invoke` 在 FastAPI 中放 sync 端点（线程池）；全异步栈用 `graph.ainvoke`
- [ ] 多实例部署时 checkpointer 必须外置（内存版不可共享）

## 出处

- LangGraph 官方文档（Graph API / Tools / Persistence / Streaming）：<https://langchain-ai.github.io/langgraph/>
- add_messages 语义（upsert by id）：<https://langchain-ai.github.io/langgraph/concepts/low_level/#messagesstate>
- DeepSeek OpenAI 兼容协议：<https://api-docs.deepseek.com/>
