"""统一日志配置。"""

import logging

from agent_service.core.config import Settings


def setup_logging(settings: Settings) -> None:
    """按配置初始化根日志。"""
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    # 降低第三方库噪音
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
