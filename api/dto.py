from typing import List, Optional, Dict, Any
from pydantic import BaseModel

# 为了避免与models/base.py中的RoleRecommendation冲突，重命名这个模型
class APIRoleRecommendation(BaseModel):
    """API角色推荐响应模型"""
    role_id: str
    name: str
    description: str
    domain: str
    capabilities: List[str]
    confidence_score: float = 0.8
    reasoning: str = ""
    estimated_time: str = "2-4小时"

# 请求/响应模型
class CreateTaskRequest(BaseModel):
    """创建任务请求"""
    title: str
    description: str
    domain: str
    complexity: str
    expected_output: str
    user_preferences: Optional[Dict[str, Any]] = None


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


class WorkflowExecutionRequest(BaseModel):
    """工作流执行请求"""
    task_id: str
    selected_roles: List[str]
    execution_config: Optional[Dict[str, Any]] = None


class RoleRecommendationRequest(BaseModel):
    """角色推荐请求"""
    task_description: str
    domain: str
    complexity: str
    output_requirements: str


class RoleDefinition(BaseModel):
    """角色定义"""
    id: str
    name: str
    description: str 
    domain: str
    capabilities: List[str]
    dependencies: List[str]
    prompt_template: str