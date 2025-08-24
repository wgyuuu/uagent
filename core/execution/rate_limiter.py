"""
Rate Limiter

速率限制器 - 负责工具调用的频率控制
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
import structlog

logger = structlog.get_logger(__name__)


class RateLimiter:
    """
    速率限制器
    
    负责工具调用的频率控制，包括：
    - 基于时间窗口的速率限制
    - 角色级别的配额管理
    - 动态调整限制策略
    """
    
    def __init__(self):
        """初始化速率限制器"""
        # 默认速率限制配置
        self.rate_limits = self._load_default_rate_limits()
        
        # 使用跟踪记录
        self.usage_tracking: Dict[str, List[datetime]] = {}
        
        # 动态限制调整
        self.dynamic_adjustments: Dict[str, Dict[str, Any]] = {}
        
        # 清理任务
        self.cleanup_task = None
        self._start_cleanup_task()
        
        logger.info("速率限制器初始化完成")
    
    def _load_default_rate_limits(self) -> Dict[str, Dict[str, Any]]:
        """加载默认速率限制配置"""
        return {
            "user_interaction": {
                "requests": 10,      # 10次/分钟
                "window": 60,        # 60秒窗口
                "burst": 5           # 突发允许5次
            },
            "web_services": {
                "requests": 100,     # 100次/分钟
                "window": 60,
                "burst": 20
            },
            "file_operations": {
                "requests": 50,      # 50次/分钟
                "window": 60,
                "burst": 10
            },
            "development_tools": {
                "requests": 30,      # 30次/分钟
                "window": 60,
                "burst": 5
            },
            "system_utilities": {
                "requests": 20,      # 20次/分钟
                "window": 60,
                "burst": 3
            },
            "default": {
                "requests": 30,      # 默认30次/分钟
                "window": 60,
                "burst": 5
            }
        }
    
    def _start_cleanup_task(self):
        """启动清理任务"""
        self.cleanup_task = asyncio.create_task(self._cleanup_expired_records())
    
    async def _cleanup_expired_records(self):
        """清理过期的使用记录"""
        while True:
            try:
                await self._cleanup_expired_usage_records()
                await asyncio.sleep(60)  # 每分钟清理一次
                
            except Exception as e:
                logger.error(f"清理过期记录失败: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_expired_usage_records(self):
        """清理过期的使用记录"""
        try:
            current_time = datetime.now()
            expired_keys = []
            
            for tracking_key, timestamps in self.usage_tracking.items():
                # 获取该工具的限制配置
                tool_category = self._extract_tool_category(tracking_key)
                limit_config = self.rate_limits.get(tool_category, self.rate_limits["default"])
                window_seconds = limit_config["window"]
                
                # 计算截止时间
                cutoff_time = current_time - timedelta(seconds=window_seconds)
                
                # 过滤过期记录
                valid_timestamps = [
                    ts for ts in timestamps if ts > cutoff_time
                ]
                
                if valid_timestamps:
                    self.usage_tracking[tracking_key] = valid_timestamps
                else:
                    expired_keys.append(tracking_key)
            
            # 清理过期的键
            for key in expired_keys:
                del self.usage_tracking[key]
            
            if expired_keys:
                logger.debug(f"清理了 {len(expired_keys)} 个过期的使用记录")
                
        except Exception as e:
            logger.error(f"清理过期使用记录失败: {e}")
    
    def _extract_tool_category(self, tracking_key: str) -> str:
        """从跟踪键中提取工具类别"""
        try:
            # 跟踪键格式: "role:tool_category:tool_name"
            parts = tracking_key.split(":")
            if len(parts) >= 2:
                return parts[1]
            return "default"
        except Exception:
            return "default"
    
    async def check_rate_limit(self, 
                             role: str,
                             tool_category: str,
                             tool_name: str) -> bool:
        """
        检查速率限制
        
        Args:
            role: 角色名称
            tool_category: 工具类别
            tool_name: 工具名称
            
        Returns:
            是否允许调用
        """
        try:
            # 生成跟踪键
            tracking_key = f"{role}:{tool_category}:{tool_name}"
            
            # 获取限制配置
            limit_config = self.rate_limits.get(tool_category, self.rate_limits["default"])
            max_requests = limit_config["requests"]
            time_window = limit_config["window"]
            burst_limit = limit_config["burst"]
            
            # 获取当前使用记录
            current_usage = self.usage_tracking.get(tracking_key, [])
            current_time = datetime.now()
            
            # 计算时间窗口内的使用量
            window_start = current_time - timedelta(seconds=time_window)
            recent_usage = [
                ts for ts in current_usage if ts > window_start
            ]
            
            # 检查是否超出限制
            if len(recent_usage) >= max_requests:
                logger.debug(f"速率限制: {tracking_key} 已达到限制 {max_requests}/{time_window}s")
                return False
            
            # 检查突发限制
            if len(recent_usage) >= burst_limit:
                # 检查最近的使用频率
                if len(recent_usage) >= 2:
                    time_diff = (recent_usage[-1] - recent_usage[-2]).total_seconds()
                    if time_diff < 1:  # 如果两次调用间隔小于1秒
                        logger.debug(f"突发限制: {tracking_key} 调用过于频繁")
                        return False
            
            # 记录本次使用
            if tracking_key not in self.usage_tracking:
                self.usage_tracking[tracking_key] = []
            
            self.usage_tracking[tracking_key].append(current_time)
            
            return True
            
        except Exception as e:
            logger.error(f"检查速率限制失败: {e}")
            # 出错时默认允许
            return True
    
    async def get_remaining_quota(self, 
                                role: str,
                                tool_category: str,
                                tool_name: str) -> Dict[str, Any]:
        """
        获取剩余配额
        
        Args:
            role: 角色名称
            tool_category: 工具类别
            tool_name: 工具名称
            
        Returns:
            配额信息
        """
        try:
            tracking_key = f"{role}:{tool_category}:{tool_name}"
            
            # 获取限制配置
            limit_config = self.rate_limits.get(tool_category, self.rate_limits["default"])
            max_requests = limit_config["requests"]
            time_window = limit_config["window"]
            
            # 获取当前使用记录
            current_usage = self.usage_tracking.get(tracking_key, [])
            current_time = datetime.now()
            
            # 计算时间窗口内的使用量
            window_start = current_time - timedelta(seconds=time_window)
            recent_usage = [
                ts for ts in current_usage if ts > window_start
            ]
            
            # 计算剩余配额
            remaining = max(0, max_requests - len(recent_usage))
            
            # 计算重置时间
            reset_time = None
            if recent_usage:
                oldest_request = min(recent_usage)
                reset_time = oldest_request + timedelta(seconds=time_window)
            
            return {
                "remaining": remaining,
                "total": max_requests,
                "used": len(recent_usage),
                "reset_time": reset_time.isoformat() if reset_time else None,
                "window_seconds": time_window,
                "tool_category": tool_category,
                "role": role
            }
            
        except Exception as e:
            logger.error(f"获取剩余配额失败: {e}")
            return {
                "remaining": 0,
                "total": 0,
                "used": 0,
                "reset_time": None,
                "window_seconds": 0,
                "error": str(e)
            }
    
    async def get_rate_limit_info(self, tool_category: str = None) -> Dict[str, Any]:
        """获取速率限制信息"""
        try:
            if tool_category:
                return self.rate_limits.get(tool_category, {})
            
            return {
                "rate_limits": self.rate_limits,
                "usage_tracking_keys": list(self.usage_tracking.keys()),
                "total_tracked_tools": len(self.usage_tracking)
            }
            
        except Exception as e:
            logger.error(f"获取速率限制信息失败: {e}")
            return {}
    
    def update_rate_limit(self, 
                         tool_category: str, 
                         new_limits: Dict[str, Any]):
        """更新速率限制配置"""
        try:
            if tool_category in self.rate_limits:
                self.rate_limits[tool_category].update(new_limits)
                logger.info(f"工具类别 {tool_category} 的速率限制已更新")
            else:
                self.rate_limits[tool_category] = new_limits
                logger.info(f"工具类别 {tool_category} 的速率限制已添加")
                
        except Exception as e:
            logger.error(f"更新速率限制失败: {e}")
    
    def add_dynamic_adjustment(self, 
                              tool_category: str, 
                              adjustment: Dict[str, Any]):
        """添加动态调整规则"""
        try:
            self.dynamic_adjustments[tool_category] = adjustment
            logger.info(f"工具类别 {tool_category} 的动态调整规则已添加")
            
        except Exception as e:
            logger.error(f"添加动态调整规则失败: {e}")
    
    def remove_dynamic_adjustment(self, tool_category: str):
        """移除动态调整规则"""
        try:
            if tool_category in self.dynamic_adjustments:
                del self.dynamic_adjustments[tool_category]
                logger.info(f"工具类别 {tool_category} 的动态调整规则已移除")
                
        except Exception as e:
            logger.error(f"移除动态调整规则失败: {e}")
    
    async def apply_dynamic_adjustments(self):
        """应用动态调整规则"""
        try:
            current_time = datetime.now()
            
            for tool_category, adjustment in self.dynamic_adjustments.items():
                # 检查调整条件
                if self._should_apply_adjustment(adjustment, current_time):
                    # 应用调整
                    new_limits = adjustment.get("new_limits", {})
                    self.update_rate_limit(tool_category, new_limits)
                    
                    logger.info(f"已应用工具类别 {tool_category} 的动态调整")
                    
        except Exception as e:
            logger.error(f"应用动态调整失败: {e}")
    
    def _should_apply_adjustment(self, adjustment: Dict[str, Any], current_time: datetime) -> bool:
        """检查是否应该应用调整"""
        try:
            # 检查时间条件
            if "time_condition" in adjustment:
                time_condition = adjustment["time_condition"]
                
                # 检查是否在指定时间范围内
                if "start_time" in time_condition:
                    start_time = datetime.fromisoformat(time_condition["start_time"])
                    if current_time < start_time:
                        return False
                
                if "end_time" in time_condition:
                    end_time = datetime.fromisoformat(time_condition["end_time"])
                    if current_time > end_time:
                        return False
            
            # 检查使用量条件
            if "usage_condition" in adjustment:
                usage_condition = adjustment["usage_condition"]
                current_usage = usage_condition.get("current_usage", 0)
                threshold = usage_condition.get("threshold", 0)
                
                if current_usage < threshold:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查调整条件失败: {e}")
            return False
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """获取使用统计信息"""
        try:
            stats = {}
            
            for tracking_key, timestamps in self.usage_tracking.items():
                if not timestamps:
                    continue
                
                # 解析跟踪键
                parts = tracking_key.split(":")
                if len(parts) >= 3:
                    role, tool_category, tool_name = parts[0], parts[1], parts[2]
                    
                    if tool_category not in stats:
                        stats[tool_category] = {}
                    
                    if role not in stats[tool_category]:
                        stats[tool_category][role] = {}
                    
                    # 计算使用统计
                    total_calls = len(timestamps)
                    recent_calls = len([
                        ts for ts in timestamps 
                        if ts > datetime.now() - timedelta(hours=1)
                    ])
                    
                    stats[tool_category][role][tool_name] = {
                        "total_calls": total_calls,
                        "recent_calls_1h": recent_calls,
                        "last_called": max(timestamps).isoformat() if timestamps else None
                    }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取使用统计失败: {e}")
            return {}
    
    async def shutdown(self):
        """关闭速率限制器"""
        try:
            if self.cleanup_task:
                self.cleanup_task.cancel()
                try:
                    await self.cleanup_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("速率限制器已关闭")
            
        except Exception as e:
            logger.error(f"关闭速率限制器失败: {e}")
