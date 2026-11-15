---
name: pytest-testing-best-practices
description: pytest 测试最佳实践：布局、fixture、参数化、mock 边界与离线原则。适用于编写与审查测试。
---

# pytest 测试最佳实践

## 1. 布局与命名

**检查清单**

- [ ] `tests/` 镜像源码结构：`test_<module>.py` 对应 `<module>.py`，按类分组场景（`TestXxx`）
- [ ] 测试名表达行为：`test_<被测>_<场景>_<预期>`；docstring 一句话补充上下文
- [ ] `pyproject.toml` 声明 `testpaths` 与 `addopts`（如 `-q`），保证 `pytest` 裸命令可用
- [ ] 测试间零依赖、零共享可变状态；顺序无关（禁止依赖执行顺序）

## 2. Fixture

**检查清单**

- [ ] 公共 fixture 进 `conftest.py`，跨目录共享；一个 fixture 只做一件事
- [ ] 作用域最小化：默认 `function`，仅无状态只读对象用 `session/module`
- [ ] 工厂 fixture 返回闭包，用于"同构不同参"的对象家族
- [ ] 清理逻辑用 `yield` fixture 的后半段或 `finally`，避免污染其他测试

**示例**

```python
@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)
```

## 3. 参数化与断言

**检查清单**

- [ ] 同逻辑多输入用 `@pytest.mark.parametrize`，而不是复制粘贴测试函数
- [ ] 断言具体值/正则/不变量，禁止只断言 `is not None` 蒙混过关
- [ ] 异常路径用 `pytest.raises` 并校验异常类型与关键信息

## 4. Mock 边界（最易错的一节）

**检查清单**

- [ ] 只 mock 系统边界：网络、时钟、外部模型、文件系统；绝不 mock 被测逻辑本身
- [ ] mock 贴近使用点（依赖注入 > monkeypatch 全局单例）；FastAPI 用 `dependency_overrides`，LangGraph 注入假模型
- [ ] 桩对象必须模拟真实行为差异：真实系统"每次响应 id 唯一/顺序递增"，桩也要模拟（共享可变对象会踩 reducer/去重类坑）
- [ ] `monkeypatch` 优于手写 patch 字符串路径；patch 目标用"使用处"而非"定义处"

## 5. 离线与速度

**检查清单**

- [ ] 单元/接口测试默认零网络、零数据库：任一测试挂掉时能 30 秒内定位
- [ ] 外部服务测试单独打标（`@pytest.mark.integration`）并在 CI 分离
- [ ] 全套测试秒级完成是常态；超过 10s 先查网络等待与无谓 sleep

## 6. 覆盖率与信号

**检查清单**

- [ ] 覆盖率是信号不是目标：错误路径、边界值必须覆盖，行数凑数无意义
- [ ] 新功能先补失败用例再实现（可先以 `xfail` 占位）
- [ ] 测试代码同样过 lint（ruff `PT` 规则组专测 pytest 风格）

## 出处

- pytest 官方 good practices：<https://docs.pytest.org/en/stable/explanation/goodpractices.html>
- pytest best practices（Microsoft）：<https://github.com/microsoft/winml-cli/blob/main/docs/pytest-best-practices.md>
- FastAPI testing：<https://fastapi.tiangolo.com/tutorial/testing/>
