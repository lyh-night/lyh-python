"""LLM 模型构建：DeepSeek 走 OpenAI 兼容协议（langchain-openai）。"""

from functools import lru_cache

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from agent_service.core.config import Settings, get_settings
from agent_service.core.errors import LLMNotConfiguredError


def build_chat_model(settings: Settings) -> ChatOpenAI:
    """按配置构建指向 DeepSeek 的 ChatOpenAI，未配置密钥时抛 LLMNotConfiguredError。"""
    if not settings.deepseek_api_key:
        raise LLMNotConfiguredError(
            "未配置 DEEPSEEK_API_KEY：请复制 .env.example 为 .env 并填写密钥后重启服务"
        )
    return ChatOpenAI(
        model=settings.deepseek_model,
        api_key=SecretStr(settings.deepseek_api_key),
        base_url=settings.deepseek_base_url,
        temperature=settings.llm_temperature,
        timeout=settings.llm_timeout_seconds,
        max_retries=2,
    )


@lru_cache
def get_chat_model() -> ChatOpenAI:
    """返回全局 ChatModel 单例（进程生命周期内复用连接池）。"""
    return build_chat_model(get_settings())
