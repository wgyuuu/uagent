"""
Base LLM Provider

LLM提供商抽象基类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from langchain.llms.base import BaseLLM
from langchain.schema import BaseMessage
import structlog

logger = structlog.get_logger(__name__)

class BaseLLMProvider(ABC):
    """LLM提供商抽象基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get("base_url")
        self.api_key = config.get("api_key")
        
    @abstractmethod
    def get_langchain_llm(self, model_name: str, params: Dict[str, Any]) -> BaseLLM:
        """获取LangChain兼容的LLM实例"""
        pass
    
    def get_provider_info(self) -> Dict[str, Any]:
        """获取提供商信息"""
        return {
            "base_url": self.base_url,
            "has_api_key": bool(self.api_key)
        }
