"""
Tool Executor

工具执行器 - 基于工具特性和上下文智能选择执行策略
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import structlog
from dataclasses import dataclass

from tools.mcp import MCPToolRegistry
from models.base import ToolExecutionResult

logger = structlog.get_logger(__name__)


@dataclass
class ToolCall:
    """工具调用定义"""
    tool_name: str
    parameters: Dict[str, Any]
    priority: int = 1  # 优先级，数字越小优先级越高
    dependencies: List[str] = None  # 依赖的工具名称
    timeout: int = 30  # 超时时间
    retry_count: int = 0  # 重试次数
    max_retries: int = 3  # 最大重试次数


@dataclass
class ToolResult:
    """工具执行结果"""
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = None


@dataclass
class ExecutionStrategy:
    """执行策略"""
    strategy_type: str  # "parallel", "sequential", "mixed"
    parallel_tools: List[str]  # 可以并行执行的工具
    sequential_tools: List[str]  # 必须串行执行的工具
    execution_order: List[str]  # 执行顺序


class ToolExecutor:
    """
    工具执行器
    
    基于工具特性和上下文智能选择执行策略：
    - 并发安全工具并行执行
    - 有依赖关系的工具按顺序执行
    - 资源密集型工具避免同时执行
    """
    
    def __init__(self, tool_registry: MCPToolRegistry):
        """初始化工具执行器"""
        self.tool_registry = tool_registry  # 依赖注入的工具注册表
        
        # 执行历史管理
        self.execution_history: List[ToolExecutionResult] = []
        self.execution_stats: Dict[str, Dict[str, Any]] = {}
        
        logger.info("工具执行器初始化完成")
    
    async def execute_single_tool(self, 
                                tool_name: str, 
                                parameters: Dict[str, Any], 
                                context: Dict[str, Any] = None) -> ToolResult:
        """
        执行单个工具
        
        Args:
            tool_name: 工具名称
            parameters: 工具参数
            context: 执行上下文
            
        Returns:
            工具执行结果
        """
        start_time = datetime.now()
        
        try:
            # 根据工具类型选择执行器并执行工具
            result = await self._execute_tool_by_type(tool_name, parameters, context)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 构建结果
            tool_result = ToolResult(
                tool_name=tool_name,
                success=result.success,
                result=result.output if hasattr(result, 'output') else result.result,
                error=result.error,
                execution_time=execution_time,
                metadata=result.metadata
            )
            
            # 记录执行历史
            self._record_execution_history(tool_name, True, execution_time, context)
            
            return tool_result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"执行工具 {tool_name} 失败: {e}")
            
            # 构建错误结果
            error_result = ToolResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                execution_time=execution_time,
                metadata={
                    "error_type": type(e).__name__,
                    "error_details": str(e)
                }
            )
            
            # 记录执行历史
            self._record_execution_history(tool_name, False, execution_time, context, str(e))
            
            return error_result
    
    async def execute_tool_calls(self, 
                               tool_calls: List[Dict[str, Any]], 
                               context: Dict[str, Any] = None) -> List[ToolResult]:
        """
        智能执行工具调用
        
        Args:
            tool_calls: 工具调用列表
            context: 执行上下文
            
        Returns:
            工具执行结果列表
        """
        try:
            # 1. 转换工具调用格式
            tool_calls_objects = self._convert_to_tool_calls(tool_calls)
            
            # 2. 分析工具特性和依赖关系
            execution_strategy = self._analyze_execution_strategy(tool_calls_objects)
            
            # 3. 按策略执行工具
            if execution_strategy.strategy_type == "parallel":
                results = await self._execute_parallel(tool_calls_objects, context)
            elif execution_strategy.strategy_type == "sequential":
                results = await self._execute_sequential(tool_calls_objects, context)
            else:  # mixed
                results = await self._execute_mixed(tool_calls_objects, execution_strategy, context)
            
            return results
            
        except Exception as e:
            logger.error(f"执行工具调用失败: {e}")
            raise
    
    def _convert_to_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[ToolCall]:
        """转换工具调用格式"""
        converted = []
        for tool_call in tool_calls:
            converted.append(ToolCall(
                tool_name=tool_call.get("tool_name", ""),
                parameters=tool_call.get("parameters", {}),
                priority=tool_call.get("priority", 1),
                dependencies=tool_call.get("dependencies"),
                timeout=tool_call.get("timeout", 30),
                retry_count=tool_call.get("retry_count", 0),
                max_retries=tool_call.get("max_retries", 3)
            ))
        return converted
    
    def _analyze_execution_strategy(self, tool_calls: List[ToolCall]) -> ExecutionStrategy:
        """分析执行策略"""
        # 简单的策略分析，可以根据需要扩展
        parallel_tools = []
        sequential_tools = []
        
        for tool_call in tool_calls:
            if tool_call.dependencies:
                sequential_tools.append(tool_call.tool_name)
            else:
                parallel_tools.append(tool_call.tool_name)
        
        if not sequential_tools:
            strategy_type = "parallel"
        elif not parallel_tools:
            strategy_type = "sequential"
        else:
            strategy_type = "mixed"
        
        return ExecutionStrategy(
            strategy_type=strategy_type,
            parallel_tools=parallel_tools,
            sequential_tools=sequential_tools,
            execution_order=[tc.tool_name for tc in tool_calls]
        )
    
    async def _execute_parallel(self, tool_calls: List[ToolCall], context: Dict[str, Any]) -> List[ToolResult]:
        """并行执行工具"""
        tasks = []
        for tool_call in tool_calls:
            task = asyncio.create_task(
                self.execute_single_tool(tool_call.tool_name, tool_call.parameters, context)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ToolResult(
                    tool_name=tool_calls[i].tool_name,
                    success=False,
                    error=str(result),
                    execution_time=0,
                    metadata={"error_type": type(result).__name__}
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _execute_sequential(self, tool_calls: List[ToolCall], context: Dict[str, Any]) -> List[ToolResult]:
        """串行执行工具"""
        results = []
        for tool_call in tool_calls:
            result = await self.execute_single_tool(tool_call.tool_name, tool_call.parameters, context)
            results.append(result)
        return results
    
    async def _execute_mixed(self, tool_calls: List[ToolCall], strategy: ExecutionStrategy, context: Dict[str, Any]) -> List[ToolResult]:
        """混合执行工具"""
        results = []
        
        # 先执行串行工具
        for tool_name in strategy.sequential_tools:
            tool_call = next(tc for tc in tool_calls if tc.tool_name == tool_name)
            result = await self.execute_single_tool(tool_call.tool_name, tool_call.parameters, context)
            results.append(result)
        
        # 再执行并行工具
        parallel_calls = [tc for tc in tool_calls if tc.tool_name in strategy.parallel_tools]
        if parallel_calls:
            parallel_results = await self._execute_parallel(parallel_calls, context)
            results.extend(parallel_results)
        
        return results
    
    async def _execute_tool_by_type(self, 
                                  tool_name: str, 
                                  parameters: Dict[str, Any], 
                                  context: Dict[str, Any] = None) -> ToolExecutionResult:
        """
        根据工具类型选择执行器并执行工具
        
        Args:
            tool_name: 工具名称
            parameters: 工具参数
            context: 执行上下文
            
        Returns:
            工具执行结果
        """
        try:
            # 直接通过工具注册表执行工具
            result = await self.tool_registry.execute_tool(tool_name, parameters)
            
            # 包装返回结果为 ToolExecutionResult 格式
            if hasattr(result, 'success'):
                # 如果已经是 ToolExecutionResult 格式
                return result
            else:
                # 包装为 ToolExecutionResult 格式
                return ToolExecutionResult(
                    tool_name=tool_name,
                    success=True,
                    result=result,
                    execution_time=0,  # 这里会在上层重新计算
                    metadata={"context": context or {}}
                )
            
        except Exception as e:
            logger.error(f"执行工具 {tool_name} 失败: {e}")
            raise
    
    def _record_execution_history(self, 
                                tool_name: str, 
                                success: bool, 
                                execution_time: float, 
                                context: Dict[str, Any] = None, 
                                error: str = None):
        """记录执行历史"""
        try:
            # 创建执行结果记录
            execution_result = ToolExecutionResult(
                tool_name=tool_name,
                success=success,
                execution_time=execution_time,
                error=error,
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "context": context or {}
                }
            )
            
            # 添加到历史记录
            self.execution_history.append(execution_result)
            
            # 限制历史记录大小
            if len(self.execution_history) > 1000:
                self.execution_history = self.execution_history[-1000:]
            
            # 更新统计信息
            self._update_execution_stats(tool_name, success, execution_time)
            
        except Exception as e:
            logger.error(f"记录执行历史失败: {e}")
    
    def _update_execution_stats(self, tool_name: str, success: bool, execution_time: float):
        """更新执行统计"""
        if tool_name not in self.execution_stats:
            self.execution_stats[tool_name] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_execution_time": 0.0,
                "average_execution_time": 0.0,
                "last_called": None
            }
        
        stats = self.execution_stats[tool_name]
        stats["total_calls"] += 1
        stats["total_execution_time"] += execution_time
        stats["average_execution_time"] = stats["total_execution_time"] / stats["total_calls"]
        stats["last_called"] = datetime.now().isoformat()
        
        if success:
            stats["successful_calls"] += 1
        else:
            stats["failed_calls"] += 1
    
    def get_execution_history(self, tool_name: str = None, limit: int = 100) -> List[ToolExecutionResult]:
        """获取执行历史"""
        if tool_name:
            filtered_history = [
                record for record in self.execution_history 
                if record.tool_name == tool_name
            ]
            return filtered_history[-limit:]
        else:
            return self.execution_history[-limit:]
    
    def get_execution_stats(self, tool_name: str = None) -> Dict[str, Any]:
        """获取执行统计"""
        if tool_name:
            return self.execution_stats.get(tool_name, {})
        else:
            return {
                "total_tools": len(self.execution_stats),
                "total_calls": sum(stats["total_calls"] for stats in self.execution_stats.values()),
                "successful_calls": sum(stats["successful_calls"] for stats in self.execution_stats.values()),
                "failed_calls": sum(stats["failed_calls"] for stats in self.execution_stats.values()),
                "tools_stats": self.execution_stats
            }
    
    def clear_execution_history(self):
        """清空执行历史"""
        self.execution_history.clear()
        self.execution_stats.clear()
        logger.info("执行历史已清空")

