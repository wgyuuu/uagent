"""
UAgent API Routes

定义所有API路由端点
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
import structlog
from pydantic import BaseModel

from models.base import Task, WorkflowExecution, RoleResult
from models.workflow import WorkflowDefinition, ExecutionPlan
from core.intelligence import MainAgent
from core.workflow import WorkflowOrchestrator
from tools.mcp import MCPToolRegistry
from api.dto import RoleDefinition, APIRoleRecommendation, CreateTaskRequest, TaskResponse, WorkflowExecutionRequest, RoleRecommendationRequest

logger = structlog.get_logger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/v1", tags=["uagent"])

# 依赖注入
async def get_main_agent() -> MainAgent:
    """获取主Agent实例"""
    # 从main.py中导入全局实例
    from api.main import main_agent
    if main_agent is None:
        raise HTTPException(status_code=503, detail="主Agent未初始化")
    return main_agent

async def get_workflow_orchestrator() -> WorkflowOrchestrator:
    """获取工作流编排器实例"""
    # 从main.py中导入全局实例
    from api.main import workflow_orchestrator
    if workflow_orchestrator is None:
        raise HTTPException(status_code=503, detail="工作流编排器未初始化")
    return workflow_orchestrator

async def get_tool_registry() -> MCPToolRegistry:
    """获取工具注册表实例"""
    # 从main.py中导入全局实例
    from api.main import tool_registry
    if tool_registry is None:
        raise HTTPException(status_code=503, detail="工具注册表未初始化")
    return tool_registry


# 任务管理API
@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    request: CreateTaskRequest,
    background_tasks: BackgroundTasks,
    main_agent: MainAgent = Depends(get_main_agent)
):
    """创建新任务"""
    try:
        logger.info(f"创建任务: {request.title}")
        
        # 创建任务
        task = Task(
            title=request.title,
            description=request.description,
            domain=request.domain,
            complexity=request.complexity,
            expected_output=request.expected_output,
            user_preferences=request.user_preferences or {}
        )
        
        # 分析任务并推荐角色
        background_tasks.add_task(
            main_agent.analyze_task_and_recommend_roles,
            task
        )
        
        return TaskResponse(
            task_id=task.id,
            status="created",
            message="任务创建成功，正在分析任务并推荐角色",
            data={"task": task.dict()}
        )
        
    except Exception as e:
        logger.error(f"创建任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    main_agent: MainAgent = Depends(get_main_agent)
):
    """获取任务详情"""
    try:
        logger.info(f"获取任务: {task_id}")
        
        # 这里应该从数据库获取任务
        # task = await main_agent.get_task(task_id)
        
        # 临时返回
        return TaskResponse(
            task_id=task_id,
            status="not_found",
            message="任务不存在",
            data=None
        )
        
    except Exception as e:
        logger.error(f"获取任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务失败: {str(e)}")


@router.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[str] = None,
    domain: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """获取任务列表"""
    try:
        logger.info(f"获取任务列表: status={status}, domain={domain}")
        
        # 这里应该从数据库获取任务列表
        # tasks = await main_agent.list_tasks(status, domain, limit, offset)
        
        # 临时返回空列表
        return []
        
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


# 角色管理API
@router.get("/roles", response_model=List[RoleDefinition])
async def list_roles(
    domain: Optional[str] = None,
    capability: Optional[str] = None
):
    """获取可用角色列表"""
    try:
        logger.info(f"获取角色列表: domain={domain}, capability={capability}")
        
        # 这里应该从角色注册表获取
        # roles = await role_registry.list_roles(domain, capability)
        
        # 临时返回示例角色
        return [
            RoleDefinition(
                id="coding_expert",
                name="编码专家",
                description="负责代码编写和实现",
                domain="软件开发",
                capabilities=["代码编写", "算法实现", "代码优化"],
                dependencies=[],
                prompt_template="你是一个专业的编码专家..."
            ),
            RoleDefinition(
                id="planner",
                name="方案规划师", 
                description="负责任务分析和方案设计",
                domain="通用",
                capabilities=["任务分析", "方案设计", "架构规划"],
                dependencies=[],
                prompt_template="你是一个专业的方案规划师..."
            )
        ]
        
    except Exception as e:
        logger.error(f"获取角色列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取角色列表失败: {str(e)}")


@router.post("/roles/recommend", response_model=List[APIRoleRecommendation])
async def recommend_roles(
    request: RoleRecommendationRequest,
    main_agent: MainAgent = Depends(get_main_agent)
):
    """获取角色推荐"""
    try:
        logger.info(f"角色推荐请求: {request.task_description}")
        
        # 调用主Agent进行角色推荐
        recommendations = await main_agent.recommend_roles(
            task_description=request.task_description,
            domain=request.domain,
            complexity=request.complexity,
            output_requirements=request.output_requirements
        )
        
        return recommendations
        
    except Exception as e:
        logger.error(f"角色推荐失败: {e}")
        raise HTTPException(status_code=500, detail=f"角色推荐失败: {str(e)}")


# 工作流管理API
@router.post("/workflows/execute", response_model=TaskResponse)
async def execute_workflow(
    request: WorkflowExecutionRequest,
    background_tasks: BackgroundTasks,
    workflow_orchestrator: WorkflowOrchestrator = Depends(get_workflow_orchestrator)
):
    """执行工作流"""
    try:
        logger.info(f"执行工作流: task_id={request.task_id}, roles={request.selected_roles}")
        
        # 创建工作流定义
        workflow_def = WorkflowDefinition(
            task_id=request.task_id,
            roles=request.selected_roles,
            execution_config=request.execution_config or {}
        )
        
        # 在后台执行工作流
        background_tasks.add_task(
            workflow_orchestrator.execute_workflow,
            workflow_def
        )
        
        return TaskResponse(
            task_id=request.task_id,
            status="executing",
            message="工作流开始执行",
            data={"workflow": workflow_def.dict()}
        )
        
    except Exception as e:
        logger.error(f"执行工作流失败: {e}")
        raise HTTPException(status_code=500, detail=f"执行工作流失败: {str(e)}")


@router.get("/workflows/{workflow_id}", response_model=Dict[str, Any])
async def get_workflow_status(
    workflow_id: str,
    workflow_orchestrator: WorkflowOrchestrator = Depends(get_workflow_orchestrator)
):
    """获取工作流状态"""
    try:
        logger.info(f"获取工作流状态: {workflow_id}")
        
        # 获取工作流状态
        # status = await workflow_orchestrator.get_workflow_status(workflow_id)
        
        # 临时返回
        return {
            "workflow_id": workflow_id,
            "status": "unknown",
            "message": "工作流状态未知"
        }
        
    except Exception as e:
        logger.error(f"获取工作流状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取工作流状态失败: {str(e)}")


@router.post("/workflows/{workflow_id}/pause")
async def pause_workflow(
    workflow_id: str,
    workflow_orchestrator: WorkflowOrchestrator = Depends(get_workflow_orchestrator)
):
    """暂停工作流"""
    try:
        logger.info(f"暂停工作流: {workflow_id}")
        
        # 暂停工作流
        # await workflow_orchestrator.pause_workflow(workflow_id)
        
        return {"message": "工作流已暂停"}
        
    except Exception as e:
        logger.error(f"暂停工作流失败: {e}")
        raise HTTPException(status_code=500, detail=f"暂停工作流失败: {str(e)}")


@router.post("/workflows/{workflow_id}/resume")
async def resume_workflow(
    workflow_id: str,
    workflow_orchestrator: WorkflowOrchestrator = Depends(get_workflow_orchestrator)
):
    """恢复工作流"""
    try:
        logger.info(f"恢复工作流: {workflow_id}")
        
        # 恢复工作流
        # await workflow_orchestrator.resume_workflow(workflow_id)
        
        return {"message": "工作流已恢复"}
        
    except Exception as e:
        logger.error(f"恢复工作流失败: {e}")
        raise HTTPException(status_code=500, detail=f"恢复工作流失败: {str(e)}")


@router.post("/workflows/{workflow_id}/cancel")
async def cancel_workflow(
    workflow_id: str,
    workflow_orchestrator: WorkflowOrchestrator = Depends(get_workflow_orchestrator)
):
    """取消工作流"""
    try:
        logger.info(f"取消工作流: {workflow_id}")
        
        # 取消工作流
        # await workflow_orchestrator.cancel_workflow(workflow_id)
        
        return {"message": "工作流已取消"}
        
    except Exception as e:
        logger.error(f"取消工作流失败: {e}")
        raise HTTPException(status_code=500, detail=f"取消工作流失败: {str(e)}")


# 工具管理API
@router.get("/tools", response_model=Dict[str, Any])
async def list_tools(
    tool_registry: MCPToolRegistry = Depends(get_tool_registry)
):
    """获取可用工具列表"""
    try:
        logger.info("获取工具列表")
        
        # 获取工具列表
        tools = tool_registry.list_all_tools()
        
        return {
            "tools": tools,
            "total": len(tools)
        }
        
    except Exception as e:
        logger.error(f"获取工具列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取工具列表失败: {str(e)}")


@router.get("/tools/{tool_id}")
async def get_tool_info(
    tool_id: str,
    tool_registry: MCPToolRegistry = Depends(get_tool_registry)
):
    """获取工具详情"""
    try:
        logger.info(f"获取工具详情: {tool_id}")
        
        # 获取工具信息
        tool_info = tool_registry.get_tool_info(tool_id)
        
        if not tool_info:
            raise HTTPException(status_code=404, detail="工具不存在")
        
        return tool_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取工具详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取工具详情失败: {str(e)}")


# 用户交互API
@router.post("/chat")
async def chat_with_system(
    message: str,
    session_id: Optional[str] = None,
    main_agent: MainAgent = Depends(get_main_agent)
):
    """与系统对话"""
    try:
        logger.info(f"用户对话: {message[:100]}...")
        
        # 处理用户消息
        # response = await main_agent.process_user_message(message, session_id)
        
        # 临时返回
        return {
            "message": "系统正在处理您的请求...",
            "session_id": session_id or "temp_session"
        }
        
    except Exception as e:
        logger.error(f"处理用户消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理用户消息失败: {str(e)}")


# 监控和统计API
@router.get("/monitor/executions")
async def get_execution_metrics(
    time_range: str = "24h",
    workflow_orchestrator: WorkflowOrchestrator = Depends(get_workflow_orchestrator)
):
    """获取执行指标"""
    try:
        logger.info(f"获取执行指标: {time_range}")
        
        # 获取执行指标
        # metrics = await workflow_orchestrator.get_execution_metrics(time_range)
        
        # 临时返回
        return {
            "time_range": time_range,
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0
        }
        
    except Exception as e:
        logger.error(f"获取执行指标失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取执行指标失败: {str(e)}")


@router.get("/monitor/roles")
async def get_role_performance(
    role_id: Optional[str] = None,
    time_range: str = "24h"
):
    """获取角色性能指标"""
    try:
        logger.info(f"获取角色性能: role_id={role_id}, time_range={time_range}")
        
        # 获取角色性能指标
        # performance = await role_registry.get_role_performance(role_id, time_range)
        
        # 临时返回
        return {
            "role_id": role_id,
            "time_range": time_range,
            "total_tasks": 0,
            "success_rate": 0.0,
            "average_completion_time": 0
        }
        
    except Exception as e:
        logger.error(f"获取角色性能失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取角色性能失败: {str(e)}")


# 注册路由到主应用
# 这个函数应该在main.py中调用
def register_routes(app):
    """注册所有路由"""
    app.include_router(router)
