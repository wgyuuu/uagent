"""
LLM Configuration Models

LLM配置相关的数据模型定义
"""

from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional, List
from enum import Enum
import os
import structlog

logger = structlog.get_logger(__name__)

class ModelType(str, Enum):
    """模型类型枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    AZURE = "azure"
    GOOGLE = "google"

class ProviderConfig(BaseModel):
    """提供商配置"""
    base_url: str = Field(..., description="基础URL")
    api_key_env: str = Field(..., description="API密钥环境变量名")
    models: List[str] = Field(..., description="模型名称列表")
    
    @field_validator('api_key_env')
    @classmethod
    def validate_api_key_env(cls, v):
        # 只验证环境变量格式，不强制要求必须设置
        # 实际使用时再检查
        return v
    
    def get_api_key(self) -> str:
        """获取API密钥"""
        return os.getenv(self.api_key_env)

class SceneConfig(BaseModel):
    """场景配置"""
    model_name: str = Field(..., description="模型名称")
    params: Dict[str, Any] = Field(default_factory=dict, description="模型参数")
    
    # 场景元数据
    description: str = Field(default="", description="场景描述")
    priority: int = Field(default=1, description="优先级")
    is_active: bool = Field(default=True, description="是否激活")

class LLMConfig(BaseModel):
    """LLM配置总模型"""
    models: Dict[ModelType, ProviderConfig] = Field(..., description="模型提供商配置")
    scenes: Dict[str, SceneConfig] = Field(..., description="场景配置")
    
    @field_validator('scenes')
    @classmethod
    def validate_scenes(cls, v, info):
        """验证场景配置的有效性"""
        if 'models' not in info.data:
            return v
        
        # 构建所有可用模型的映射
        available_models = {}
        for provider_type, provider_config in info.data['models'].items():
            for model_name in provider_config.models:
                available_models[model_name] = provider_type
        
        # 验证场景配置的模型是否存在
        for scene_name, scene_config in v.items():
            if scene_config.model_name not in available_models:
                logger.warning(f"场景 {scene_name} 引用了不存在的模型: {scene_config.model_name}，将在运行时验证")
        
        return v
    
    def get_model_provider(self, model_name: str) -> Optional[ModelType]:
        """根据模型名称获取提供商类型"""
        for provider_type, provider_config in self.models.items():
            if model_name in provider_config.models:
                return provider_type
        return None
