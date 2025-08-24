"""
Smart Tool Executor

智能工具执行器 - 基于工具特性和上下文智能选择执行策略
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import structlog
from dataclasses import dataclass

# 移除对tool_manager的导入，改为导入底层工具执行器
from tools.mcp import (
    BuiltInMCPServerManager,
    ConfigurableMCPServerManager,
    UserInteractionMCPService
)
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


class SmartToolExecutor:
    """
    智能工具执行器
    
    基于工具特性和上下文智能选择执行策略：
    - 并发安全工具并行执行
    - 有依赖关系的工具按顺序执行
    - 资源密集型工具避免同时执行
    """
    
    def __init__(self, 
                 builtin_manager: BuiltInMCPServerManager,
                 configurable_manager: ConfigurableMCPServerManager,
                 user_interaction: UserInteractionMCPService):
        """初始化智能工具执行器"""
        self.builtin_manager = builtin_manager
        self.configurable_manager = configurable_manager
        self.user_interaction = user_interaction
        self.execution_history: List[Dict[str, Any]] = []
        
        logger.info("智能工具执行器初始化完成")
    
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
            
            # 4. 记录执行历史
            await self._record_execution_history(tool_calls_objects, results, context)
            
            return results
            
        except Exception as e:
            logger.error(f"智能执行工具调用失败: {e}")
            raise
    
    def _convert_to_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[ToolCall]:
        """转换工具调用格式"""
        converted = []
        
        for i, call in enumerate(tool_calls):
            tool_call = ToolCall(
                tool_name=call.get("tool_name", f"unknown_tool_{i}"),
                parameters=call.get("parameters", {}),
                priority=call.get("priority", 1),
                dependencies=call.get("dependencies", []),
                timeout=call.get("timeout", 30),
                retry_count=0,
                max_retries=call.get("max_retries", 3)
            )
            converted.append(tool_call)
        
        return converted
    
    def _analyze_execution_strategy(self, tool_calls: List[ToolCall]) -> ExecutionStrategy:
        """分析执行策略"""
        
        # 检查是否有依赖关系
        has_dependencies = any(call.dependencies for call in tool_calls)
        
        # 检查是否有非并发安全工具
        has_unsafe_tools = False  # 这里需要从工具管理器获取工具信息
        
        # 检查是否有资源密集型工具
        has_resource_intensive = False  # 这里需要分析工具参数
        
        if has_dependencies:
            # 有依赖关系，使用混合策略
            strategy_type = "mixed"
            parallel_tools, sequential_tools = self._separate_by_dependencies(tool_calls)
        elif has_unsafe_tools:
            # 有非并发安全工具，使用串行策略
            strategy_type = "sequential"
            parallel_tools = []
            sequential_tools = [call.tool_name for call in tool_calls]
        else:
            # 所有工具都可以并行执行
            strategy_type = "parallel"
            parallel_tools = [call.tool_name for call in tool_calls]
            sequential_tools = []
        
        # 确定执行顺序
        execution_order = self._determine_execution_order(tool_calls, strategy_type)
        
        return ExecutionStrategy(
            strategy_type=strategy_type,
            parallel_tools=parallel_tools,
            sequential_tools=sequential_tools,
            execution_order=execution_order
        )
    
    def _separate_by_dependencies(self, tool_calls: List[ToolCall]) -> tuple[List[str], List[str]]:
        """根据依赖关系分离工具"""
        # 简单的依赖分析：有依赖的工具放在串行组
        parallel_tools = []
        sequential_tools = []
        
        for call in tool_calls:
            if call.dependencies:
                sequential_tools.append(call.tool_name)
            else:
                parallel_tools.append(call.tool_name)
        
        return parallel_tools, sequential_tools
    
    def _determine_execution_order(self, tool_calls: List[ToolCall], strategy_type: str) -> List[str]:
        """确定执行顺序"""
        if strategy_type == "parallel":
            # 并行执行，顺序不重要
            return [call.tool_name for call in tool_calls]
        elif strategy_type == "sequential":
            # 串行执行，按优先级排序
            sorted_calls = sorted(tool_calls, key=lambda x: x.priority)
            return [call.tool_name for call in sorted_calls]
        else:  # mixed
            # 混合策略，先并行后串行
            parallel_tools = []
            sequential_tools = []
            
            for call in tool_calls:
                if call.dependencies:
                    sequential_tools.append(call.tool_name)
                else:
                    parallel_tools.append(call.tool_name)
            
            # 串行工具按优先级排序
            sequential_calls = [call for call in tool_calls if call.dependencies]
            sorted_sequential = sorted(sequential_calls, key=lambda x: x.priority)
            sequential_tools = [call.tool_name for call in sorted_sequential]
            
            return parallel_tools + sequential_tools
    
    async def _execute_parallel(self, 
                              tool_calls: List[ToolCall], 
                              context: Dict[str, Any]) -> List[ToolResult]:
        """并行执行工具"""
        try:
            # 创建并行任务
            tasks = []
            for call in tool_calls:
                task = self._execute_single_tool(call, context)
                tasks.append(task)
            
            # 等待所有任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # 处理异常
                    processed_results.append(ToolResult(
                        tool_name=tool_calls[i].tool_name,
                        success=False,
                        error=str(result),
                        execution_time=0.0
                    ))
                else:
                    processed_results.append(result)
            
            return processed_results
            
        except Exception as e:
            logger.error(f"并行执行工具失败: {e}")
            raise
    
    async def _execute_sequential(self, 
                                tool_calls: List[ToolCall], 
                                context: Dict[str, Any]) -> List[ToolResult]:
        """串行执行工具"""
        results = []
        
        for call in tool_calls:
            try:
                result = await self._execute_single_tool(call, context)
                results.append(result)
                
                # 如果工具执行失败，可以选择是否继续
                if not result.success:
                    logger.warning(f"工具 {call.tool_name} 执行失败，继续执行下一个工具")
                
            except Exception as e:
                logger.error(f"执行工具 {call.tool_name} 时发生异常: {e}")
                results.append(ToolResult(
                    tool_name=call.tool_name,
                    success=False,
                    error=str(e),
                    execution_time=0.0
                ))
        
        return results
    
    async def _execute_mixed(self, 
                           tool_calls: List[ToolCall], 
                           strategy: ExecutionStrategy,
                           context: Dict[str, Any]) -> List[ToolResult]:
        """混合策略执行工具"""
        results = []
        
        # 1. 先并行执行并发安全工具
        parallel_calls = [call for call in tool_calls if call.tool_name in strategy.parallel_tools]
        if parallel_calls:
            parallel_results = await self._execute_parallel(parallel_calls, context)
            results.extend(parallel_results)
        
        # 2. 再串行执行有依赖的工具
        sequential_calls = [call for call in tool_calls if call.tool_name in strategy.sequential_tools]
        if sequential_calls:
            sequential_results = await self._execute_sequential(sequential_calls, context)
            results.extend(sequential_results)
        
        return results
    
    async def _execute_single_tool(self, 
                                 tool_call: ToolCall, 
                                 context: Dict[str, Any]) -> ToolResult:
        """执行单个工具"""
        start_time = datetime.now()
        
        try:
            # 根据工具名称判断工具类型并选择执行器
            result = await self._execute_tool_by_type(
                tool_call.tool_name,
                tool_call.parameters,
                context
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ToolResult(
                tool_name=tool_call.tool_name,
                success=result.success,
                result=result.result if hasattr(result, 'result') else None,
                error=result.error if hasattr(result, 'error') else None,
                execution_time=execution_time,
                metadata={
                    "parameters": tool_call.parameters,
                    "priority": tool_call.priority,
                    "dependencies": tool_call.dependencies
                }
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 处理重试逻辑
            if tool_call.retry_count < tool_call.max_retries:
                tool_call.retry_count += 1
                logger.warning(f"工具 {tool_call.tool_name} 执行失败，尝试重试 ({tool_call.retry_count}/{tool_call.max_retries})")
                
                # 递归重试
                return await self._execute_single_tool(tool_call, context)
            else:
                logger.error(f"工具 {tool_call.tool_name} 执行失败，已达到最大重试次数: {e}")
                
                return ToolResult(
                    tool_name=tool_call.tool_name,
                    success=False,
                    error=str(e),
                    execution_time=execution_time,
                    metadata={
                        "parameters": tool_call.parameters,
                        "retry_count": tool_call.retry_count
                    }
                )
    
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
            # 尝试从内置工具管理器执行
            try:
                result = await self.builtin_manager.execute_tool(tool_name, parameters)
                return result
            except Exception as e:
                logger.debug(f"工具 {tool_name} 不是内置工具: {e}")
            
            # 尝试从可配置MCP服务执行
            try:
                result = await self.configurable_manager.execute_tool(tool_name, parameters)
                return result
            except Exception as e:
                logger.debug(f"工具 {tool_name} 不是可配置MCP工具: {e}")
            
            # 尝试从用户交互服务执行
            try:
                result = await self.user_interaction.process_interaction(tool_name, parameters)
                return result
            except Exception as e:
                logger.debug(f"工具 {tool_name} 不是用户交互工具: {e}")
            
            # 如果所有执行器都无法执行，抛出异常
            raise ValueError(f"无法找到工具 {tool_name} 的执行器")
            
        except Exception as e:
            logger.error(f"执行工具 {tool_name} 失败: {e}")
            raise
    
    async def _record_execution_history(self, 
                                      tool_calls: List[ToolCall], 
                                      results: List[ToolResult],
                                      context: Dict[str, Any]):
        """记录执行历史"""
        execution_record = {
            "timestamp": datetime.now().isoformat(),
            "tool_calls": [
                {
                    "tool_name": call.tool_name,
                    "parameters": call.parameters,
                    "priority": call.priority,
                    "dependencies": call.dependencies
                }
                for call in tool_calls
            ],
            "results": [
                {
                    "tool_name": result.tool_name,
                    "success": result.success,
                    "execution_time": result.execution_time,
                    "error": result.error
                }
                for result in results
            ],
            "context": context,
            "summary": {
                "total_tools": len(tool_calls),
                "successful_tools": len([r for r in results if r.success]),
                "failed_tools": len([r for r in results if not r.success]),
                "total_execution_time": sum(r.execution_time for r in results)
            }
        }
        
        self.execution_history.append(execution_record)
        
        # 保持历史记录在合理范围内
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]
    
    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return self.execution_history[-limit:] if limit > 0 else self.execution_history
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        if not self.execution_history:
            return {}
        
        total_executions = len(self.execution_history)
        total_tools = sum(record["summary"]["total_tools"] for record in self.execution_history)
        successful_tools = sum(record["summary"]["successful_tools"] for record in self.execution_history)
        failed_tools = sum(record["summary"]["failed_tools"] for record in self.execution_history)
        total_time = sum(record["summary"]["total_execution_time"] for record in self.execution_history)
        
        return {
            "total_executions": total_executions,
            "total_tools_executed": total_tools,
            "successful_tools": successful_tools,
            "failed_tools": failed_tools,
            "success_rate": successful_tools / total_tools if total_tools > 0 else 0,
            "average_execution_time": total_time / total_tools if total_tools > 0 else 0,
            "recent_executions": self.execution_history[-10:] if self.execution_history else []
        }
