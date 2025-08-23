"""
Anthropic LLM Provider

Anthropic LLM提供商实现
"""

from typing import Dict, Any
from langchain_anthropic import ChatAnthropic
from langchain.llms.base import BaseLLM
from .base import BaseLLMProvider
import structlog

logger = structlog.get_logger(__name__)

class AnthropicProvider(BaseLLMProvider):
    """Anthropic LLM提供商"""
    
    def get_langchain_llm(self, model_name: str, params: Dict[str, Any]) -> BaseLLM:
        """获取LangChain兼容的LLM实例"""
        return ChatAnthropic(
            api_key=self.api_key,
            base_url=self.base_url,
            model=model_name,
            temperature=params.get("temperature", 0.7),
            max_tokens=params.get("max_tokens", 4096),
            top_p=params.get("top_p", 1.0),
            timeout=params.get("timeout", 30),
            max_retries=params.get("max_retries", 3)
        )
