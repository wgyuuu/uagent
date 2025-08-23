from typing import List
from pydantic import BaseModel


class RoleDefinition(BaseModel):
    """角色定义"""
    id: str
    name: str
    description: str 
    domain: str
    capabilities: List[str]
    dependencies: List[str]
    prompt_template: str

class RoleRecommendation(BaseModel):
    """角色推荐"""
    role_id: str
    name: str
    description: str
    domain: str
    capabilities: List[str]