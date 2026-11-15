---
name: fastapi-service-best-practices
description: FastAPI 服务最佳实践：应用工厂、依赖注入、请求校验、错误处理、安全与可观测。适用于 API 层设计与审查。
---

# FastAPI 服务最佳实践

## 1. 应用组织

**检查清单**

- [ ] 应用工厂 `create_app()`：路由注册、中间件、异常处理器集中配置，便于测试多实例
- [ ] 路由按资源拆分文件，`APIRouter(prefix=..., tags=...)` 分组；路径版本化（`/api/v1`）
- [ ] 分层单向依赖：routes → services/agents → infra，路由层不写业务逻辑
- [ ] 依赖注入用 `Annotated[T, Depends(...)]` 类型别名（可复用、避免 B008、易于 override）

**示例**

```python
AppSettings = Annotated[Settings, Depends(get_app_settings)]

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, settings: AppSettings) -> ChatResponse: ...
```

## 2. 请求/响应模型（Pydantic v2）

**检查清单**

- [ ] 每个端点声明 `response_model`，禁止返回裸 dict 漂移契约
- [ ] 请求模型在字段级校验（`min_length`/`Field`/`field_validator`），全空白、超长、非法枚举在 422 拦截
- [ ] DTO 与领域模型分离：不直接把 ORM/内部对象序列化给客户端

## 3. async/sync 端点

**检查清单**

- [ ] 端点内调用阻塞库（requests、同步 SDK、CPU 密集）→ 用 `def`（自动进线程池）；全异步链路才用 `async def`
- [ ] `async def` 端点内禁止阻塞调用（同步 sleep、同步 DB），否则拖垮事件循环
- [ ] 一个端点内混用同步阻塞 + async 时，优先统一为 sync 端点或用 `run_in_executor`

## 4. 错误处理

**检查清单**

- [ ] 应用异常 → HTTP 语义映射集中在 exception handler（401/403/404/422/429/500/502/503）
- [ ] 5xx 响应不泄漏内部细节（栈、SQL、异常原文）；`detail` 用受控文案，原文进日志
- [ ] 上游服务失败映射 502/504，配置缺失映射 503，输入非法 422——语义不可混用
- [ ] 全链路兜底：未捕获异常也返回结构化 JSON 而非裸 500

## 5. 安全

**检查清单**

- [ ] 密钥只经环境变量注入；错误响应/日志/异常文本三处检查不泄漏
- [ ] CORS 显式白名单，禁止 `*` 搭配凭证
- [ ] 面向公网必须有限流（slowapi/网关层）与请求体大小限制
- [ ] 依赖固定 + `pip-audit`；调试端点（docs）生产可关（`docs_url=None`）

## 6. 可观测

**检查清单**

- [ ] 访问日志：方法、路径、状态码、耗时、请求 ID（中间件注入 `X-Request-ID`）
- [ ] `/health` 存活探针；需要时加 `/ready` 依赖就绪探针
- [ ] 用量/成本类指标（token、上游调用次数）结构化记录，而非只塞响应体

## 7. 测试接入

**检查清单**

- [ ] `TestClient(create_app())` + `app.dependency_overrides[...]` 替换重依赖（LLM/DB/时间）
- [ ] 错误路径必须测试：每个 exception handler 至少一个用例
- [ ] 契约测试：response 字段、状态码、错误 detail 关键词

## 出处

- FastAPI 官方文档（含 async/sync 与依赖注入章节）：<https://fastapi.tiangolo.com/>
- fastapi-best-practices（社区共识）：<https://github.com/zhanymkanov/fastapi-best-practices>
- Pydantic v2 文档：<https://docs.pydantic.dev/latest/>
