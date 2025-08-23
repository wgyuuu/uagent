"""
Eight Segment Context Compression Engine

8段式上下文压缩引擎 - 智能记忆管理和优化
"""

from typing import Dict, List, Any, Optional, Tuple
import structlog
from datetime import datetime, timedelta
import json
import hashlib
from dataclasses import dataclass, asdict

from ...models.base import IsolatedRoleContext

logger = structlog.get_logger(__name__)


@dataclass
class CompressionSegment:
    """压缩段数据结构"""
    segment_id: str
    content: str
    importance_score: float
    last_accessed: datetime
    access_count: int
    compression_ratio: float
    metadata: Dict[str, Any]


class EightSegmentCompressionEngine:
    """
    8段式上下文压缩引擎
    
    基于wagent的设计，实现智能记忆管理和优化
    """
    
    def __init__(self, max_segments: int = 8, compression_threshold: float = 0.8):
        self.max_segments = max_segments
        self.compression_threshold = compression_threshold
        self.segments: Dict[str, CompressionSegment] = {}
        self.segment_history: List[CompressionSegment] = []
        
        # 段类型定义
        self.segment_types = {
            "primary_request": "主要请求",
            "key_concepts": "关键技术概念", 
            "files_code": "文件和代码",
            "errors_fixes": "错误和修复",
            "problem_solving": "问题解决过程",
            "user_messages": "用户消息历史",
            "pending_tasks": "待处理任务",
            "current_work": "当前工作状态"
        }
        
        logger.info("8段式上下文压缩引擎初始化完成")
    
    async def compress_context(
        self, 
        context: IsolatedRoleContext,
        role_id: str,
        compression_strategy: str = "adaptive"
    ) -> Dict[str, CompressionSegment]:
        """
        压缩上下文到8个关键段
        
        Args:
            context: 角色上下文
            role_id: 角色ID
            compression_strategy: 压缩策略
            
        Returns:
            压缩后的段字典
        """
        try:
            logger.info(f"开始压缩角色 {role_id} 的上下文")
            
            # 分析上下文内容
            content_analysis = await self._analyze_context_content(context)
            
            # 根据策略选择压缩方法
            if compression_strategy == "adaptive":
                segments = await self._adaptive_compression(content_analysis, role_id)
            elif compression_strategy == "importance_based":
                segments = await self._importance_based_compression(content_analysis, role_id)
            else:
                segments = await self._default_compression(content_analysis, role_id)
            
            # 更新段历史
            self._update_segment_history(segments)
            
            logger.info(f"角色 {role_id} 上下文压缩完成，生成了 {len(segments)} 个段")
            return segments
            
        except Exception as e:
            logger.error(f"上下文压缩失败: {e}")
            raise
    
    async def _analyze_context_content(self, context: IsolatedRoleContext) -> Dict[str, Any]:
        """分析上下文内容，提取关键信息"""
        analysis = {
            "content_length": len(str(context)),
            "key_topics": [],
            "important_concepts": [],
            "action_items": [],
            "technical_details": [],
            "user_interactions": []
        }
        
        # 分析主要请求
        if hasattr(context, 'primary_request') and context.primary_request:
            analysis["key_topics"].append("primary_request")
            analysis["important_concepts"].append(context.primary_request)
        
        # 分析技术概念
        if hasattr(context, 'technical_concepts') and context.technical_concepts:
            analysis["technical_details"].extend(context.technical_concepts)
        
        # 分析待处理任务
        if hasattr(context, 'pending_tasks') and context.pending_tasks:
            analysis["action_items"].extend(context.pending_tasks)
        
        # 分析用户交互
        if hasattr(context, 'user_messages') and context.user_messages:
            analysis["user_interactions"].extend(context.user_messages)
        
        return analysis
    
    async def _adaptive_compression(
        self, 
        content_analysis: Dict[str, Any], 
        role_id: str
    ) -> Dict[str, CompressionSegment]:
        """自适应压缩策略"""
        segments = {}
        
        # 1. 主要请求段
        if content_analysis["key_topics"]:
            segments["primary_request"] = self._create_segment(
                "primary_request",
                content_analysis["key_topics"][0],
                1.0,  # 最高重要性
                role_id
            )
        
        # 2. 关键技术概念段
        if content_analysis["important_concepts"]:
            concepts_text = "\n".join(content_analysis["important_concepts"][:3])
            segments["key_concepts"] = self._create_segment(
                "key_concepts",
                concepts_text,
                0.9,
                role_id
            )
        
        # 3. 文件和代码段
        if content_analysis["technical_details"]:
            tech_text = "\n".join(content_analysis["technical_details"][:5])
            segments["files_code"] = self._create_segment(
                "files_code",
                tech_text,
                0.8,
                role_id
            )
        
        # 4. 错误和修复段
        # 这里可以从上下文中提取错误信息
        segments["errors_fixes"] = self._create_segment(
            "errors_fixes",
            "暂无错误信息",
            0.6,
            role_id
        )
        
        # 5. 问题解决过程段
        if content_analysis["action_items"]:
            actions_text = "\n".join(content_analysis["action_items"][:3])
            segments["problem_solving"] = self._create_segment(
                "problem_solving",
                actions_text,
                0.7,
                role_id
            )
        
        # 6. 用户消息历史段
        if content_analysis["user_interactions"]:
            user_text = "\n".join(content_analysis["user_interactions"][-3:])
            segments["user_messages"] = self._create_segment(
                "user_messages",
                user_text,
                0.5,
                role_id
            )
        
        # 7. 待处理任务段
        if content_analysis["action_items"]:
            tasks_text = "\n".join(content_analysis["action_items"][:5])
            segments["pending_tasks"] = self._create_segment(
                "pending_tasks",
                tasks_text,
                0.8,
                role_id
            )
        
        # 8. 当前工作状态段
        segments["current_work"] = self._create_segment(
            "current_work",
            f"角色 {role_id} 正在处理任务",
            0.6,
            role_id
        )
        
        return segments
    
    async def _importance_based_compression(
        self, 
        content_analysis: Dict[str, Any], 
        role_id: str
    ) -> Dict[str, CompressionSegment]:
        """基于重要性的压缩策略"""
        # 计算每个内容的重要性分数
        importance_scores = {}
        
        for topic in content_analysis["key_topics"]:
            importance_scores[topic] = 1.0
        
        for concept in content_analysis["important_concepts"]:
            importance_scores[concept] = 0.9
        
        for detail in content_analysis["technical_details"]:
            importance_scores[detail] = 0.8
        
        # 按重要性排序，选择前8个
        sorted_items = sorted(
            importance_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:self.max_segments]
        
        segments = {}
        for i, (content, score) in enumerate(sorted_items):
            segment_type = list(self.segment_types.keys())[i]
            segments[segment_type] = self._create_segment(
                segment_type,
                content,
                score,
                role_id
            )
        
        return segments
    
    async def _default_compression(
        self, 
        content_analysis: Dict[str, Any], 
        role_id: str
    ) -> Dict[str, CompressionSegment]:
        """默认压缩策略"""
        segments = {}
        
        # 创建8个默认段
        for segment_type in self.segment_types.keys():
            segments[segment_type] = self._create_segment(
                segment_type,
                f"默认{self.segment_types[segment_type]}内容",
                0.5,
                role_id
            )
        
        return segments
    
    def _create_segment(
        self, 
        segment_type: str, 
        content: str, 
        importance: float, 
        role_id: str
    ) -> CompressionSegment:
        """创建压缩段"""
        # 计算压缩比
        original_length = len(content)
        compressed_length = len(content.encode('utf-8'))
        compression_ratio = compressed_length / original_length if original_length > 0 else 1.0
        
        # 生成段ID
        segment_id = f"{role_id}_{segment_type}_{hashlib.md5(content.encode()).hexdigest()[:8]}"
        
        return CompressionSegment(
            segment_id=segment_id,
            content=content,
            importance_score=importance,
            last_accessed=datetime.now(),
            access_count=1,
            compression_ratio=compression_ratio,
            metadata={
                "role_id": role_id,
                "segment_type": segment_type,
                "created_at": datetime.now().isoformat(),
                "original_length": original_length,
                "compressed_length": compressed_length
            }
        )
    
    def _update_segment_history(self, segments: Dict[str, CompressionSegment]):
        """更新段历史记录"""
        for segment in segments.values():
            self.segment_history.append(segment)
            
            # 保持历史记录在合理范围内
            if len(self.segment_history) > 100:
                self.segment_history = self.segment_history[-50:]
    
    async def decompress_context(
        self, 
        segments: Dict[str, CompressionSegment]
    ) -> str:
        """
        解压缩上下文段
        
        Args:
            segments: 压缩段字典
            
        Returns:
            解压缩后的完整上下文
        """
        try:
            logger.info("开始解压缩上下文")
            
            # 按重要性排序段
            sorted_segments = sorted(
                segments.values(),
                key=lambda x: x.importance_score,
                reverse=True
            )
            
            # 重建上下文
            context_parts = []
            for segment in sorted_segments:
                context_parts.append(f"## {self.segment_types.get(segment.metadata['segment_type'], '未知段')}")
                context_parts.append(segment.content)
                context_parts.append("")  # 空行分隔
            
            full_context = "\n".join(context_parts)
            
            logger.info(f"上下文解压缩完成，总长度: {len(full_context)}")
            return full_context
            
        except Exception as e:
            logger.error(f"上下文解压缩失败: {e}")
            raise
    
    async def optimize_segments(
        self, 
        segments: Dict[str, CompressionSegment],
        target_compression_ratio: float = 0.7
    ) -> Dict[str, CompressionSegment]:
        """
        优化压缩段，提高压缩比
        
        Args:
            segments: 当前段字典
            target_compression_ratio: 目标压缩比
            
        Returns:
            优化后的段字典
        """
        try:
            logger.info("开始优化压缩段")
            
            optimized_segments = {}
            
            for segment_type, segment in segments.items():
                # 检查是否需要优化
                if segment.compression_ratio > target_compression_ratio:
                    # 应用文本压缩算法
                    optimized_content = await self._compress_text(segment.content)
                    
                    # 创建优化后的段
                    optimized_segment = CompressionSegment(
                        segment_id=segment.segment_id,
                        content=optimized_content,
                        importance_score=segment.importance_score,
                        last_accessed=segment.last_accessed,
                        access_count=segment.access_count,
                        compression_ratio=len(optimized_content.encode()) / len(segment.content),
                        metadata=segment.metadata.copy()
                    )
                    
                    optimized_segments[segment_type] = optimized_segment
                else:
                    optimized_segments[segment_type] = segment
            
            logger.info("压缩段优化完成")
            return optimized_segments
            
        except Exception as e:
            logger.error(f"压缩段优化失败: {e}")
            raise
    
    async def _compress_text(self, text: str) -> str:
        """压缩文本内容"""
        # 简单的文本压缩算法
        # 1. 移除多余空白
        compressed = " ".join(text.split())
        
        # 2. 缩写常见词汇
        abbreviations = {
            "function": "func",
            "variable": "var",
            "parameter": "param",
            "configuration": "config",
            "information": "info"
        }
        
        for full, abbr in abbreviations.items():
            compressed = compressed.replace(full, abbr)
        
        # 3. 移除重复内容
        lines = compressed.split('\n')
        unique_lines = []
        seen = set()
        
        for line in lines:
            line_hash = hashlib.md5(line.encode()).hexdigest()
            if line_hash not in seen:
                unique_lines.append(line)
                seen.add(line_hash)
        
        return '\n'.join(unique_lines)
    
    async def get_compression_stats(self) -> Dict[str, Any]:
        """获取压缩统计信息"""
        if not self.segments:
            return {"message": "暂无压缩数据"}
        
        total_segments = len(self.segments)
        avg_importance = sum(s.importance_score for s in self.segments.values()) / total_segments
        avg_compression_ratio = sum(s.compression_ratio for s in self.segments.values()) / total_segments
        
        return {
            "total_segments": total_segments,
            "average_importance_score": round(avg_importance, 3),
            "average_compression_ratio": round(avg_compression_ratio, 3),
            "segment_types": list(self.segments.keys()),
            "total_history_records": len(self.segment_history)
        }
    
    async def cleanup_old_segments(self, max_age_hours: int = 24):
        """清理过期的段"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            # 清理主段字典
            old_segments = [
                segment_id for segment_id, segment in self.segments.items()
                if segment.last_accessed < cutoff_time
            ]
            
            for segment_id in old_segments:
                del self.segments[segment_id]
            
            # 清理历史记录
            self.segment_history = [
                segment for segment in self.segment_history
                if segment.last_accessed >= cutoff_time
            ]
            
            logger.info(f"清理了 {len(old_segments)} 个过期段")
            
        except Exception as e:
            logger.error(f"清理过期段失败: {e}")
            raise
