"""
Text Processing Tools

文本处理工具 - 提供文本摘要和文本分析功能
"""

from typing import Dict, Any
from .base_tool import BaseTool, ToolSchema


class TextSummarizeTool(BaseTool):
    """文本摘要工具"""
    
    def get_tool_id(self) -> str:
        return "text_summarize"
    
    def get_name(self) -> str:
        return "文本摘要"
    
    def get_description(self) -> str:
        return "生成文本摘要"
    
    def get_category(self) -> str:
        return "text_processing"
    
    def get_tags(self) -> list:
        return ["text", "summary", "nlp"]
    
    def get_metadata(self) -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "author": "uagent",
            "supports_async": True,
            "supported_languages": ["chinese", "english"],
            "max_input_length": 100000
        }
    
    def get_schema(self) -> ToolSchema:
        return ToolSchema(
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
            }
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行文本摘要"""
        self.validate_input(kwargs)
        
        text = kwargs["text"]
        max_length = kwargs.get("max_length", 200)
        style = kwargs.get("style", "concise")
        
        original_length = len(text)
        
        if original_length <= max_length:
            summary = text
        else:
            # 根据风格选择摘要策略
            if style == "concise":
                summary = self._generate_concise_summary(text, max_length)
            elif style == "detailed":
                summary = self._generate_detailed_summary(text, max_length)
            else:
                summary = self._generate_concise_summary(text, max_length)
        
        return {
            "summary": summary,
            "original_length": original_length,
            "summary_length": len(summary),
            "compression_ratio": len(summary) / original_length
        }
    
    def _generate_concise_summary(self, text: str, max_length: int) -> str:
        """生成简洁摘要"""
        # 简单的摘要算法：取前N个字符，在句子边界截断
        summary = text[:max_length]
        last_period = summary.rfind('.')
        if last_period > max_length * 0.8:  # 如果句号在合理位置
            summary = summary[:last_period + 1]
        else:
            summary = summary.rstrip() + "..."
        return summary
    
    def _generate_detailed_summary(self, text: str, max_length: int) -> str:
        """生成详细摘要"""
        # 尝试保留更多内容，在段落边界截断
        summary = text[:max_length]
        last_newline = summary.rfind('\n')
        if last_newline > max_length * 0.7:  # 如果在合理位置有换行
            summary = summary[:last_newline]
        else:
            summary = summary.rstrip() + "..."
        return summary
