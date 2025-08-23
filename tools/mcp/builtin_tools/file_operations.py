"""
File Operations Tools

文件操作工具 - 提供文件读取和写入功能
"""

from typing import Dict, Any
from .base_tool import BaseTool, ToolSchema


class FileReadTool(BaseTool):
    """文件读取工具"""
    
    def get_tool_id(self) -> str:
        return "file_read"
    
    def get_name(self) -> str:
        return "文件读取"
    
    def get_description(self) -> str:
        return "读取文件内容"
    
    def get_category(self) -> str:
        return "file_operations"
    
    def get_tags(self) -> list:
        return ["file", "read", "io"]
    
    def get_metadata(self) -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "author": "uagent",
            "supports_async": True
        }
    
    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "文件路径"},
                    "encoding": {"type": "string", "default": "utf-8", "description": "文件编码"}
                },
                "required": ["file_path"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "文件内容"},
                    "size": {"type": "integer", "description": "文件大小"},
                    "encoding": {"type": "string", "description": "使用的编码"}
                }
            }
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行文件读取"""
        self.validate_input(kwargs)
        
        file_path = kwargs["file_path"]
        encoding = kwargs.get("encoding", "utf-8")
        
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            return {
                "content": content,
                "size": len(content.encode(encoding)),
                "encoding": encoding
            }
        except Exception as e:
            raise RuntimeError(f"读取文件失败: {e}")


class FileWriteTool(BaseTool):
    """文件写入工具"""
    
    def get_tool_id(self) -> str:
        return "file_write"
    
    def get_name(self) -> str:
        return "文件写入"
    
    def get_description(self) -> str:
        return "写入内容到文件"
    
    def get_category(self) -> str:
        return "file_operations"
    
    def get_tags(self) -> list:
        return ["file", "write", "io"]
    
    def get_metadata(self) -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "author": "uagent",
            "supports_async": True
        }
    
    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "要写入的内容"},
                    "encoding": {"type": "string", "default": "utf-8", "description": "文件编码"},
                    "mode": {"type": "string", "default": "w", "description": "写入模式"}
                },
                "required": ["file_path", "content"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "description": "是否成功"},
                    "bytes_written": {"type": "integer", "description": "写入的字节数"},
                    "file_path": {"type": "string", "description": "文件路径"}
                }
            }
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行文件写入"""
        self.validate_input(kwargs)
        
        file_path = kwargs["file_path"]
        content = kwargs["content"]
        encoding = kwargs.get("encoding", "utf-8")
        mode = kwargs.get("mode", "w")
        
        try:
            with open(file_path, mode, encoding=encoding) as f:
                bytes_written = f.write(content)
            
            return {
                "success": True,
                "bytes_written": bytes_written,
                "file_path": file_path
            }
        except Exception as e:
            raise RuntimeError(f"写入文件失败: {e}")
