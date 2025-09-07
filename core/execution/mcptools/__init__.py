"""
UAgent MCPTools Package

mcptools包 - 统一管理所有工具相关功能
"""

from .manager import ToolManager

# 全局实例
_tool_manager = None

def get_tool_manager() -> ToolManager:
    """获取工具管理器实例"""
    global _tool_manager
    if _tool_manager is None:
        raise RuntimeError("mcptools包尚未初始化，请先调用 mcptools.init()")
    return _tool_manager

async def init(config_file_path: str = None):
    """
    初始化mcptools包
    
    Args:
        config_file_path: MCP配置文件路径，可选
    """
    global _tool_manager
    
    # 创建工具注册表（传入配置文件路径）
    from tools.mcp import MCPToolRegistry
    tool_registry = MCPToolRegistry(config_file_path)
    tool_registry.initialize()
    
    # 初始化工具管理器（传入工具注册表）
    _tool_manager = ToolManager(tool_registry)
    
    print("mcptools包初始化完成")

__all__ = [
    "ToolManager",
    "init",
    "get_tool_manager",
]
