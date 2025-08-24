"""
Role Executor

角色执行器核心 - 每个角色都是一个完整的Agent运行过程
"""

import asyncio
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
import structlog
import traceback

from core.execution.prompt_manager import PromptManager
from core.execution.tool_manager import UnifiedToolManager
from models.base import (
    RoleResult, 
    generate_id,
    ExecutionConfig,
    AgentEnvironment,
    ExecutionContext,
    IterationResult
)
from models.roles import RoleConfig
from .agent_runner import AgentRunner
from .execution_controller import ExecutionController
from .result_synthesizer import ResultSynthesizer

logger = structlog.get_logger(__name__)

class RoleExecutor:
    """角色执行器 - 每个角色都是一个完整的Agent"""
    
    def __init__(self, 
                 tool_manager: UnifiedToolManager,
                 prompt_manager: PromptManager,
                 execution_config: ExecutionConfig = None):
        
        self.tool_manager = tool_manager
        self.prompt_manager = prompt_manager
        self.config = execution_config or ExecutionConfig()
        
        # 核心组件
        self.agent_runner = AgentRunner(tool_manager)
        self.execution_controller = ExecutionController(self.config)
        self.result_synthesizer = ResultSynthesizer()
        
        logger.info(f"角色执行器初始化完成，配置: {self.config}")
    
    async def execute_role(self, role: str, context: ExecutionContext) -> RoleResult:
        """执行角色任务 - 完整的Agent运行过程"""
        
        execution_id = f"exec_{generate_id()}"
        start_time = datetime.now()
        
        try:
            logger.info(f"开始执行角色 {role}, 执行ID: {execution_id}")
            
            # 1. 获取角色配置和提示词
            role_config = await self._get_role_config(role)
            role_prompt = await self.prompt_manager.build_role_prompt(role, role_config, context)
            
            # 2. 创建Agent运行环境
            agent_env = await self._create_agent_environment(role, context, role_prompt)
            
            # 3. 执行Agent运行循环
            execution_results = []
            iteration_count = 0
            
            while iteration_count < self.config.max_iterations:
                iteration_count += 1
                logger.info(f"角色 {role} 第 {iteration_count} 轮执行")
                
                # 检查执行控制条件
                if not self.execution_controller.can_continue(iteration_count, agent_env):
                    logger.info(f"角色 {role} 执行控制条件不满足，停止执行")
                    break
                
                # 执行一轮Agent推理
                iteration_result = await self.agent_runner.run_iteration(
                    agent_env, iteration_count
                )
                
                execution_results.append(iteration_result)
                
                # 检查是否完成
                if iteration_result.is_completed:
                    logger.info(f"角色 {role} 在第 {iteration_count} 轮完成")
                    break
                
                # 更新执行环境
                agent_env = await self._update_agent_environment(agent_env, iteration_result)
                
                # 检查上下文是否需要压缩
                if self._should_compress_context(agent_env):
                    await self._compress_context(agent_env)
            
            # 4. 合成最终结果
            final_result = await self.result_synthesizer.synthesize(
                execution_results, role_config, context
            )
            
            # 5. 生成角色结果
            role_result = await self._generate_role_result(
                execution_id, role, final_result, start_time, iteration_count
            )
            
            logger.info(f"角色 {role} 执行完成，共 {iteration_count} 轮")
            return role_result
            
        except Exception as e:
            logger.error(f"角色 {role} 执行失败: {e} 堆栈信息: {traceback.format_exc()}")
            return await self._handle_execution_error(role, context, e, execution_id, start_time)
    
    async def _get_role_config(self, role: str) -> RoleConfig:
        """获取角色配置"""
        # 这里应该从角色配置系统获取
        # 暂时返回默认配置
        return RoleConfig(
            name=role,
            display_name=role,
            description=f"专业{role}角色",
            category="software_development",
            capabilities=None,
            dependencies=None,
            prompt_template="",
            system_prompts={},
            behavior_rules=[],
            max_execution_time=3600,
            retry_attempts=3,
            resource_limits={}
        )
    
    async def _create_agent_environment(self, role: str, context: ExecutionContext, role_prompt: str) -> AgentEnvironment:
        """创建Agent运行环境"""
        
        # 获取可用工具
        available_tools = await self._get_available_tools(role, context)
        
        return AgentEnvironment(
            role=role,
            context=context,
            available_tools=available_tools,
            prompt=role_prompt
        )
    
    async def _get_available_tools(self, role: str, context: ExecutionContext) -> List[str]:
        """获取角色可用的工具"""
        # 这里应该根据角色配置和权限获取可用工具
        # 暂时返回所有工具
        return ["file_operations", "code_analysis", "testing_tools", "git_operations"]
    
    async def _update_agent_environment(self, agent_env: AgentEnvironment, iteration_result: IterationResult) -> AgentEnvironment:
        """更新Agent运行环境"""
        
        agent_env.iteration_count = iteration_result.iteration
        agent_env.last_response = iteration_result.llm_response
        
        # 更新上下文
        if iteration_result.tool_results:
            # 将工具执行结果添加到上下文
            for tool_result in iteration_result.tool_results:
                if hasattr(tool_result, 'output') and tool_result.output:
                    # 这里应该更新8段式上下文
                    pass
        
        return agent_env
    
    def _should_compress_context(self, agent_env: AgentEnvironment) -> bool:
        """检查是否需要压缩上下文"""
        # 简单的上下文大小检查
        context_size = len(str(agent_env.context))
        return context_size > 5000  # 可配置的阈值
    
    async def _compress_context(self, agent_env: AgentEnvironment):
        """压缩上下文"""
        logger.info(f"压缩角色 {agent_env.role} 的上下文")
        # 这里应该调用上下文压缩器
        # 暂时只是记录日志
    
    async def _generate_role_result(self, 
                                  execution_id: str,
                                  role: str, 
                                  final_result: Any, 
                                  start_time: datetime,
                                  iteration_count: int) -> RoleResult:
        """生成角色结果"""
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        return RoleResult(
            execution_id=execution_id,
            role=role,
            task_id=execution_id,
            status="COMPLETED",
            outputs={
                "status": "completed",
                "message": f"角色 {role} 执行完成",
                "iterations": iteration_count,
                "execution_time": execution_time
            },
            deliverables={
                "summary": final_result.get("summary", ""),
                "key_information": final_result.get("key_information", {}),
                "deliverables": final_result.get("deliverables", {})
            },
            quality_score=final_result.get("quality_score", 0.8),
            completeness_score=final_result.get("completeness_score", 0.9)
        )
    
    async def _handle_execution_error(self, 
                                    role: str, 
                                    context: ExecutionContext, 
                                    error: Exception,
                                    execution_id: str,
                                    start_time: datetime) -> RoleResult:
        """处理执行错误"""
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        logger.error(f"角色 {role} 执行错误: {error}")
        
        return RoleResult(
            execution_id=execution_id,
            role=role,
            task_id=execution_id,
            status="FAILED",
            outputs={
                "status": "failed",
                "message": f"角色 {role} 执行失败: {str(error)}",
                "execution_time": execution_time
            },
            deliverables={
                "error": str(error),
                "error_type": type(error).__name__
            },
            quality_score=0.0,
            completeness_score=0.0
        )
