"""测试桩：脚本化假模型（支持 bind_tools，供 LangGraph 循环测试）。"""

from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class ScriptedChatModel(BaseChatModel):
    """按脚本顺序依次返回预设消息的假模型，可循环复用最后一条。

    注意：每次响应都会生成全新 id（模拟真实模型行为）。若复用同一消息对象，
    LangGraph 的 add_messages reducer 会按消息 id 去重替换，导致循环提前终止。
    """

    responses: list[BaseMessage]
    step: int = 0

    @property
    def _llm_type(self) -> str:
        return "scripted-chat-model"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ScriptedChatModel":
        """假装绑定工具，直接返回自身。"""
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """按脚本顺序产出消息；脚本耗尽后重复最后一条，id 每次唯一。"""
        index = min(self.step, len(self.responses) - 1)
        self.step += 1
        message = self.responses[index].model_copy(deep=True)
        message.id = f"scripted-{self.step}"
        return ChatResult(generations=[ChatGeneration(message=message)])
