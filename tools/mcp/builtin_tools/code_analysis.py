"""
Code Analysis Tools

代码分析工具 - 提供代码结构和复杂度分析功能
"""

from typing import Dict, Any
from .base_tool import BaseTool, ToolSchema


class CodeAnalyzeTool(BaseTool):
    """代码分析工具"""
    
    def get_tool_id(self) -> str:
        return "code_analyze"
    
    def get_name(self) -> str:
        return "代码分析"
    
    def get_description(self) -> str:
        return "分析代码结构和复杂度"
    
    def get_category(self) -> str:
        return "code_analysis"
    
    def get_tags(self) -> list:
        return ["code", "analysis", "complexity"]
    
    def get_metadata(self) -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "author": "uagent",
            "supports_async": True,
            "supported_languages": ["python", "javascript", "java", "cpp"]
        }
    
    def get_schema(self) -> ToolSchema:
        return ToolSchema(
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
            }
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行代码分析"""
        self.validate_input(kwargs)
        
        code = kwargs["code"]
        language = kwargs.get("language", "python")
        analysis_type = kwargs.get("analysis_type", "basic")
        
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
        elif language == "javascript":
            return code.count('function ') + code.count('=>')
        elif language == "java":
            return code.count('public ') + code.count('private ') + code.count('protected ')
        elif language == "cpp":
            return code.count('void ') + code.count('int ') + code.count('string ')
        return 0
    
    def _count_classes(self, code: str, language: str) -> int:
        """统计类数量"""
        if language == "python":
            return code.count('class ')
        elif language == "javascript":
            return code.count('class ')
        elif language == "java":
            return code.count('class ') + code.count('interface ')
        elif language == "cpp":
            return code.count('class ') + code.count('struct ')
        return 0
    
    def _count_imports(self, code: str, language: str) -> int:
        """统计导入数量"""
        if language == "python":
            return code.count('import ') + code.count('from ')
        elif language == "javascript":
            return code.count('import ') + code.count('require(')
        elif language == "java":
            return code.count('import ')
        elif language == "cpp":
            return code.count('#include ')
        return 0
