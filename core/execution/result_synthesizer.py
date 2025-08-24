"""
Result Synthesizer

结果合成器 - 整合多轮执行结果
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import structlog

from models.base import ExecutionContext
from models.roles import RoleConfig
from .role_executor import IterationResult

logger = structlog.get_logger(__name__)

@dataclass
class SynthesizedResult:
    """合成结果"""
    role: str
    execution_summary: Dict[str, Any]
    key_information: Dict[str, Any]
    quality_assessment: Dict[str, Any]
    deliverables: Dict[str, Any]
    handoff_information: Dict[str, Any]
    total_iterations: int
    completion_status: bool

class ResultSynthesizer:
    """结果合成器 - 整合多轮执行结果"""
    
    def __init__(self):
        """初始化结果合成器"""
        pass
    
    async def synthesize(self, 
                        execution_results: List[IterationResult],
                        role_config: RoleConfig,
                        context: ExecutionContext) -> SynthesizedResult:
        """合成多轮执行结果"""
        
        try:
            logger.info(f"开始合成角色 {role_config.name} 的执行结果")
            
            # 1. 分析执行历史
            execution_analysis = await self._analyze_execution_history(execution_results)
            
            # 2. 提取关键信息
            key_information = await self._extract_key_information(execution_results, role_config)
            
            # 3. 评估完成质量
            quality_assessment = await self._assess_completion_quality(
                execution_results, role_config
            )
            
            # 4. 生成交付物摘要
            deliverables_summary = await self._generate_deliverables_summary(
                execution_results, role_config
            )
            
            # 5. 生成交接信息
            handoff_information = await self._generate_handoff_information(
                execution_results, role_config, context
            )
            
            # 6. 构建最终结果
            synthesized_result = SynthesizedResult(
                role=role_config.name,
                execution_summary=execution_analysis,
                key_information=key_information,
                quality_assessment=quality_assessment,
                deliverables=deliverables_summary,
                handoff_information=handoff_information,
                total_iterations=len(execution_results),
                completion_status=quality_assessment.get("is_completed", False)
            )
            
            logger.info(f"角色 {role_config.name} 结果合成完成")
            return synthesized_result
            
        except Exception as e:
            logger.error(f"结果合成失败: {e}")
            return await self._create_fallback_result(execution_results, e, role_config)
    
    async def _analyze_execution_history(self, execution_results: List[IterationResult]) -> Dict[str, Any]:
        """分析执行历史"""
        
        if not execution_results:
            return {"message": "无执行结果"}
        
        # 统计基本信息
        total_iterations = len(execution_results)
        completed_iterations = sum(1 for r in execution_results if r.is_completed)
        failed_iterations = total_iterations - completed_iterations
        
        # 分析工具使用情况
        tool_usage_stats = {}
        total_tool_calls = 0
        successful_tool_calls = 0
        
        for result in execution_results:
            if result.tool_calls:
                total_tool_calls += len(result.tool_calls)
                successful_tool_calls += sum(1 for t in result.tool_results if hasattr(t, 'success') and t.success)
                
                for tool_call in result.tool_calls:
                    tool_name = tool_call.name if hasattr(tool_call, 'name') else 'unknown'
                    if tool_name not in tool_usage_stats:
                        tool_usage_stats[tool_name] = 0
                    tool_usage_stats[tool_name] += 1
        
        # 分析执行趋势
        execution_trend = self._analyze_execution_trend(execution_results)
        
        return {
            "total_iterations": total_iterations,
            "completed_iterations": completed_iterations,
            "failed_iterations": failed_iterations,
            "completion_rate": completed_iterations / total_iterations if total_iterations > 0 else 0,
            "tool_usage": {
                "total_calls": total_tool_calls,
                "successful_calls": successful_tool_calls,
                "success_rate": successful_tool_calls / total_tool_calls if total_tool_calls > 0 else 0,
                "tool_distribution": tool_usage_stats
            },
            "execution_trend": execution_trend,
            "last_iteration": execution_results[-1].iteration if execution_results else 0
        }
    
    def _analyze_execution_trend(self, execution_results: List[IterationResult]) -> Dict[str, Any]:
        """分析执行趋势"""
        
        if len(execution_results) < 2:
            return {"message": "执行轮次不足，无法分析趋势"}
        
        # 分析质量变化趋势
        quality_trend = []
        for result in execution_results:
            if hasattr(result, 'completion_analysis') and result.completion_analysis:
                quality = getattr(result.completion_analysis, 'confidence_score', 0.0)
                quality_trend.append(quality)
        
        # 分析工具使用趋势
        tool_trend = []
        for result in execution_results:
            tool_count = len(result.tool_calls) if result.tool_calls else 0
            tool_trend.append(tool_count)
        
        # 判断趋势方向
        def calculate_trend(values):
            if len(values) < 2:
                return "stable"
            
            # 计算变化率
            changes = [values[i] - values[i-1] for i in range(1, len(values))]
            avg_change = sum(changes) / len(changes)
            
            if avg_change > 0.1:
                return "improving"
            elif avg_change < -0.1:
                return "declining"
            else:
                return "stable"
        
        quality_direction = calculate_trend(quality_trend)
        tool_direction = calculate_trend(tool_trend)
        
        return {
            "quality_trend": {
                "values": quality_trend,
                "direction": quality_direction,
                "improvement": quality_trend[-1] - quality_trend[0] if quality_trend else 0
            },
            "tool_usage_trend": {
                "values": tool_trend,
                "direction": tool_direction,
                "average_tools_per_iteration": sum(tool_trend) / len(tool_trend) if tool_trend else 0
            }
        }
    
    async def _extract_key_information(self, execution_results: List[IterationResult], role_config: RoleConfig) -> Dict[str, Any]:
        """提取关键信息"""
        
        key_info = {
            "role_capabilities": [],
            "technical_decisions": [],
            "problem_solutions": [],
            "user_interactions": [],
            "outputs_generated": []
        }
        
        for result in execution_results:
            # 提取技术决策
            if result.llm_response:
                response_lower = result.llm_response.lower()
                
                # 识别技术决策关键词
                tech_keywords = ["决定", "选择", "采用", "使用", "implement", "choose", "adopt"]
                if any(keyword in response_lower for keyword in tech_keywords):
                    key_info["technical_decisions"].append({
                        "iteration": result.iteration,
                        "content": result.llm_response[:200] + "..." if len(result.llm_response) > 200 else result.llm_response
                    })
                
                # 识别问题解决方案
                solution_keywords = ["解决", "修复", "优化", "solve", "fix", "optimize"]
                if any(keyword in response_lower for keyword in solution_keywords):
                    key_info["problem_solutions"].append({
                        "iteration": result.iteration,
                        "content": result.llm_response[:200] + "..." if len(result.llm_response) > 200 else result.llm_response
                    })
            
            # 提取工具执行结果
            if result.tool_results:
                for tool_result in result.tool_results:
                    if hasattr(tool_result, 'output') and tool_result.output:
                        key_info["outputs_generated"].append({
                            "iteration": result.iteration,
                            "tool": getattr(tool_result.tool_call, 'name', 'unknown') if hasattr(tool_result, 'tool_call') else 'unknown',
                            "output": str(tool_result.output)[:200] + "..." if len(str(tool_result.output)) > 200 else str(tool_result.output)
                        })
        
        return key_info
    
    async def _assess_completion_quality(self, execution_results: List[IterationResult], role_config: RoleConfig) -> Dict[str, Any]:
        """评估完成质量"""
        
        if not execution_results:
            return {"is_completed": False, "quality_score": 0.0, "reason": "无执行结果"}
        
        # 检查完成状态
        last_result = execution_results[-1]
        is_completed = last_result.is_completed
        
        # 计算质量分数
        quality_scores = []
        for result in execution_results:
            if hasattr(result, 'completion_analysis') and result.completion_analysis:
                quality = getattr(result.completion_analysis, 'confidence_score', 0.0)
                quality_scores.append(quality)
        
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        # 评估完成质量
        completion_quality = self._evaluate_completion_quality(execution_results, role_config)
        
        return {
            "is_completed": is_completed,
            "quality_score": avg_quality,
            "completion_quality": completion_quality,
            "quality_trend": "improving" if len(quality_scores) > 1 and quality_scores[-1] > quality_scores[0] else "stable",
            "confidence_level": self._get_confidence_level(avg_quality)
        }
    
    def _evaluate_completion_quality(self, execution_results: List[IterationResult], role_config: RoleConfig) -> Dict[str, Any]:
        """评估完成质量"""
        
        # 基于角色类型评估质量
        role_type = role_config.category if hasattr(role_config, 'category') else "unknown"
        
        quality_metrics = {
            "task_completion": 0.0,
            "output_quality": 0.0,
            "tool_usage_efficiency": 0.0,
            "execution_efficiency": 0.0
        }
        
        # 任务完成度
        completed_count = sum(1 for r in execution_results if r.is_completed)
        quality_metrics["task_completion"] = completed_count / len(execution_results)
        
        # 输出质量（基于工具执行成功率）
        total_tools = sum(len(r.tool_calls) for r in execution_results if r.tool_calls)
        successful_tools = sum(
            sum(1 for t in r.tool_results if hasattr(t, 'success') and t.success)
            for r in execution_results if r.tool_results
        )
        quality_metrics["output_quality"] = successful_tools / total_tools if total_tools > 0 else 0.0
        
        # 工具使用效率
        if total_tools > 0:
            quality_metrics["tool_usage_efficiency"] = min(1.0, total_tools / len(execution_results))
        
        # 执行效率（基于迭代次数）
        optimal_iterations = self._get_optimal_iterations_for_role(role_type)
        actual_iterations = len(execution_results)
        quality_metrics["execution_efficiency"] = max(0.0, 1.0 - (actual_iterations - optimal_iterations) / optimal_iterations)
        
        return quality_metrics
    
    def _get_optimal_iterations_for_role(self, role_type: str) -> int:
        """获取角色的最优迭代次数"""
        
        optimal_iterations = {
            "software_development": 5,
            "data_analysis": 4,
            "content_creation": 3,
            "information_processing": 4,
            "quality_assurance": 3,
            "project_management": 6
        }
        
        return optimal_iterations.get(role_type, 5)
    
    def _get_confidence_level(self, quality_score: float) -> str:
        """获取置信度级别"""
        
        if quality_score >= 0.9:
            return "very_high"
        elif quality_score >= 0.8:
            return "high"
        elif quality_score >= 0.7:
            return "medium"
        elif quality_score >= 0.6:
            return "low"
        else:
            return "very_low"
    
    async def _generate_deliverables_summary(self, execution_results: List[IterationResult], role_config: RoleConfig) -> Dict[str, Any]:
        """生成交付物摘要"""
        
        deliverables = {
            "code_outputs": [],
            "documentation": [],
            "analysis_reports": [],
            "configuration_files": [],
            "test_results": []
        }
        
        # 分析每轮执行的输出
        for result in execution_results:
            if result.tool_results:
                for tool_result in result.tool_results:
                    if hasattr(tool_result, 'output') and tool_result.output:
                        output_str = str(tool_result.output)
                        
                        # 分类输出类型
                        if any(keyword in output_str.lower() for keyword in ["代码", "code", "函数", "function"]):
                            deliverables["code_outputs"].append({
                                "iteration": result.iteration,
                                "content": output_str[:300] + "..." if len(output_str) > 300 else output_str
                            })
                        elif any(keyword in output_str.lower() for keyword in ["文档", "document", "说明", "description"]):
                            deliverables["documentation"].append({
                                "iteration": result.iteration,
                                "content": output_str[:300] + "..." if len(output_str) > 300 else output_str
                            })
                        elif any(keyword in output_str.lower() for keyword in ["分析", "analysis", "报告", "report"]):
                            deliverables["analysis_reports"].append({
                                "iteration": result.iteration,
                                "content": output_str[:300] + "..." if len(output_str) > 300 else output_str
                            })
        
        return deliverables
    
    async def _generate_handoff_information(self, 
                                          execution_results: List[IterationResult],
                                          role_config: RoleConfig,
                                          context: ExecutionContext) -> Dict[str, Any]:
        """生成交接信息 - 参考Claude Code的核心提示词"""
        
        # 使用Claude Code的8段式总结思想
        handoff_prompt = f"""
