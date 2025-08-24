"""
UAgent API Routes

定义所有API路由端点
"""

from fastapi import APIRouter, FastAPI
import structlog

logger = structlog.get_logger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/v1", tags=["uagent"])


# 注册路由到主应用
# 这个函数应该在main.py中调用
def register_routes(app: FastAPI):
    """注册所有路由"""
    app.include_router(router)