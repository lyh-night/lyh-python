FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# 国内网络构建时可覆盖：--build-arg UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple
ARG UV_DEFAULT_INDEX=https://pypi.org/simple
ENV UV_DEFAULT_INDEX=${UV_DEFAULT_INDEX} \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# 先只拷贝清单以利用层缓存，再拷贝源码
COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --frozen --no-dev

# 非 root 运行
RUN useradd --create-home --shell /usr/sbin/nologin appuser
USER appuser

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)" || exit 1

CMD ["uvicorn", "agent_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
