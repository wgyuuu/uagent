"""
Agent Runner

Agent运行引擎 - 管理单轮Agent推理和执行
"""

import asyncio
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass
import structlog

from core.execution.mcptools import get_tool_manager
from tools.llm.llm_manager import LLMManager
from core.prompt_manager import create_prompt_manager, create_build_request
from models.base import ExecutionState

from .role_executor import AgentEnvironment, IterationResult

logger = structlog.get_logger(__name__)

@dataclass
class ToolCall:
    """工具调用"""
    name: str
    arguments: Dict[str, Any]
    description: str

@dataclass
class ToolResult:
    """工具执行结果"""
    tool_call: ToolCall
    success: bool
    output: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0

@dataclass
class CompletionAnalysis:
    """完成状态分析"""
    is_completed: bool
    completion_reason: str
    confidence_score: float
    next_actions: List[str]
    quality_indicators: Dict[str, Any]

class AgentRunner:
    """Agent运行引擎 - 管理单轮Agent推理和执行"""
    
    def __init__(self):
        # LLM实例
        from tools.llm import get_llm_for_scene
        self.llm = get_llm_for_scene("sub_agent")
        
        # 工具管理器
        self.tool_manager = get_tool_manager()
        
        # 使用独立的prompt管理器
        self.prompt_manager = create_prompt_manager()
        
        # 工具执行统计
        self.tool_execution_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_execution_time": 0.0,
            "tools_used": set()
        }
    
    async def run_iteration(self, agent_env: AgentEnvironment, iteration: int) -> IterationResult:
        """运行一轮Agent推理"""
        
        try:
            logger.info(f"开始第 {iteration} 轮Agent推理")
            
            # 使用独立prompt管理器构建完整提示词
            full_prompt = await self._build_prompt_with_manager(agent_env, iteration)
            
            # 异步调用LLM
            llm_result = await self.llm.ainvoke(full_prompt)
            
            # 提取响应内容
            llm_response = self._extract_llm_response(llm_result)
            
            # 3. 解析LLM响应，提取工具调用
            tool_calls = await self._parse_tool_calls(llm_response)
            
            # 4. 并行执行工具调用
            tool_results = await self._execute_tools_parallel(tool_calls, agent_env)
            
            # 5. 分析执行结果，判断是否完成
            completion_analysis = await self._analyze_completion(tool_results, agent_env)
            
            # 6. 生成迭代结果
            iteration_result = IterationResult(
                iteration=iteration,
                prompt=full_prompt,
                llm_response=llm_response,
                tool_calls=tool_calls,
                tool_results=tool_results,
                completion_analysis=completion_analysis,
                is_completed=completion_analysis.is_completed,
                next_actions=completion_analysis.next_actions
            )
            
            logger.info(f"第 {iteration} 轮Agent推理完成")
            return iteration_result
            
        except Exception as e:
            logger.error(f"Agent迭代 {iteration} 执行失败: {e}")
            return await self._handle_iteration_error(iteration, e)
    
    async def _build_prompt_with_manager(self, agent_env: AgentEnvironment, iteration: int) -> str:
        """使用独立prompt管理器构建完整提示词"""
        
        try:
            # 构建执行状态
            execution_state = ExecutionState(
                iteration=iteration,
                role=agent_env.role,
                iteration_count=agent_env.iteration_count,
                quality_score=agent_env.quality_score,
                last_response=getattr(agent_env, 'last_response', None),
                tool_execution_stats=self.get_tool_execution_stats(),
                successful_tool_calls=self.tool_execution_stats.get('successful_calls', 0),
                failed_tool_calls=self.tool_execution_stats.get('failed_calls', 0)
            )
            
            # 创建prompt构建请求
            build_request = create_build_request(
                role=agent_env.role,
                role_config=getattr(agent_env, 'role_config', None),
                context=agent_env.context,
                execution_state=execution_state,
                available_tools=agent_env.available_tools
            )
            
            # 使用prompt管理器构建完整prompt
            full_prompt = await self.prompt_manager.build_complete_prompt(build_request)
            
            logger.debug(f"使用prompt管理器构建prompt完成，长度: {len(full_prompt)}")
            return full_prompt
            
        except Exception as e:
            raise Exception(f"使用prompt管理器构建prompt失败: {e}")
            
    
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
    
    async def _parse_tool_calls(self, llm_response: str) -> List[ToolCall]:
        """解析LLM响应，提取工具调用"""
        
        tool_calls = []
        
        try:
            # 1. 尝试解析结构化的工具调用（JSON格式）
            structured_calls = await self._parse_structured_tool_calls(llm_response)
            tool_calls.extend(structured_calls)
            
            # 2. 如果没有找到结构化调用，尝试自然语言解析
            if not tool_calls:
                natural_calls = await self._parse_natural_language_tool_calls(llm_response)
                tool_calls.extend(natural_calls)
            
            logger.info(f"解析到 {len(tool_calls)} 个工具调用")
            return tool_calls
            
        except Exception as e:
            logger.error(f"工具调用解析失败: {e}")
            return []
    
    async def _parse_structured_tool_calls(self, llm_response: str) -> List[ToolCall]:
        """解析结构化的工具调用（JSON格式）"""
        import json
        import re
        
        tool_calls = []
        
        # 查找JSON格式的工具调用
        json_pattern = r'```json\s*(\{.*?\})\s*```|```\s*(\{.*?\})\s*```|\{[^{}]*"tool_name"[^{}]*\}'
        matches = re.findall(json_pattern, llm_response, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            try:
                # match可能是元组，取非空的部分
                json_str = match[0] if match[0] else (match[1] if len(match) > 1 and match[1] else match)
                if isinstance(json_str, tuple):
                    json_str = next((item for item in json_str if item), "")
                
                if not json_str:
                    continue
                    
                tool_data = json.loads(json_str)
                
                if isinstance(tool_data, dict) and "tool_name" in tool_data:
                    tool_calls.append(ToolCall(
                        name=tool_data["tool_name"],
                        arguments=tool_data.get("parameters", tool_data.get("arguments", {})),
                        description=tool_data.get("description", f"执行工具: {tool_data['tool_name']}")
                    ))
                elif isinstance(tool_data, list):
                    for item in tool_data:
                        if isinstance(item, dict) and "tool_name" in item:
                            tool_calls.append(ToolCall(
                                name=item["tool_name"],
                                arguments=item.get("parameters", item.get("arguments", {})),
                                description=item.get("description", f"执行工具: {item['tool_name']}")
                            ))
                            
            except json.JSONDecodeError:
                continue
        
        return tool_calls
    
    async def _parse_natural_language_tool_calls(self, llm_response: str) -> List[ToolCall]:
        """解析自然语言中的工具调用"""
        tool_calls = []
        
        # 获取可用工具列表进行智能匹配
        tools_info = await self.tool_manager.get_available_tools()
        available_tools = [tool["name"] for tool in tools_info]
        
        # 基于可用工具进行智能匹配
        response_lower = llm_response.lower()
        
        for tool_name in available_tools:
            tool_lower = tool_name.lower()
            
            # 检查工具名称或相关关键词
            keywords = [tool_lower, tool_lower.replace("_", " ")]
            
            # 添加特定工具的关键词
            if "file" in tool_lower:
                keywords.extend(["文件", "读取", "写入", "file", "read", "write"])
            elif "code" in tool_lower:
                keywords.extend(["代码", "分析", "code", "analyze"])
            elif "text" in tool_lower:
                keywords.extend(["文本", "处理", "text", "process"])
            elif "data" in tool_lower:
                keywords.extend(["数据", "验证", "data", "validate"])
            
            # 检查是否匹配
            if any(keyword in response_lower for keyword in keywords):
                # 尝试提取参数（简单实现）
                arguments = self._extract_tool_arguments(llm_response, tool_name)
                
                tool_calls.append(ToolCall(
                    name=tool_name,
                    arguments=arguments,
                    description=f"基于自然语言解析的工具调用: {tool_name}"
                ))
        
        return tool_calls
    
    def _extract_tool_arguments(self, llm_response: str, tool_name: str) -> Dict[str, Any]:
        """从自然语言中提取工具参数（简单实现）"""
        arguments = {}
        
        # 基于工具类型提取常见参数
        if "file" in tool_name.lower():
            # 文件操作参数
            import re
            
            # 提取文件路径
            path_patterns = [
                r'文件[路径]*[:：]\s*([^\s]+)',
                r'路径[:：]\s*([^\s]+)',
                r'file[path]*[:：]\s*([^\s]+)',
                r'path[:：]\s*([^\s]+)'
            ]
            
            for pattern in path_patterns:
                match = re.search(pattern, llm_response, re.IGNORECASE)
                if match:
                    arguments["path"] = match.group(1)
                    break
            
            # 提取操作类型
            if any(word in llm_response.lower() for word in ["读取", "read", "查看"]):
                arguments["action"] = "read"
            elif any(word in llm_response.lower() for word in ["写入", "write", "创建"]):
                arguments["action"] = "write"
            else:
                arguments["action"] = "read"  # 默认
                
        elif "code" in tool_name.lower():
            # 代码分析参数
            arguments["action"] = "analyze"
            arguments["target"] = "current_code"
            
        elif "text" in tool_name.lower():
            # 文本处理参数
            arguments["action"] = "process"
            
        elif "data" in tool_name.lower():
            # 数据验证参数
            arguments["action"] = "validate"
        
        return arguments
    
    async def _execute_tools_parallel(self, tool_calls: List[ToolCall], agent_env: AgentEnvironment) -> List[ToolResult]:
        """并行执行工具调用"""
        
        if not tool_calls:
            return []
        
        logger.info(f"开始并行执行 {len(tool_calls)} 个工具")
        
        # 使用工具管理器批量执行
        return await self._execute_tools_batch_via_manager(tool_calls, agent_env)
    
    async def _execute_tools_batch_via_manager(self, tool_calls: List[ToolCall], agent_env: AgentEnvironment) -> List[ToolResult]:
        """通过工具管理器批量执行工具"""
        
        # 构建工具调用格式
        batch_calls = []
        for tool_call in tool_calls:
            batch_calls.append({
                "tool_name": tool_call.name,
                "parameters": tool_call.arguments,
                "description": tool_call.description
            })
        
        # 构建执行上下文
        context = {
            "agent_env": agent_env,
            "iteration_context": getattr(agent_env, 'context', {}),
            "available_tools": getattr(agent_env, 'available_tools', [])
        }
        
        # 使用工具管理器批量执行
        tool_execution_results = await self.tool_manager.execute_tools_batch(batch_calls, context)
        
        # 转换结果格式
        results = []
        for i, (tool_call, execution_result) in enumerate(zip(tool_calls, tool_execution_results)):
            results.append(ToolResult(
                tool_call=tool_call,
                success=execution_result.success,
                output=execution_result.result,
                error=execution_result.error,
                execution_time=execution_result.execution_time
            ))
        
        # 更新统计信息
        self._update_tool_execution_stats(results)
        
        logger.info(f"批量工具执行完成，成功: {sum(1 for r in results if r.success)}/{len(results)}")
        return results
    
    
    
    def _update_tool_execution_stats(self, tool_results: List[ToolResult]):
        """更新工具执行统计信息"""
        
        for result in tool_results:
            self.tool_execution_stats["total_calls"] += 1
            self.tool_execution_stats["total_execution_time"] += result.execution_time
            self.tool_execution_stats["tools_used"].add(result.tool_call.name)
            
            if result.success:
                self.tool_execution_stats["successful_calls"] += 1
            else:
                self.tool_execution_stats["failed_calls"] += 1
    
    def get_tool_execution_stats(self) -> Dict[str, Any]:
        """获取工具执行统计信息"""
        
        stats = self.tool_execution_stats.copy()
        stats["tools_used"] = list(stats["tools_used"])  # 转换为列表
        
        # 计算平均执行时间
        if stats["total_calls"] > 0:
            stats["average_execution_time"] = stats["total_execution_time"] / stats["total_calls"]
            stats["success_rate"] = stats["successful_calls"] / stats["total_calls"]
        else:
            stats["average_execution_time"] = 0.0
            stats["success_rate"] = 0.0
        
        return stats
    
    def reset_tool_execution_stats(self):
        """重置工具执行统计信息"""
        
        self.tool_execution_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_execution_time": 0.0,
            "tools_used": set()
        }
    
    async def _execute_single_tool(self, tool_call: ToolCall, agent_env: AgentEnvironment) -> ToolResult:
        """执行单个工具"""
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"执行工具: {tool_call.name}")
            
            # 使用工具管理器执行工具
            context = {
                "agent_env": agent_env,
                "iteration_context": getattr(agent_env, 'context', {}),
                "available_tools": getattr(agent_env, 'available_tools', [])
            }
            
            tool_execution_result = await self.tool_manager.execute_tool(
                tool_name=tool_call.name,
                parameters=tool_call.arguments,
                context=context
            )
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            # 转换为 AgentRunner 的 ToolResult 格式
            return ToolResult(
                tool_call=tool_call,
                success=tool_execution_result.success,
                output=tool_execution_result.result,
                error=tool_execution_result.error,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"工具 {tool_call.name} 执行失败: {e}")
            
            return ToolResult(
                tool_call=tool_call,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    async def _analyze_completion(self, tool_results: List[ToolResult], agent_env: AgentEnvironment) -> CompletionAnalysis:
        """分析执行结果，判断是否完成"""
        
        # 这里应该使用LLM分析完成状态
        # 暂时使用简单的启发式判断
        
        # 检查是否有明确的完成信号
        completion_signals = ["完成", "finished", "done", "任务结束"]
        is_completed = False
        completion_reason = ""
        
        # 检查工具执行结果中是否有完成信号
        for result in tool_results:
            if result.success and result.output:
                output_str = str(result.output).lower()
                for signal in completion_signals:
                    if signal in output_str:
                        is_completed = True
                        completion_reason = f"检测到完成信号: {signal}"
                        break
                if is_completed:
                    break
        
        # 如果没有明确信号，检查是否达到质量要求
        if not is_completed and agent_env.quality_score > 0.8:
            is_completed = True
            completion_reason = "达到质量阈值"
        
        # 生成下一步行动建议
        next_actions = []
        if not is_completed:
            next_actions = [
                "继续执行当前任务",
                "收集更多信息",
                "验证当前结果"
            ]
        else:
            next_actions = [
                "总结执行结果",
                "准备交接信息",
                "完成最终交付"
            ]
        
        # 计算质量指标
        tool_success_rate = sum(1 for r in tool_results if r.success) / len(tool_results) if tool_results else 0
        execution_efficiency = len(tool_results) > 0
        
        # 获取工具执行统计信息
        execution_stats = self.get_tool_execution_stats()
        
        return CompletionAnalysis(
            is_completed=is_completed,
            completion_reason=completion_reason,
            confidence_score=0.8 if is_completed else 0.6,
            next_actions=next_actions,
            quality_indicators={
                "tool_success_rate": tool_success_rate,
                "execution_efficiency": execution_efficiency,
                "context_quality": agent_env.quality_score,
                "total_tools_used": len(execution_stats["tools_used"]),
                "overall_success_rate": execution_stats["success_rate"],
                "average_execution_time": execution_stats["average_execution_time"]
            }
        )
    
    async def _handle_iteration_error(self, iteration: int, error: Exception) -> IterationResult:
        """处理迭代错误"""
        
        logger.error(f"处理迭代 {iteration} 错误: {error}")
        
        return IterationResult(
            iteration=iteration,
            prompt="",
            llm_response="",
            tool_calls=[],
            tool_results=[],
            completion_analysis=CompletionAnalysis(
                is_completed=False,
                completion_reason=f"执行错误: {str(error)}",
                confidence_score=0.0,
                next_actions=["错误恢复", "重新尝试"],
                quality_indicators={}
            ),
            is_completed=False,
            next_actions=["错误恢复", "重新尝试"]
        )
