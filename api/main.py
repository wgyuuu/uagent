"""
UAgent Main API Application

主要的FastAPI应用入口，集成所有核心功能
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import structlog
from contextlib import asynccontextmanager

from core.intelligence import MainAgent
from core.workflow import WaterfallWorkflowEngine, WorkflowOrchestrator
from core.context import ContextIsolationManager
from tools.mcp import MCPToolRegistry

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("正在启动UAgent系统...")
    
    # 初始化核心组件
    await initialize_core_components()
    
    logger.info("UAgent系统启动完成")
    
    yield
    
    # 关闭时清理
    logger.info("正在关闭UAgent系统...")
    await cleanup_core_components()
    logger.info("UAgent系统已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="UAgent System",
    description="通用任务完成的多Agent协作系统",
    version="2.0.0",
    lifespan=lifespan
)

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # 生产环境中应该限制
)

# 全局组件实例
main_agent: MainAgent = None
workflow_engine: WaterfallWorkflowEngine = None
workflow_orchestrator: WorkflowOrchestrator = None
context_manager: ContextIsolationManager = None
tool_registry: MCPToolRegistry = None


async def initialize_core_components():
    """初始化核心组件"""
    global main_agent, workflow_engine, workflow_orchestrator, context_manager, tool_registry
    
    try:
        # 初始化工具注册表
        tool_registry = MCPToolRegistry()
        
        # 初始化上下文管理器
        context_manager = ContextIsolationManager()
        
        # 初始化主Agent（这里需要LLM实例）
        # main_agent = MainAgent(llm_instance)
        
        # 初始化工作流引擎
        # workflow_engine = WaterfallWorkflowEngine(main_agent)
        
        # 初始化工作流编排器
        # workflow_orchestrator = WorkflowOrchestrator(main_agent, workflow_engine)
        
        logger.info("核心组件初始化完成")
        
    except Exception as e:
        logger.error(f"核心组件初始化失败: {e}")
        raise


async def cleanup_core_components():
    """清理核心组件"""
    global main_agent, workflow_engine, workflow_orchestrator, context_manager, tool_registry
    
    try:
        # 清理资源
        if tool_registry:
            tool_registry.registered_tools.clear()
        
        if context_manager:
            context_manager.active_contexts.clear()
        
        logger.info("核心组件清理完成")
        
    except Exception as e:
        logger.error(f"核心组件清理失败: {e}")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "UAgent System v2.0.0",
        "status": "running",
        "description": "通用任务完成的多Agent协作系统"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 检查核心组件状态
        component_status = {
            "tool_registry": tool_registry is not None,
            "context_manager": context_manager is not None,
            "main_agent": main_agent is not None,
            "workflow_engine": workflow_engine is not None,
            "workflow_orchestrator": workflow_orchestrator is not None
        }
        
        all_healthy = all(component_status.values())
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "components": component_status,
            "timestamp": "2024-01-14T00:00:00Z"  # 这里应该使用实际时间
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail="健康检查失败")


@app.get("/api/v1/system/info")
async def get_system_info():
    """获取系统信息"""
    return {
        "system_name": "UAgent System",
        "version": "2.0.0",
        "architecture": {
            "intelligence_layer": "智能决策层 - 任务分析、角色推荐、错误恢复",
            "workflow_layer": "工作流层 - 瀑布式执行、状态管理、监控",
            "context_layer": "上下文层 - 角色隔离、8段式压缩、交接管理",
            "tool_layer": "工具层 - MCP集成、用户交互、工具管理",
            "infrastructure_layer": "基础设施层 - 并发管理、持久化、监控"
        },
        "capabilities": [
            "多领域任务处理",
            "智能角色推荐", 
            "瀑布式工作流执行",
            "上下文隔离管理",
            "MCP工具集成",
            "用户实时交互"
        ],
        "supported_domains": [
            "软件开发",
            "数据分析", 
            "金融分析",
            "内容创作",
            "信息处理"
        ]
    }


@app.get("/api/v1/system/stats")
async def get_system_stats():
    """获取系统统计信息"""
    try:
        stats = {}
        
        if tool_registry:
            stats["tools"] = tool_registry.get_registry_stats()
        
        if context_manager:
            stats["context"] = await context_manager.get_context_stats()
        
        return {
            "system_stats": stats,
            "timestamp": "2024-01-14T00:00:00Z"
        }
        
    except Exception as e:
        logger.error(f"获取系统统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取系统统计失败")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "uagent.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
