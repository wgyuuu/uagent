"""
LLM Logging Utilities

LLM日志工具模块 - 提供配置管理、性能统计和日志格式化功能
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class LoggingConfig:
    """日志配置"""
    enabled: bool = True
    log_level: LogLevel = LogLevel.INFO
    include_prompt: bool = True
    include_response: bool = True
    include_call_context: bool = True
    include_performance: bool = True
    max_prompt_length: int = 10000
    max_response_length: int = 10000
    performance_threshold_ms: int = 5000  # 性能警告阈值
    log_to_file: bool = False
    log_file_path: str = "logs/llm_calls.log"


class PerformanceTracker:
    """性能追踪器"""
    
    def __init__(self):
        self.stats: Dict[str, Dict[str, Any]] = {}
        self.recent_calls: List[Dict[str, Any]] = []
        self.max_recent_calls = 1000
    
    def record_call(self, scene_key: str, model_name: str, duration: float, 
                   token_count: int, success: bool, error: Optional[str] = None):
        """记录调用统计"""
        # 更新场景统计
        if scene_key not in self.stats:
            self.stats[scene_key] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_duration": 0.0,
                "total_tokens": 0,
                "avg_duration": 0.0,
                "avg_tokens": 0.0,
                "min_duration": float('inf'),
                "max_duration": 0.0,
                "last_call": None
            }
        
        stats = self.stats[scene_key]
        stats["total_calls"] += 1
        stats["total_duration"] += duration
        stats["total_tokens"] += token_count
        stats["last_call"] = datetime.now().isoformat()
        
        if success:
            stats["successful_calls"] += 1
        else:
            stats["failed_calls"] += 1
        
        # 更新平均值
        stats["avg_duration"] = stats["total_duration"] / stats["total_calls"]
        stats["avg_tokens"] = stats["total_tokens"] / stats["total_calls"]
        
        # 更新最值
        stats["min_duration"] = min(stats["min_duration"], duration)
        stats["max_duration"] = max(stats["max_duration"], duration)
        
        # 记录最近调用
        recent_call = {
            "timestamp": datetime.now().isoformat(),
            "scene_key": scene_key,
            "model_name": model_name,
            "duration": duration,
            "token_count": token_count,
            "success": success,
            "error": error
        }
        
        self.recent_calls.append(recent_call)
        if len(self.recent_calls) > self.max_recent_calls:
            self.recent_calls.pop(0)
    
    def get_scene_stats(self, scene_key: str) -> Dict[str, Any]:
        """获取场景统计信息"""
        return self.stats.get(scene_key, {})
    
    def get_overall_stats(self) -> Dict[str, Any]:
        """获取总体统计信息"""
        if not self.stats:
            return {}
        
        total_calls = sum(s["total_calls"] for s in self.stats.values())
        total_duration = sum(s["total_duration"] for s in self.stats.values())
        total_tokens = sum(s["total_tokens"] for s in self.stats.values())
        
        return {
            "total_scenes": len(self.stats),
            "total_calls": total_calls,
            "total_duration": total_duration,
            "total_tokens": total_tokens,
            "avg_duration": total_duration / total_calls if total_calls > 0 else 0,
            "avg_tokens": total_tokens / total_calls if total_calls > 0 else 0,
            "scenes": self.stats
        }
    
    def get_recent_calls(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取最近的调用记录"""
        return self.recent_calls[-limit:]
    
    def clear_stats(self):
        """清除统计信息"""
        self.stats.clear()
        self.recent_calls.clear()


