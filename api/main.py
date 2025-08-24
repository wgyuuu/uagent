"""
UAgent Main API Application

主要的FastAPI应用入口，集成所有核心功能
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import structlog
from contextlib import asynccontextmanager

from core.intelligence import MainAgent
from core.workflow import WaterfallWorkflowEngine, WorkflowOrchestrator
from core.context import ContextIsolationManager
from tools.mcp import MCPToolRegistry
from tools.llm import LLMManager
from api.routes import register_routes

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

# 注册API路由
register_routes(app)

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
llm_manager: LLMManager = None
main_agent: MainAgent = None
workflow_engine: WaterfallWorkflowEngine = None
workflow_orchestrator: WorkflowOrchestrator = None
context_manager: ContextIsolationManager = None
tool_registry: MCPToolRegistry = None


async def initialize_core_components():
    """初始化核心组件"""
    global llm_manager, main_agent, workflow_engine, workflow_orchestrator, context_manager, tool_registry
    
    try:
        # 初始化LLM管理器
        llm_manager = LLMManager()
        
        # 初始化工具注册表
        tool_registry = MCPToolRegistry()
        
        # 初始化上下文管理器
        context_manager = ContextIsolationManager()
        
        # 初始化主Agent（传入LLM管理器）
        main_agent = MainAgent(llm_manager)
        
        # 初始化工作流引擎
        workflow_engine = WaterfallWorkflowEngine(main_agent)
        
        # 初始化工作流编排器
        workflow_orchestrator = WorkflowOrchestrator(main_agent, workflow_engine)
        
        logger.info("核心组件初始化完成")
        
        # 返回初始化后的组件实例
        return {
            "llm_manager": llm_manager,
            "main_agent": main_agent,
            "workflow_engine": workflow_engine,
            "workflow_orchestrator": workflow_orchestrator,
            "context_manager": context_manager,
            "tool_registry": tool_registry
        }
        
    except Exception as e:
        logger.error(f"核心组件初始化失败: {e}")
        raise


async def cleanup_core_components():
    """清理核心组件"""
    global llm_manager, main_agent, workflow_engine, workflow_orchestrator, context_manager, tool_registry
    
    try:
        # 清理资源
        if tool_registry:
            tool_registry.registered_tools.clear()
        
        if context_manager:
            context_manager.active_contexts.clear()
        
        logger.info("核心组件清理完成")
        
    except Exception as e:
        logger.error(f"核心组件清理失败: {e}")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "uagent.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
