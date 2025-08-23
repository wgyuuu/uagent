"""
System Information Tools

系统信息工具 - 提供系统信息获取和监控功能
"""

from typing import Dict, Any
from .base_tool import BaseTool, ToolSchema


class SystemInfoTool(BaseTool):
    """系统信息工具"""
    
    def get_tool_id(self) -> str:
        return "system_info"
    
    def get_name(self) -> str:
        return "系统信息"
    
    def get_description(self) -> str:
        return "获取系统信息"
    
    def get_category(self) -> str:
        return "system"
    
    def get_tags(self) -> list:
        return ["system", "info", "monitoring"]
    
    def get_metadata(self) -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "author": "uagent",
            "supports_async": True,
            "supported_platforms": ["linux", "darwin", "windows"],
            "requires_psutil": True
        }
    
    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            input_schema={
                "type": "object",
                "properties": {
                    "info_type": {"type": "string", "default": "all", "description": "信息类型"}
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "platform": {"type": "object", "description": "平台信息"},
                    "python_version": {"type": "string", "description": "Python版本"},
                    "memory_usage": {"type": "object", "description": "内存使用情况"},
                    "cpu_info": {"type": "object", "description": "CPU信息"}
                }
            }
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行系统信息获取"""
        info_type = kwargs.get("info_type", "all")
        
        info = {}
        
        try:
            import platform
            import psutil
        except ImportError as e:
            raise RuntimeError(f"缺少必要的依赖: {e}")
        
        if info_type in ["all", "platform"]:
            info["platform"] = {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor()
            }
        
        if info_type in ["all", "python"]:
            info["python_version"] = platform.python_version()
        
        if info_type in ["all", "memory"]:
            try:
                memory = psutil.virtual_memory()
                info["memory_usage"] = {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                }
            except Exception as e:
                info["memory_usage"] = {"error": str(e)}
        
        if info_type in ["all", "cpu"]:
            try:
                info["cpu_info"] = {
                    "count": psutil.cpu_count(),
                    "percent": psutil.cpu_percent(interval=1),
                    "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
                }
            except Exception as e:
                info["cpu_info"] = {"error": str(e)}
        
        return info
