"""
LLM Package

LLM管理系统包
"""

from .llm_manager import LLMManager

# 全局LLM管理器实例
_llm_manager: LLMManager = None

def initialize_llm_manager(config_path: str = "config/llm_models.yaml"):
    """
    初始化全局LLM管理器
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        LLMManager: 初始化后的LLM管理器实例
    """
    global _llm_manager
    _llm_manager = LLMManager(config_path)

def get_llm_manager() -> LLMManager:
    """
    获取全局LLM管理器实例
    
    Returns:
        LLMManager: 全局LLM管理器实例
        
    Raises:
        RuntimeError: 如果LLM管理器未初始化
    """
    if _llm_manager is None:
        raise RuntimeError("LLM管理器未初始化，请先调用 initialize_llm_manager()")
    return _llm_manager

def get_llm_for_scene(scene_key: str):
    """
    根据场景key获取LLM实例
    
    Args:
        scene_key: 场景key
        
    Returns:
        BaseLLM: 对应场景的LLM实例
    """
    return get_llm_manager().get_llm_for_scene(scene_key)

def get_scene_config(scene_key: str):
    """
    获取场景配置
    
    Args:
        scene_key: 场景key
        
    Returns:
        SceneConfig: 场景配置
    """
    return get_llm_manager().get_scene_config(scene_key)

def get_available_scenes():
    """
    获取可用场景列表
    
    Returns:
        List[str]: 可用场景列表
    """
    return get_llm_manager().get_available_scenes()

def reload_config():
    """
    重新加载配置
    """
    if _llm_manager:
        _llm_manager.reload_config()

__all__ = [
    "LLMManager",
    "initialize_llm_manager",
    "get_llm_manager", 
    "get_llm_for_scene",
    "get_scene_config",
    "get_available_scenes",
    "reload_config"
]
