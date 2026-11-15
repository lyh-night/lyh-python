---
name: python-project-best-practices
description: Python 项目工程最佳实践：结构、打包、依赖、静态检查、CI 与 Docker。适用于新项目搭建、工程审查与重构。
---

# Python 项目工程最佳实践

## 1. 工程结构

**检查清单**

- [ ] src layout：包置于 `src/<package>/`，测试置顶 `tests/`，避免"装了才测得准"的隐性耦合
- [ ] 单一可发布包：`pyproject.toml` 为唯一配置入口（元数据、依赖、工具配置）
- [ ] 目录职责清晰：`core/`（配置/日志/异常）、`schemas/`、领域模块、`api/` 层各自独立，禁止循环导入
- [ ] `__init__.py` 保持轻量（只放 `__version__` 与导出，不放重逻辑）

**反例**：配置散落在 `config.py`/`settings.py`/环境变量三处；包内 import 依赖运行目录。

## 2. 打包与依赖（PEP 621 + uv）

**检查清单**

- [ ] `pyproject.toml`：`requires-python` 明确下限；`dependencies` 用 `>=` 下限约束（库）或锁定（应用）
- [ ] 应用项目必须提交 `uv.lock`/`poetry.lock`（可复现构建）；库项目可不提交
- [ ] dev 依赖与运行时依赖分组（PEP 735 `dependency-groups` 或 `[project.optional-dependencies]`）
- [ ] 构建后端声明完整（如 hatchling 需 `[tool.hatch.build.targets.wheel] packages`）
- [ ] 依赖定期审计：`uv tree` 查依赖树；`pip-audit` 扫已知漏洞
- [ ] `.gitignore` 覆盖 `.venv/`、缓存目录、`.env`（密钥绝不入库）

## 3. 配置管理（12-Factor）

**检查清单**

- [ ] 配置来自环境（pydantic-settings + `.env`），代码零硬编码密钥/URL/端口
- [ ] 配置类单例化（`lru_cache`），字段带类型与默认值；新增配置同步更新 `.env.example`
- [ ] 敏感信息不进日志、不进异常文本、不进错误响应

## 4. 代码风格与类型

**检查清单**

- [ ] ruff 一体化（format + lint），规则集至少 `E,F,I,UP,B,SIM`；建议补 `C4,RET,RUF,PT`（pytest 专用 PT）
- [ ] 行宽/引号等风格统一写入 `pyproject.toml`，禁止口头约定
- [ ] 类型标注覆盖公共函数与模块边界；建议接入 mypy（渐进式：先 `--ignore-missing-imports`，逐步收紧）
- [ ] 公共函数/模块有 docstring；复杂逻辑有行内注释解释"为什么"而非"是什么"

## 5. 异常与日志

**检查清单**

- [ ] 定义应用异常层级（基类 + 语义子类），在边界层统一转换为响应/日志
- [ ] 禁止裸 `except:`；`except Exception` 必须配 `raise ... from exc` 保留因果链
- [ ] 用 `logging` 而非 `print`；格式含时间/级别/logger 名；第三方库降噪（如 httpx → WARNING）

## 6. CI 与 Docker

**检查清单**

- [ ] CI 最小集：`uv sync` → `ruff format --check` + `ruff check` → `pytest`（缺一不可）
- [ ] Dockerfile：基础镜像 tag 尽量固定（最好 digest）、多阶段/层缓存优化、非 root 用户运行、`.dockerignore` 排除 `.venv/.git/测试/密钥`
- [ ] 健康检查端点供编排层探活；容器内配置同样走环境变量

## 7. 版本与发布

**检查清单**

- [ ] 语义化版本（`__version__` 与 pyproject 一致）
- [ ] README 含：快速开始、命令表、架构图、扩展指南、路线图
- [ ] 变更可见：PR/commit 粒度清晰，避免"一把梭"大提交

## 出处

- PEP 8 / PEP 484 / PEP 621 / PEP 735：<https://peps.python.org/>
- uv 文档：<https://docs.astral.sh/uv/>
- ruff 配置：<https://docs.astral.sh/ruff/configuration/>
- 12-Factor Config：<https://12factor.net/zh_cn/config>
- Trail of Bits modern-python skill：<https://github.com/trailofbits/skills>
