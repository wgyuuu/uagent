"""
Context Compressor

8段式上下文压缩器 - 实现Claude Code的智能记忆管理
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)

@dataclass
class CompressionSection:
    """压缩段落"""
    name: str
    content: str
    importance_score: float
    compression_ratio: float
    compressed_content: Optional[str] = None

@dataclass
class CompressionResult:
    """压缩结果"""
    original_size: int
    compressed_size: int
    compression_ratio: float
    sections: List[CompressionSection]
    quality_score: float

class ContextCompressor:
    """8段式上下文压缩器"""
    
    def __init__(self):
        """初始化8段式上下文压缩器"""
        
        # 8段式压缩结构定义
        self.compression_sections = [
            "Primary Request and Intent",
            "Key Technical Concepts", 
            "Files and Code Sections",
            "Errors and fixes",
            "Problem Solving",
            "All user messages",
            "Pending Tasks",
            "Current Work"
        ]
        
        # 压缩策略配置
        self.compression_strategies = {
            "Primary Request and Intent": {
                "preserve_ratio": 0.9,
                "strategy": "preserve_key_requirements"
            },
            "Key Technical Concepts": {
                "preserve_ratio": 0.8,
                "strategy": "summarize_technical_details"
            },
            "Files and Code Sections": {
                "preserve_ratio": 0.7,
                "strategy": "extract_code_snippets"
            },
            "Errors and fixes": {
                "preserve_ratio": 0.6,
                "strategy": "preserve_critical_errors"
            },
            "Problem Solving": {
                "preserve_ratio": 0.7,
                "strategy": "summarize_solutions"
            },
            "All user messages": {
                "preserve_ratio": 0.5,
                "strategy": "extract_key_messages"
            },
            "Pending Tasks": {
                "preserve_ratio": 0.8,
                "strategy": "list_actionable_items"
            },
            "Current Work": {
                "preserve_ratio": 0.9,
                "strategy": "highlight_progress"
            }
        }
    
    async def compress_context(self, context: Dict[str, Any], target_ratio: float = 0.6) -> CompressionResult:
        """压缩上下文内容"""
        
        logger.info(f"开始压缩上下文，目标压缩比例: {target_ratio}")
        
        # 1. 分析上下文结构
        sections = await self._analyze_context_sections(context)
        
        # 2. 计算重要性分数
        sections = await self._calculate_importance_scores(sections)
        
        # 3. 应用压缩策略
        sections = await self._apply_compression_strategies(sections, target_ratio)
        
        # 4. 生成压缩结果
        result = await self._generate_compression_result(sections, context)
        
        logger.info(f"上下文压缩完成，压缩比例: {result.compression_ratio:.2f}")
        return result
    
    async def _analyze_context_sections(self, context: Dict[str, Any]) -> List[CompressionSection]:
        """分析上下文段落"""
        
        sections = []
        
        for section_name in self.compression_sections:
            content = context.get(section_name, "")
            
            if content and content.strip():
                # 计算初始重要性分数
                importance_score = self._calculate_initial_importance(section_name, content)
                
                # 计算压缩比例
                compression_ratio = self.compression_strategies.get(section_name, {}).get("preserve_ratio", 0.7)
                
                section = CompressionSection(
                    name=section_name,
                    content=content,
                    importance_score=importance_score,
                    compression_ratio=compression_ratio
                )
                
                sections.append(section)
        
        return sections
    
    def _calculate_initial_importance(self, section_name: str, content: str) -> float:
        """计算初始重要性分数"""
        
        # 基于段落类型和内容长度计算重要性
        base_scores = {
            "Primary Request and Intent": 0.9,
            "Key Technical Concepts": 0.8,
            "Files and Code Sections": 0.7,
            "Errors and fixes": 0.6,
            "Problem Solving": 0.7,
            "All user messages": 0.5,
            "Pending Tasks": 0.8,
            "Current Work": 0.9
        }
        
        base_score = base_scores.get(section_name, 0.5)
        
        # 基于内容长度调整分数
        content_length = len(content)
        if content_length < 100:
            length_factor = 0.8
        elif content_length < 500:
            length_factor = 1.0
        elif content_length < 1000:
            length_factor = 0.9
        else:
            length_factor = 0.7
        
        return base_score * length_factor
    
    async def _calculate_importance_scores(self, sections: List[CompressionSection]) -> List[CompressionSection]:
        """计算重要性分数"""
        
        for section in sections:
            # 基于内容特征调整重要性
            if section.name == "Primary Request and Intent":
                # 主要请求和意图最重要
                section.importance_score = min(1.0, section.importance_score * 1.2)
            
            elif section.name == "Current Work":
                # 当前工作状态很重要
                section.importance_score = min(1.0, section.importance_score * 1.1)
            
            elif section.name == "Errors and fixes":
                # 错误信息相对次要
                section.importance_score = max(0.3, section.importance_score * 0.8)
            
            elif section.name == "All user messages":
                # 用户消息相对次要
                section.importance_score = max(0.3, section.importance_score * 0.7)
        
        return sections
    
    async def _apply_compression_strategies(self, sections: List[CompressionSection], target_ratio: float) -> List[CompressionSection]:
        """应用压缩策略"""
        
        for section in sections:
            strategy_name = self.compression_strategies.get(section.name, {}).get("strategy", "general_summarization")
            
            # 应用相应的压缩策略
            compressed_content = await self._apply_compression_strategy(
                section.content, 
                strategy_name, 
                section.compression_ratio,
                target_ratio
            )
            
            section.compressed_content = compressed_content
        
        return sections
    
    async def _apply_compression_strategy(self, content: str, strategy: str, preserve_ratio: float, target_ratio: float) -> str:
        """应用具体的压缩策略"""
        
        # 调整压缩比例以适应目标比例
        adjusted_ratio = preserve_ratio * target_ratio
        
        if strategy == "preserve_key_requirements":
            return await self._preserve_key_requirements(content, adjusted_ratio)
        elif strategy == "summarize_technical_details":
            return await self._summarize_technical_details(content, adjusted_ratio)
        elif strategy == "extract_code_snippets":
            return await self._extract_code_snippets(content, adjusted_ratio)
        elif strategy == "preserve_critical_errors":
            return await self._preserve_critical_errors(content, adjusted_ratio)
        elif strategy == "summarize_solutions":
            return await self._summarize_solutions(content, adjusted_ratio)
        elif strategy == "extract_key_messages":
            return await self._extract_key_messages(content, adjusted_ratio)
        elif strategy == "list_actionable_items":
            return await self._list_actionable_items(content, adjusted_ratio)
        elif strategy == "highlight_progress":
            return await self._highlight_progress(content, adjusted_ratio)
        else:
            return await self._general_summarization(content, adjusted_ratio)
    
    async def _preserve_key_requirements(self, content: str, ratio: float) -> str:
        """保留关键需求"""
        # 提取关键词汇和短语
        key_phrases = self._extract_key_phrases(content)
        return "\n".join(key_phrases[:int(len(key_phrases) * ratio)])
    
    async def _summarize_technical_details(self, content: str, ratio: float) -> str:
        """总结技术细节"""
        # 提取技术概念和定义
        lines = content.split('\n')
        return '\n'.join(lines[:int(len(lines) * ratio)])
    
    async def _extract_code_snippets(self, content: str, ratio: float) -> str:
        """提取代码片段"""
        # 保留重要的代码块
        if "```" in content:
            # 保留代码块，压缩其他内容
            code_blocks = content.split("```")
            preserved_content = []
            for i, block in enumerate(code_blocks):
                if i % 2 == 1:  # 代码块
                    preserved_content.append(f"```{block}```")
                else:  # 非代码块
                    compressed = block[:int(len(block) * ratio)]
                    if compressed:
                        preserved_content.append(compressed)
            return "".join(preserved_content)
        else:
            return content[:int(len(content) * ratio)]
    
    async def _preserve_critical_errors(self, content: str, ratio: float) -> str:
        """保留关键错误"""
        # 保留错误信息和解决方案
        lines = content.split('\n')
        return '\n'.join(lines[:int(len(lines) * ratio)])
    
    async def _summarize_solutions(self, content: str, ratio: float) -> str:
        """总结解决方案"""
        # 提取解决方案要点
        key_points = self._extract_key_points(content)
        return "\n".join(key_points[:int(len(key_points) * ratio)])
    
    async def _extract_key_messages(self, content: str, ratio: float) -> str:
        """提取关键消息"""
        # 保留重要的用户消息
        messages = content.split('\n')
        return '\n'.join(messages[:int(len(messages) * ratio)])
    
    async def _list_actionable_items(self, content: str, ratio: float) -> str:
        """列出可执行项目"""
        # 保留待处理任务
        tasks = content.split('\n')
        return '\n'.join(tasks[:int(len(tasks) * ratio)])
    
    async def _highlight_progress(self, content: str, ratio: float) -> str:
        """突出进展"""
        # 保留当前工作状态
        return content[:int(len(content) * ratio)]
    
    async def _general_summarization(self, content: str, ratio: float) -> str:
        """通用摘要"""
        return content[:int(len(content) * ratio)]
    
    def _extract_key_phrases(self, content: str) -> List[str]:
        """提取关键短语"""
        # 简单的关键词提取
        lines = content.split('\n')
        key_phrases = []
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 10:  # 过滤太短的行
                key_phrases.append(line)
        
        return key_phrases
    
    def _extract_key_points(self, content: str) -> List[str]:
        """提取关键要点"""
        # 提取以特定标记开头的行
        lines = content.split('\n')
        key_points = []
        
        for line in lines:
            line = line.strip()
            if line.startswith(('-', '*', '•', '1.', '2.', '3.')):
                key_points.append(line)
        
        return key_points
    
    async def _generate_compression_result(self, sections: List[CompressionSection], original_context: Dict[str, Any]) -> CompressionResult:
        """生成压缩结果"""
        
        # 计算原始大小
        original_size = len(str(original_context))
        
        # 生成压缩后的内容
        compressed_content = {}
        total_compressed_size = 0
        
        for section in sections:
            if section.compressed_content:
                compressed_content[section.name] = section.compressed_content
                total_compressed_size += len(section.compressed_content)
        
        # 计算压缩比例
        compression_ratio = 1.0 - (total_compressed_size / original_size) if original_size > 0 else 0.0
        
        # 计算质量分数
        quality_score = self._calculate_quality_score(sections, compression_ratio)
        
        return CompressionResult(
            original_size=original_size,
            compressed_size=total_compressed_size,
            compression_ratio=compression_ratio,
            sections=sections,
            quality_score=quality_score
        )
    
    def _calculate_quality_score(self, sections: List[CompressionSection], compression_ratio: float) -> float:
        """计算质量分数"""
        
        if not sections:
            return 0.0
        
        # 基于重要性分数和压缩比例计算质量
        total_importance = sum(section.importance_score for section in sections)
        avg_importance = total_importance / len(sections)
        
        # 压缩比例过高会降低质量分数
        compression_penalty = max(0, compression_ratio - 0.8) * 2
        
        quality_score = avg_importance - compression_penalty
        
        return max(0.0, min(1.0, quality_score))
    
    async def generate_handoff_summary(self, compressed_context: CompressionResult) -> str:
        """生成交接总结 - 参考Claude Code的核心提示词"""
        
        handoff_prompt = f"""
