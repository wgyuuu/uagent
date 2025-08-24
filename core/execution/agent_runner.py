"""
Agent Runner

Agent运行引擎 - 管理单轮Agent推理和执行
"""

import asyncio
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass
import structlog

from core.execution.tool_manager import UnifiedToolManager
from tools.llm.llm_manager import LLMManager

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
    
    def __init__(self, tool_manager: UnifiedToolManager):
        # 直接使用模块级函数获取LLM实例
        from tools.llm import get_llm_for_scene
        self.llm = get_llm_for_scene("sub_agent")
        self.tool_manager = tool_manager
    
    async def run_iteration(self, agent_env: AgentEnvironment, iteration: int) -> IterationResult:
        """运行一轮Agent推理"""
        
        try:
            logger.info(f"开始第 {iteration} 轮Agent推理")
            
            # 1. 构建当前轮次的提示词
            current_prompt = await self._build_iteration_prompt(agent_env, iteration)
            
            # 2. 调用LLM进行推理
            # 构建完整的提示词
            full_prompt = self._build_full_prompt(current_prompt, agent_env)
            
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
                prompt=current_prompt,
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
    
    async def _build_iteration_prompt(self, agent_env: AgentEnvironment, iteration: int) -> str:
        """构建当前轮次的提示词"""
        
        # 基础提示词
        base_prompt = agent_env.prompt
        
        # 添加迭代信息
        iteration_info = f"""
## 当前执行状态
- 执行轮次: 第 {iteration} 轮
- 可用工具: {', '.join(agent_env.available_tools)}
- 上下文大小: {len(str(agent_env.context))} 字符

## 执行指导
请基于当前上下文和可用工具，执行你的任务。如果任务完成，请明确说明完成状态和交付物。
如果任务未完成，请说明下一步计划和所需信息。

请开始执行。
        """
        
        return base_prompt + iteration_info
    
    def _build_full_prompt(self, base_prompt: str, agent_env: AgentEnvironment) -> str:
        """构建完整的提示词，包含上下文和工具信息"""
        
        # 构建上下文摘要
        context_summary = self._build_context_summary(agent_env.context)
        
        # 构建工具信息
        tools_info = self._build_tools_info(agent_env.available_tools)
        
        # 组装完整提示词
        full_prompt = f"""
{base_prompt}

## 执行上下文
{context_summary}

## 可用工具
{tools_info}

## 重要提醒
请使用可用的工具来完成任务，并在响应中明确说明：
1. 你计划使用哪些工具
2. 每个工具的具体用途
3. 执行结果和下一步计划
        """
        
        return full_prompt
    
    def _build_context_summary(self, context: Any) -> str:
        """构建上下文摘要"""
        
        if not context:
            return "无上下文信息"
        
        try:
            # 尝试提取关键信息
            if hasattr(context, 'isolated_context'):
                isolated = context.isolated_context
                if hasattr(isolated, 'sections'):
                    sections = isolated.sections
                    summary = []
                    for section_name, content in sections.items():
                        if content and content.strip():
                            summary.append(f"### {section_name}\n{content[:200]}{'...' if len(content) > 200 else ''}")
                    return "\n\n".join(summary)
            
            # 降级处理
            context_str = str(context)
            return context_str[:500] + "..." if len(context_str) > 500 else context_str
            
        except Exception as e:
            return f"上下文解析失败: {str(e)}"
    
    def _build_tools_info(self, available_tools: List[str]) -> str:
        """构建工具信息"""
        
        if not available_tools:
            return "当前没有可用的工具"
        
        tools_info = []
        for tool in available_tools:
            tools_info.append(f"- **{tool}**: 可用于相关操作")
        
        return "\n".join(tools_info)
    
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
        
        # 这里应该实现更智能的工具调用解析
        # 暂时使用简单的关键词匹配
        if "file_operations" in llm_response.lower():
            tool_calls.append(ToolCall(
                name="file_operations",
                arguments={"action": "read", "path": "example.txt"},
                description="执行文件操作"
            ))
        
        if "code_analysis" in llm_response.lower():
            tool_calls.append(ToolCall(
                name="code_analysis",
                arguments={"action": "analyze", "target": "current_code"},
                description="执行代码分析"
            ))
        
        logger.info(f"解析到 {len(tool_calls)} 个工具调用")
        return tool_calls
    
    async def _execute_tools_parallel(self, tool_calls: List[ToolCall], agent_env: AgentEnvironment) -> List[ToolResult]:
        """并行执行工具调用"""
        
        if not tool_calls:
            return []
        
        logger.info(f"开始并行执行 {len(tool_calls)} 个工具")
        
        # 分析工具调用的并发安全性
        safe_tools, unsafe_tools = self._categorize_tools_by_safety(tool_calls)
        
        # 并行执行安全工具
        safe_results = []
        if safe_tools:
            safe_tasks = [
                self._execute_single_tool(tool_call, agent_env) 
                for tool_call in safe_tools
            ]
            safe_results = await asyncio.gather(*safe_tasks, return_exceptions=True)
            
            # 处理异常结果
            safe_results = [
                result if not isinstance(result, Exception) 
                else ToolResult(
                    tool_call=tool_call,
                    success=False,
                    error=str(result)
                )
                for result, tool_call in zip(safe_results, safe_tools)
            ]
        
        # 顺序执行不安全工具
        unsafe_results = []
        for tool_call in unsafe_tools:
            try:
                result = await self._execute_single_tool(tool_call, agent_env)
                unsafe_results.append(result)
            except Exception as e:
                logger.error(f"工具 {tool_call.name} 执行失败: {e}")
                unsafe_results.append(ToolResult(
                    tool_call=tool_call,
                    success=False,
                    error=str(e)
                ))
        
        # 合并结果，保持原始顺序
        all_results = []
        safe_idx = 0
        unsafe_idx = 0
        
        for tool_call in tool_calls:
            if tool_call in safe_tools:
                all_results.append(safe_results[safe_idx])
                safe_idx += 1
            else:
                all_results.append(unsafe_results[unsafe_idx])
                unsafe_idx += 1
        
        logger.info(f"工具执行完成，成功: {sum(1 for r in all_results if r.success)}/{len(all_results)}")
        return all_results
    
    def _categorize_tools_by_safety(self, tool_calls: List[ToolCall]) -> tuple[List[ToolCall], List[ToolCall]]:
        """按安全性分类工具调用"""
        
        safe_tools = []
        unsafe_tools = []
        
        for tool_call in tool_calls:
            # 这里应该根据工具配置判断并发安全性
            # 暂时将读取类操作视为安全，写入类操作视为不安全
            if tool_call.name in ["file_operations", "code_analysis"]:
                safe_tools.append(tool_call)
            else:
                unsafe_tools.append(tool_call)
        
        return safe_tools, unsafe_tools
    
    async def _execute_single_tool(self, tool_call: ToolCall, agent_env: AgentEnvironment) -> ToolResult:
        """执行单个工具"""
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"执行工具: {tool_call.name}")
            
            # 这里应该调用实际的工具管理器
            # 暂时模拟工具执行
            await asyncio.sleep(0.1)  # 模拟执行时间
            
            # 模拟工具输出
            output = f"工具 {tool_call.name} 执行结果: {tool_call.arguments}"
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            return ToolResult(
                tool_call=tool_call,
                success=True,
                output=output,
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
        
        return CompletionAnalysis(
            is_completed=is_completed,
            completion_reason=completion_reason,
            confidence_score=0.8 if is_completed else 0.6,
            next_actions=next_actions,
            quality_indicators={
                "tool_success_rate": sum(1 for r in tool_results if r.success) / len(tool_results) if tool_results else 0,
                "execution_efficiency": len(tool_results) > 0,
                "context_quality": agent_env.quality_score
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
