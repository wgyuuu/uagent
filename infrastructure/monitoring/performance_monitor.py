from datetime import datetime
from typing import Dict, Any

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics = {
            "query_count": 0,
            "total_query_time": 0,
            "slow_queries": [],
            "connection_pool_stats": {},
            "cache_hit_rate": 0
        }
        self.slow_query_threshold = 1.0  # 1秒
    
    async def record_query_execution(self, 
                                   query: str,
                                   execution_time: float,
                                   result_count: int):
        """记录查询执行"""
        self.metrics["query_count"] += 1
        self.metrics["total_query_time"] += execution_time
        
        # 记录慢查询
        if execution_time > self.slow_query_threshold:
            self.metrics["slow_queries"].append({
                "query": query[:200] + "..." if len(query) > 200 else query,
                "execution_time": execution_time,
                "result_count": result_count,
                "timestamp": datetime.now()
            })
            
            # 只保留最近100个慢查询
            if len(self.metrics["slow_queries"]) > 100:
                self.metrics["slow_queries"] = self.metrics["slow_queries"][-100:]
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        avg_query_time = (
            self.metrics["total_query_time"] / self.metrics["query_count"]
            if self.metrics["query_count"] > 0 else 0
        )
        
        return {
            "total_queries": self.metrics["query_count"],
            "average_query_time": avg_query_time,
            "slow_query_count": len(self.metrics["slow_queries"]),
            "cache_hit_rate": self.metrics["cache_hit_rate"],
            "connection_pool_stats": self.metrics["connection_pool_stats"]
        }