"""
UAgent Main API Application

主要的FastAPI应用入口，集成所有核心功能
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import structlog
from contextlib import asynccontextmanager

from tools.llm import initialize_llm_manager
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


async def initialize_core_components():
    """初始化核心组件"""
    
    try:
        # 初始化LLM管理器（在tools/llm模块内全局初始化）
        initialize_llm_manager()
        logger.info("LLM管理器初始化完成")
        
        logger.info("核心组件初始化完成")
        
    except Exception as e:
        logger.error(f"核心组件初始化失败: {e}")
        raise


async def cleanup_core_components():
    """清理核心组件"""
    
    try:
        # 清理资源
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
