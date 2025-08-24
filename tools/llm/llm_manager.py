"""
LLM Manager

LLM管理器 - 统一管理所有LLM提供商和模型
"""

from typing import Dict, Any, Optional, List
import yaml
import structlog
from pathlib import Path
from langchain.llms.base import BaseLLM

from .models.llm_config import LLMConfig, ModelType, SceneConfig
from .providers.base import BaseLLMProvider
from .providers.openai_provider import OpenAIProvider
from .providers.anthropic_provider import AnthropicProvider
from .llm_logging_wrapper import LLMLoggingWrapper

logger = structlog.get_logger(__name__)

class LLMManager:
    """LLM管理器 - 统一管理所有LLM提供商和模型"""
    
    def __init__(self, config_path: str = "config/llm_models.yaml"):
        self.config_path = Path(config_path)
        self.config: Optional[LLMConfig] = None
        self.providers: Dict[ModelType, BaseLLMProvider] = {}
        self.scene_configs: Dict[str, SceneConfig] = {}
        
        # 性能统计
        self.performance_stats: Dict[str, Dict[str, Any]] = {}
        
        # 初始化
        self._load_config()
        self._initialize_providers()
        self._initialize_scenes()
        
        logger.info("LLM管理器初始化完成")
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            self.config = LLMConfig(**config_data)
            logger.info(f"成功加载LLM配置: {len(self.config.models)} 个提供商, {len(self.config.scenes)} 个场景")
            
        except Exception as e:
            logger.error(f"加载LLM配置失败: {e}")
            raise
    
    def _initialize_providers(self):
        """初始化提供商"""
        try:
            for model_type, provider_config in self.config.models.items():
                # 检查环境变量是否设置
                try:
                    api_key = provider_config.api_key
                    if not api_key:
                        logger.warning(f"跳过提供商 {model_type}，API密钥未设置")
                        continue
                except Exception as e:
                    logger.warning(f"跳过提供商 {model_type}，获取API密钥失败: {e}")
                    continue
                
                if model_type == ModelType.OPENAI:
                    provider = OpenAIProvider({
                        "base_url": provider_config.base_url,
                        "api_key": api_key
                    })
                elif model_type == ModelType.ANTHROPIC:
                    provider = AnthropicProvider({
                        "base_url": provider_config.base_url,
                        "api_key": api_key
                    })
                else:
                    logger.warning(f"暂不支持的模型类型: {model_type}")
                    continue
                
                self.providers[model_type] = provider
                logger.info(f"初始化提供商: {model_type}")
                
        except Exception as e:
            logger.error(f"初始化提供商失败: {e}")
            raise
    
    def _initialize_scenes(self):
        """初始化场景配置"""
        self.scene_configs = self.config.scenes
        logger.info(f"初始化场景配置: {list(self.scene_configs.keys())}")
    
    def get_llm_for_scene(self, scene_key: str) -> BaseLLM:
        """根据场景key获取LLM实例"""
        if scene_key not in self.scene_configs:
            raise ValueError(f"未找到场景配置: {scene_key}")
        
        scene_config = self.scene_configs[scene_key]
        model_name = scene_config.model_name
        
        # 根据模型名称找到对应的提供商类型
        provider_type = self.config.get_model_provider(model_name)
        if not provider_type:
            raise ValueError(f"未找到模型 {model_name} 对应的提供商, 场景: {scene_key}")
        
        if provider_type not in self.providers:
            raise ValueError(f"未找到提供商: {provider_type}, 模型: {model_name}")
        
        # 获取提供商并创建LLM实例
        provider = self.providers[provider_type]
        llm = provider.get_langchain_llm(model_name, scene_config.params)
        
        # 创建模型信息字典
        model_info = {
            "scene_key": scene_key,
            "model_name": model_name,
            "provider_type": provider_type,
            "parameters": scene_config.params,
            "provider_info": provider.get_provider_info()
        }
        
        # 使用日志包装器包装LLM实例
        wrapped_llm = LLMLoggingWrapper(llm, model_info)
        
        logger.info(f"为场景 {scene_key} 创建带日志的LLM: {provider_type}/{model_name}")
        return wrapped_llm
    
    def get_scene_config(self, scene_key: str) -> Optional[SceneConfig]:
        """获取场景配置"""
        return self.scene_configs.get(scene_key)
    
    def get_available_scenes(self) -> List[str]:
        """获取可用场景列表"""
        return list(self.scene_configs.keys())
    
    def get_model_info(self, scene_key: str) -> Dict[str, Any]:
        """获取场景对应的模型信息"""
        if scene_key not in self.scene_configs:
            return {}
        
        scene_config = self.scene_configs[scene_key]
        model_name = scene_config.model_name
        provider_type = self.config.get_model_provider(model_name)
        
        if not provider_type or provider_type not in self.providers:
            return {}
        
        return {
            "scene": scene_key,
            "model_name": model_name,
            "provider_type": provider_type,
            "params": scene_config.params,
            "provider_info": self.providers[provider_type].get_provider_info()
        }
    
    def update_scene_config(self, scene_key: str, new_config: SceneConfig):
        """更新场景配置"""
        self.scene_configs[scene_key] = new_config
        logger.info(f"更新场景配置: {scene_key}")
    
    def reload_config(self):
        """重新加载配置"""
        logger.info("重新加载LLM配置")
        self._load_config()
        self._initialize_providers()
        self._initialize_scenes()
    
    def get_performance_stats(self, scene_key: str = None) -> Dict[str, Any]:
        """获取性能统计"""
        if scene_key:
            return self.performance_stats.get(scene_key, {})
        return self.performance_stats
    
    def record_performance(self, scene_key: str, metrics: Dict[str, Any]):
        """记录性能指标"""
        if scene_key not in self.performance_stats:
            self.performance_stats[scene_key] = {}
        
        self.performance_stats[scene_key].update(metrics)