class LogFormatter:
    """日志格式化器"""
    
    def __init__(self, config: LoggingConfig):
        self.config = config
    
    def format_request_log(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化请求日志"""
        if not self.config.enabled:
            return {}
        
        formatted = {
            "type": "LLM_REQUEST",
            "timestamp": request_data.get("timestamp"),
            "request_id": request_data.get("request_id"),
            "scene_key": request_data.get("model_info", {}).get("scene_key"),
            "model_name": request_data.get("model_info", {}).get("model_name"),
            "provider_type": request_data.get("model_info", {}).get("provider_type"),
            "stream": request_data.get("stream", False)
        }
        
        # 添加调用上下文
        if self.config.include_call_context and "call_context" in request_data:
            call_context = request_data["call_context"]
            formatted.update({
                "call_file": call_context.get("file"),
                "call_line": call_context.get("line"),
                "call_function": call_context.get("function")
            })
        
        # 添加prompt内容
        if self.config.include_prompt and "prompt" in request_data:
            prompt = request_data["prompt"]
            if len(prompt) > self.config.max_prompt_length:
                prompt = prompt[:self.config.max_prompt_length] + "...[截断]"
            formatted["prompt"] = prompt
        
        # 添加参数信息
        if "parameters" in request_data:
            formatted["parameters"] = request_data["parameters"]
        
        return formatted
    
    def format_response_log(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化响应日志"""
        if not self.config.enabled:
            return {}
        
        formatted = {
            "type": "LLM_RESPONSE",
            "timestamp": response_data.get("timestamp"),
            "response_id": response_data.get("response_id"),
            "request_id": response_data.get("request_id"),
            "finish_reason": response_data.get("finish_reason"),
            "error": response_data.get("error")
        }
        
        # 添加响应内容
        if self.config.include_response and "content" in response_data:
            content = response_data["content"]
            if len(content) > self.config.max_response_length:
                content = content[:self.config.max_response_length] + "...[截断]"
            formatted["content"] = content
        
        # 添加性能指标
        if self.config.include_performance and "performance" in response_data:
            performance = response_data["performance"]
            formatted.update({
                "duration": performance.get("duration"),
                "tokens_per_second": performance.get("tokens_per_second")
            })
        
        # 添加token使用统计
        if "token_usage" in response_data:
            formatted["token_usage"] = response_data["token_usage"]
        
        # 添加流式chunk信息
        if "stream_chunks" in response_data:
            chunk_count = len(response_data["stream_chunks"])
            formatted["chunk_count"] = chunk_count
        
        return formatted
    
    def format_performance_warning(self, scene_key: str, duration: float, 
                                 threshold_ms: int) -> Dict[str, Any]:
        """格式化性能警告"""
        return {
            "type": "PERFORMANCE_WARNING",
            "timestamp": datetime.now().isoformat(),
            "scene_key": scene_key,
            "duration_ms": duration * 1000,
            "threshold_ms": threshold_ms,
            "message": f"LLM调用耗时 {duration:.2f}秒，超过阈值 {threshold_ms/1000:.2f}秒"
        }


class LLMLoggingManager:
    """LLM日志管理器"""
    
    def __init__(self, config: Optional[LoggingConfig] = None):
        self.config = config or LoggingConfig()
        self.performance_tracker = PerformanceTracker()
        self.formatter = LogFormatter(self.config)
        
        logger.info("LLM日志管理器初始化完成", config=asdict(self.config))
    
    def update_config(self, new_config: LoggingConfig):
        """更新配置"""
        self.config = new_config
        self.formatter = LogFormatter(self.config)
        logger.info("LLM日志配置已更新", new_config=asdict(new_config))
    
    def log_request(self, request_data: Dict[str, Any]):
        """记录请求日志"""
        if not self.config.enabled:
            return
        
        formatted = self.formatter.format_request_log(request_data)
        if formatted:
            logger.info("LLM请求", **formatted)
    
    def log_response(self, response_data: Dict[str, Any]):
        """记录响应日志"""
        if not self.config.enabled:
            return
        
        formatted = self.formatter.format_response_log(response_data)
        if formatted:
            logger.info("LLM响应", **formatted)
        
        # 检查性能警告
        if self.config.include_performance:
            performance = response_data.get("performance", {})
            duration = performance.get("duration", 0)
            if duration * 1000 > self.config.performance_threshold_ms:
                scene_key = response_data.get("model_info", {}).get("scene_key", "unknown")
                warning = self.formatter.format_performance_warning(
                    scene_key, duration, self.config.performance_threshold_ms
                )
                logger.warning("性能警告", **warning)
    
    def record_performance(self, scene_key: str, model_name: str, duration: float,
                          token_count: int, success: bool, error: Optional[str] = None):
        """记录性能统计"""
        self.performance_tracker.record_call(
            scene_key, model_name, duration, token_count, success, error
        )
    
    def get_performance_stats(self, scene_key: Optional[str] = None) -> Dict[str, Any]:
        """获取性能统计"""
        if scene_key:
            return self.performance_tracker.get_scene_stats(scene_key)
        return self.performance_tracker.get_overall_stats()
    
    def get_recent_calls(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取最近的调用记录"""
        return self.performance_tracker.get_recent_calls(limit)
    
    def clear_stats(self):
        """清除统计信息"""
        self.performance_tracker.clear_stats()
        logger.info("LLM性能统计已清除")


# 全局日志管理器实例
_global_logging_manager: Optional[LLMLoggingManager] = None


def get_logging_manager() -> LLMLoggingManager:
    """获取全局日志管理器实例"""
    global _global_logging_manager
    if _global_logging_manager is None:
        _global_logging_manager = LLMLoggingManager()
    return _global_logging_manager


def set_logging_manager(manager: LLMLoggingManager):
    """设置全局日志管理器实例"""
    global _global_logging_manager
    _global_logging_manager = manager


def configure_logging(config: LoggingConfig):
    """配置全局日志管理器"""
    manager = get_logging_manager()
    manager.update_config(config)
    set_logging_manager(manager)
