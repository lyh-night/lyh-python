# .agent/skills — Python 最佳实践技能库

供人与 agent 会话按需查阅的项目级技能库，采用 SKILL.md 格式（frontmatter：`name`/`description`）。

| Skill | 用途 |
| --- | --- |
| [python-project-best-practices](python-project-best-practices/SKILL.md) | 工程结构、打包、依赖、静态检查、CI/Docker |
| [fastapi-service-best-practices](fastapi-service-best-practices/SKILL.md) | FastAPI 服务分层、DI、错误处理、安全 |
| [pytest-testing-best-practices](pytest-testing-best-practices/SKILL.md) | 测试布局、fixture、mock 边界、离线原则 |
| [langgraph-agent-best-practices](langgraph-agent-best-practices/SKILL.md) | 图编排、工具调用、checkpointer、防失控 |

## 使用方式

- 新会话或新成员审查/扩展本项目时，先读对应 SKILL.md 的「检查清单」部分；
- 新增代码时按清单自检；审查时按清单逐项核对并输出分级结论（P0/P1/P2）。

## 参考来源

- PEP 8 / PEP 484 / PEP 621：<https://peps.python.org/>
- uv：<https://docs.astral.sh/uv/>
- ruff：<https://docs.astral.sh/ruff/>
- 12-Factor（配置）：<https://12factor.net/zh_cn/config>
- FastAPI：<https://fastapi.tiangolo.com/>
- fastapi-best-practices：<https://github.com/zhanymkanov/fastapi-best-practices>
- pytest good practices：<https://docs.pytest.org/en/stable/explanation/goodpractices.html>
- pytest best practices（Microsoft）：<https://github.com/microsoft/winml-cli/blob/main/docs/pytest-best-practices.md>
- LangGraph：<https://langchain-ai.github.io/langgraph/>
- Trail of Bits modern-python skill：<https://github.com/trailofbits/skills>

> 注：撰写时本机网络仅 PyPI 镜像可达，上述来源未能逐条在线核对；内容基于长期稳定的官方规范与社区共识，出处链接供深入阅读。