我需要总结当前所有工作内容，后续将由其他开发者接手继续开发。

请基于以下压缩后的上下文，生成详细的交接总结：

## 压缩上下文信息
- 原始大小: {compressed_context.original_size} 字符
- 压缩后大小: {compressed_context.compressed_size} 字符
- 压缩比例: {compressed_context.compression_ratio:.2%}
- 质量分数: {compressed_context.quality_score:.2f}

## 上下文段落
{self._format_sections_for_handoff(compressed_context.sections)}

请按以下8个部分进行总结：

1. **Primary Request and Intent**: 主要请求和意图
2. **Key Technical Concepts**: 关键技术概念和决策
3. **Files and Code Sections**: 涉及的文件和代码段
4. **Errors and fixes**: 遇到的错误和解决方案
5. **Problem Solving**: 问题解决过程和方法
6. **All user messages**: 所有用户消息和反馈
7. **Pending Tasks**: 待完成的任务
8. **Current Work**: 当前工作状态和下一步计划

请确保总结足够详细，让后续开发者能够无缝接手继续开发。
        """
        
        # 如果有LLM管理器，使用LLM生成总结
        # if self.llm_manager: # This line is removed as per the edit hint
        #     try:
        #         # 获取LLM实例
        #         llm = self.llm_manager.get_llm_for_scene("main_agent")
                
        #         # 调用LLM生成总结
        #         llm_result = await llm.ainvoke(handoff_prompt)
                
        #         # 提取响应内容
        #         response = self._extract_llm_response(llm_result)
                
        #         return response
        #     except Exception as e:
        #         logger.error(f"LLM生成交接总结失败: {e}")
        
        # 否则返回手动生成的总结
        return self._generate_manual_handoff_summary(compressed_context)
    
    def _format_sections_for_handoff(self, sections: List[CompressionSection]) -> str:
        """格式化段落用于交接"""
        
        formatted = []
        for section in sections:
            if section.compressed_content:
                formatted.append(f"### {section.name}\n{section.compressed_content}")
        
        return "\n\n".join(formatted)
    
    def _generate_manual_handoff_summary(self, compressed_context: CompressionResult) -> str:
        """手动生成交接总结"""
        
        summary = f"""
