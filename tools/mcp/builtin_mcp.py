"""
Built-in MCP Server Manager

内置MCP服务器管理器 - 管理直接实现的函数调用MCP服务
"""

from typing import Dict, List, Any, Optional, Callable, Union
import structlog
import asyncio
import inspect
import json
from datetime import datetime
from dataclasses import dataclass, asdict
import traceback

from ...models.base import MCPToolDefinition, ToolExecutionResult

logger = structlog.get_logger(__name__)


@dataclass
class BuiltInTool:
    """内置工具定义"""
    tool_id: str
    name: str
    description: str
    function: Callable
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    category: str
    tags: List[str]
    metadata: Dict[str, Any]


class BuiltInMCPServerManager:
    """
    内置MCP服务器管理器
    
    管理直接实现的函数调用MCP服务，提供常用功能的本地实现
    """
    
    def __init__(self):
        self.tools: Dict[str, BuiltInTool] = {}
        self.categories: Dict[str, List[str]] = {}
        self.execution_stats: Dict[str, Dict[str, Any]] = {}
        
        # 注册默认工具
        self._register_default_tools()
        
        logger.info("内置MCP服务器管理器初始化完成")
    
    def _register_default_tools(self):
        """注册默认内置工具"""
        # 文件操作工具
        self.register_tool(
            tool_id="file_read",
            name="文件读取",
            description="读取文件内容",
            function=self._file_read,
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
            },
            category="file_operations",
            tags=["file", "read", "io"]
        )
        
        self.register_tool(
            tool_id="file_write",
            name="文件写入",
            description="写入内容到文件",
            function=self._file_write,
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
            },
            category="file_operations",
            tags=["file", "write", "io"]
        )
        
        # 代码分析工具
        self.register_tool(
            tool_id="code_analyze",
            name="代码分析",
            description="分析代码结构和复杂度",
            function=self._code_analyze,
            input_schema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "要分析的代码"},
                    "language": {"type": "string", "default": "python", "description": "编程语言"},
                    "analysis_type": {"type": "string", "default": "basic", "description": "分析类型"}
                },
                "required": ["code"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "lines_of_code": {"type": "integer", "description": "代码行数"},
                    "complexity": {"type": "object", "description": "复杂度分析"},
                    "structure": {"type": "object", "description": "结构分析"},
                    "suggestions": {"type": "array", "description": "改进建议"}
                }
            },
            category="code_analysis",
            tags=["code", "analysis", "complexity"]
        )
        
        # 文本处理工具
        self.register_tool(
            tool_id="text_summarize",
            name="文本摘要",
            description="生成文本摘要",
            function=self._text_summarize,
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "要摘要的文本"},
                    "max_length": {"type": "integer", "default": 200, "description": "最大摘要长度"},
                    "style": {"type": "string", "default": "concise", "description": "摘要风格"}
                },
                "required": ["text"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "生成的摘要"},
                    "original_length": {"type": "integer", "description": "原文长度"},
                    "summary_length": {"type": "integer", "description": "摘要长度"},
                    "compression_ratio": {"type": "number", "description": "压缩比"}
                }
            },
            category="text_processing",
            tags=["text", "summary", "nlp"]
        )
        
        # 系统信息工具
        self.register_tool(
            tool_id="system_info",
            name="系统信息",
            description="获取系统信息",
            function=self._system_info,
            input_schema={
                "type": "object",
                "properties": {
                    "info_type": {"type": "string", "default": "all", "description": "信息类型"}
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "platform": {"type": "string", "description": "平台信息"},
                    "python_version": {"type": "string", "description": "Python版本"},
                    "memory_usage": {"type": "object", "description": "内存使用情况"},
                    "cpu_info": {"type": "object", "description": "CPU信息"}
                }
            },
            category="system",
            tags=["system", "info", "monitoring"]
        )
        
        # 数据验证工具
        self.register_tool(
            tool_id="data_validate",
            name="数据验证",
            description="验证数据格式和内容",
            function=self._data_validate,
            input_schema={
                "type": "object",
                "properties": {
                    "data": {"description": "要验证的数据"},
                    "schema": {"type": "object", "description": "验证模式"},
                    "strict": {"type": "boolean", "default": False, "description": "是否严格验证"}
                },
                "required": ["data", "schema"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "is_valid": {"type": "boolean", "description": "是否有效"},
                    "errors": {"type": "array", "description": "错误列表"},
                    "warnings": {"type": "array", "description": "警告列表"}
                }
            },
            category="data_validation",
            tags=["validation", "schema", "data"]
        )
    
    def register_tool(
        self,
        tool_id: str,
        name: str,
        description: str,
        function: Callable,
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
        category: str,
        tags: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """注册内置工具"""
        try:
            # 验证函数签名
            if not callable(function):
                raise ValueError("function必须是可调用对象")
            
            # 创建工具定义
            tool = BuiltInTool(
                tool_id=tool_id,
                name=name,
                description=description,
                function=function,
                input_schema=input_schema,
                output_schema=output_schema,
                category=category,
                tags=tags,
                metadata=metadata or {}
            )
            
            # 注册工具
            self.tools[tool_id] = tool
            
            # 更新分类
            if category not in self.categories:
                self.categories[category] = []
            self.categories[category].append(tool_id)
            
            # 初始化执行统计
            self.execution_stats[tool_id] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_execution_time": 0.0,
                "last_called": None,
                "error_history": []
            }
            
            logger.info(f"内置工具已注册: {name} ({tool_id})")
            
        except Exception as e:
            logger.error(f"注册内置工具失败: {e}")
            raise
    
    def unregister_tool(self, tool_id: str):
        """注销内置工具"""
        try:
            if tool_id not in self.tools:
                logger.warning(f"工具 {tool_id} 不存在")
                return
            
            tool = self.tools[tool_id]
            
            # 从分类中移除
            if tool.category in self.categories:
                self.categories[tool.category].remove(tool_id)
                if not self.categories[tool.category]:
                    del self.categories[tool.category]
            
            # 移除工具和统计
            del self.tools[tool_id]
            if tool_id in self.execution_stats:
                del self.execution_stats[tool_id]
            
            logger.info(f"内置工具已注销: {tool_id}")
            
        except Exception as e:
            logger.error(f"注销内置工具失败: {e}")
            raise
    
    async def execute_tool(
        self,
        tool_id: str,
        input_data: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> ToolExecutionResult:
        """
        执行内置工具
        
        Args:
            tool_id: 工具ID
            input_data: 输入数据
            timeout: 超时时间
            
        Returns:
            工具执行结果
        """
        try:
            if tool_id not in self.tools:
                raise ValueError(f"工具 {tool_id} 不存在")
            
            tool = self.tools[tool_id]
            
            # 更新执行统计
            self.execution_stats[tool_id]["total_calls"] += 1
            self.execution_stats[tool_id]["last_called"] = datetime.now().isoformat()
            
            # 验证输入数据
            await self._validate_input(input_data, tool.input_schema)
            
            # 执行工具
            start_time = datetime.now()
            
            if asyncio.iscoroutinefunction(tool.function):
                result = await tool.function(**input_data)
            else:
                # 如果是同步函数，在线程池中执行
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, tool.function, **input_data)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 更新成功统计
            self.execution_stats[tool_id]["successful_calls"] += 1
            self.execution_stats[tool_id]["total_execution_time"] += execution_time
            
            # 构建结果
            tool_result = ToolExecutionResult(
                tool_id=tool_id,
                success=True,
                output=result,
                execution_time=execution_time,
                metadata={
                    "category": tool.category,
                    "tags": tool.tags,
                    "input_schema": tool.input_schema,
                    "output_schema": tool.output_schema
                }
            )
            
            logger.info(f"内置工具 {tool_id} 执行成功，耗时: {execution_time:.3f}s")
            return tool_result
            
        except Exception as e:
            # 更新失败统计
            if tool_id in self.execution_stats:
                self.execution_stats[tool_id]["failed_calls"] += 1
                self.execution_stats[tool_id]["error_history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                
                # 保持错误历史在合理范围内
                if len(self.execution_stats[tool_id]["error_history"]) > 10:
                    self.execution_stats[tool_id]["error_history"] = \
                        self.execution_stats[tool_id]["error_history"][-10:]
            
            logger.error(f"内置工具 {tool_id} 执行失败: {e}")
            
            # 构建错误结果
            error_result = ToolExecutionResult(
                tool_id=tool_id,
                success=False,
                error=str(e),
                execution_time=0,
                metadata={
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc()
                }
            )
            
            return error_result
    
    async def _validate_input(self, input_data: Dict[str, Any], schema: Dict[str, Any]):
        """验证输入数据"""
        # 这里可以实现更复杂的JSON Schema验证
        # 目前只做基本的类型检查
        if not isinstance(input_data, dict):
            raise ValueError("输入数据必须是字典")
        
        # 检查必需字段
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in input_data:
                raise ValueError(f"缺少必需字段: {field}")
    
    # 默认工具实现
    
    async def _file_read(self, file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """文件读取工具"""
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
    
    async def _file_write(self, file_path: str, content: str, encoding: str = "utf-8", mode: str = "w") -> Dict[str, Any]:
        """文件写入工具"""
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
    
    async def _code_analyze(self, code: str, language: str = "python", analysis_type: str = "basic") -> Dict[str, Any]:
        """代码分析工具"""
        lines = code.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        # 基本分析
        analysis = {
            "lines_of_code": len(lines),
            "non_empty_lines": len(non_empty_lines),
            "complexity": {
                "cyclomatic_complexity": self._calculate_cyclomatic_complexity(code),
                "nesting_depth": self._calculate_nesting_depth(code)
            },
            "structure": {
                "functions": self._count_functions(code, language),
                "classes": self._count_classes(code, language),
                "imports": self._count_imports(code, language)
            },
            "suggestions": []
        }
        
        # 生成建议
        if analysis["complexity"]["cyclomatic_complexity"] > 10:
            analysis["suggestions"].append("代码复杂度较高，建议重构")
        
        if analysis["complexity"]["nesting_depth"] > 4:
            analysis["suggestions"].append("嵌套层次过深，建议优化")
        
        return analysis
    
    def _calculate_cyclomatic_complexity(self, code: str) -> int:
        """计算圈复杂度"""
        complexity = 1  # 基础复杂度
        
        # 统计控制流语句
        control_keywords = ['if', 'elif', 'else', 'for', 'while', 'except', 'and', 'or']
        for keyword in control_keywords:
            complexity += code.count(f' {keyword} ')
        
        return complexity
    
    def _calculate_nesting_depth(self, code: str) -> int:
        """计算嵌套深度"""
        max_depth = 0
        current_depth = 0
        
        for char in code:
            if char in '([{':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char in ')]}':
                current_depth = max(0, current_depth - 1)
        
        return max_depth
    
    def _count_functions(self, code: str, language: str) -> int:
        """统计函数数量"""
        if language == "python":
            return code.count('def ')
        return 0
    
    def _count_classes(self, code: str, language: str) -> int:
        """统计类数量"""
        if language == "python":
            return code.count('class ')
        return 0
    
    def _count_imports(self, code: str, language: str) -> int:
        """统计导入数量"""
        if language == "python":
            return code.count('import ') + code.count('from ')
        return 0
    
    async def _text_summarize(self, text: str, max_length: int = 200, style: str = "concise") -> Dict[str, Any]:
        """文本摘要工具"""
        original_length = len(text)
        
        if original_length <= max_length:
            summary = text
        else:
            # 简单的摘要算法：取前N个字符，在句子边界截断
            summary = text[:max_length]
            last_period = summary.rfind('.')
            if last_period > max_length * 0.8:  # 如果句号在合理位置
                summary = summary[:last_period + 1]
            else:
                summary = summary.rstrip() + "..."
        
        return {
            "summary": summary,
            "original_length": original_length,
            "summary_length": len(summary),
            "compression_ratio": len(summary) / original_length
        }
    
    async def _system_info(self, info_type: str = "all") -> Dict[str, Any]:
        """系统信息工具"""
        import platform
        import psutil
        
        info = {}
        
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
            memory = psutil.virtual_memory()
            info["memory_usage"] = {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used
            }
        
        if info_type in ["all", "cpu"]:
            info["cpu_info"] = {
                "count": psutil.cpu_count(),
                "percent": psutil.cpu_percent(interval=1),
                "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            }
        
        return info
    
    async def _data_validate(self, data: Any, schema: Dict[str, Any], strict: bool = False) -> Dict[str, Any]:
        """数据验证工具"""
        errors = []
        warnings = []
        
        try:
            # 这里可以实现更复杂的验证逻辑
            # 目前只做基本的类型检查
            if "type" in schema:
                expected_type = schema["type"]
                if expected_type == "string" and not isinstance(data, str):
                    errors.append(f"期望字符串类型，实际类型: {type(data).__name__}")
                elif expected_type == "integer" and not isinstance(data, int):
                    errors.append(f"期望整数类型，实际类型: {type(data).__name__}")
                elif expected_type == "object" and not isinstance(data, dict):
                    errors.append(f"期望对象类型，实际类型: {type(data).__name__}")
                elif expected_type == "array" and not isinstance(data, list):
                    errors.append(f"期望数组类型，实际类型: {type(data).__name__}")
            
            # 检查必需字段
            if isinstance(data, dict) and "required" in schema:
                for field in schema["required"]:
                    if field not in data:
                        errors.append(f"缺少必需字段: {field}")
            
            is_valid = len(errors) == 0
            
            return {
                "is_valid": is_valid,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "is_valid": False,
                "errors": [f"验证过程出错: {str(e)}"],
                "warnings": []
            }
    
    def get_tool_info(self, tool_id: str) -> Optional[BuiltInTool]:
        """获取工具信息"""
        return self.tools.get(tool_id)
    
    def get_all_tools(self) -> List[BuiltInTool]:
        """获取所有工具"""
        return list(self.tools.values())
    
    def get_tools_by_category(self, category: str) -> List[BuiltInTool]:
        """获取指定分类的工具"""
        if category not in self.categories:
            return []
        
        return [self.tools[tool_id] for tool_id in self.categories[category]]
    
    def get_tools_by_tag(self, tag: str) -> List[BuiltInTool]:
        """获取指定标签的工具"""
        return [
            tool for tool in self.tools.values()
            if tag in tool.tags
        ]
    
    def get_categories(self) -> List[str]:
        """获取所有分类"""
        return list(self.categories.keys())
    
    def get_execution_stats(self, tool_id: Optional[str] = None) -> Dict[str, Any]:
        """获取执行统计"""
        if tool_id:
            return self.execution_stats.get(tool_id, {})
        
        return {
            "total_tools": len(self.tools),
            "total_calls": sum(stats["total_calls"] for stats in self.execution_stats.values()),
            "successful_calls": sum(stats["successful_calls"] for stats in self.execution_stats.values()),
            "failed_calls": sum(stats["failed_calls"] for stats in self.execution_stats.values()),
            "tools_stats": self.execution_stats
        }