我需要总结当前所有工作内容，后续将由其他开发者接手继续开发。

请基于以下执行历史，生成详细的交接总结：

## 执行概况
- 角色: {role_config.name}
- 总执行轮次: {len(execution_results)}
- 完成状态: {'已完成' if any(r.is_completed for r in execution_results) else '未完成'}

## 执行历史摘要
{self._format_execution_history_for_handoff(execution_results)}

## 原始任务
{getattr(context, 'task_description', '未提供任务描述')}

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
                
        #         return {
        #             "summary": response,
        #             "format": "8_segment_summary",
        #             "generated_at": datetime.now().isoformat(),
        #             "method": "llm_generated"
        #         }
        #     except Exception as e:
        #         logger.error(f"LLM生成交接总结失败: {e}")
        
        # 否则返回手动生成的总结
        return {
            "summary": self._generate_manual_handoff_summary(execution_results, role_config, context),
            "format": "8_segment_summary",
            "generated_at": datetime.now().isoformat(),
            "method": "manual_generated"
        }
    
    def _format_execution_history_for_handoff(self, execution_results: List[IterationResult]) -> str:
        """格式化执行历史用于交接"""
        
        if not execution_results:
            return "无执行历史"
        
        formatted = []
        for result in execution_results:
            formatted.append(f"### 第 {result.iteration} 轮")
            formatted.append(f"**状态**: {'完成' if result.is_completed else '进行中'}")
            formatted.append(f"**工具调用**: {len(result.tool_calls) if result.tool_calls else 0} 个")
            formatted.append(f"**响应摘要**: {result.llm_response[:100] + '...' if len(result.llm_response) > 100 else result.llm_response}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def _generate_manual_handoff_summary(self, 
                                       execution_results: List[IterationResult],
                                       role_config: RoleConfig,
                                       context: ExecutionContext) -> str:
        """手动生成交接总结"""
        
        summary = f"""
# 工作交接总结

## 执行概况
- **角色**: {role_config.name}
- **总执行轮次**: {len(execution_results)}
- **完成状态**: {'已完成' if any(r.is_completed for r in execution_results) else '未完成'}
- **原始任务**: {getattr(context, 'task_description', '未提供任务描述')}

## 执行历史
"""
        
        for result in execution_results:
            summary += f"\n### 第 {result.iteration} 轮执行\n"
            summary += f"- 状态: {'完成' if result.is_completed else '进行中'}\n"
            summary += f"- 工具调用: {len(result.tool_calls) if result.tool_calls else 0} 个\n"
            if result.llm_response:
                summary += f"- 响应摘要: {result.llm_response[:200] + '...' if len(result.llm_response) > 200 else result.llm_response}\n"
        
        summary += """
## 交接要点
1. 请仔细阅读上述执行历史
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
    
    async def _create_fallback_result(self, 
                                    execution_results: List[IterationResult],
                                    error: Exception,
                                    role_config: RoleConfig) -> SynthesizedResult:
        """创建降级结果"""
        
        logger.error(f"创建降级结果: {error}")
        
        return SynthesizedResult(
            role=role_config.name,
            execution_summary={"error": str(error)},
            key_information={},
            quality_assessment={"is_completed": False, "quality_score": 0.0},
            deliverables={},
            handoff_information={"summary": f"执行过程中发生错误: {str(error)}"},
            total_iterations=len(execution_results),
            completion_status=False
        )