# 工作交接总结

## 执行概况
- 原始上下文大小: {compressed_context.original_size} 字符
- 压缩后大小: {compressed_context.compressed_size} 字符
- 压缩质量: {compressed_context.quality_score:.2f}

## 关键信息摘要
"""
        
        for section in compressed_context.sections:
            if section.compressed_content:
                summary += f"\n### {section.name}\n{section.compressed_content}\n"
        
        summary += """
## 交接要点
1. 请仔细阅读上述上下文信息
2. 重点关注当前工作状态和待处理任务
3. 如有疑问，请参考原始上下文或联系前一个执行者
4. 继续执行时请保持工作的一致性和连续性

## 下一步建议
基于当前状态，建议优先处理：
- 待处理任务
- 当前工作中的关键问题
- 需要用户确认的重要决策
        """
        
        return summary
    
    def _extract_llm_response(self, llm_result) -> str:
        """从LLM结果中提取响应内容"""
        
        try:
            # 尝试从不同格式的结果中提取内容
            if hasattr(llm_result, 'generations') and llm_result.generations:
                # LangChain标准格式
                generation = llm_result.generations[0][0]
                if hasattr(generation, 'text'):
                    return generation.text
            
            elif hasattr(llm_result, 'content'):
                # 直接包含content属性
                return llm_result.content
            
            elif hasattr(llm_result, 'text'):
                # 直接包含text属性
                return llm_result.text
            
            else:
                # 降级处理
                return str(llm_result)
                
        except Exception as e:
            logger.error(f"提取LLM响应失败: {e}")
            return str(llm_result)
