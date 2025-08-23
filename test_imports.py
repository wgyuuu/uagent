#!/usr/bin/env python3
"""
测试脚本 - 验证UAgent系统各模块的导入
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试各个模块的导入"""
    print("🔍 开始测试UAgent系统模块导入...")
    
    # 测试基础模型
    try:
        from models.base import BaseModel, TimestampMixin
        print("✅ 基础模型导入成功")
    except Exception as e:
        print(f"❌ 基础模型导入失败: {e}")
    
    # 测试角色模型
    try:
        from models.roles import Role, RoleCapability, RoleInstance
        print("✅ 角色模型导入成功")
    except Exception as e:
        print(f"❌ 角色模型导入失败: {e}")
    
    # 测试工作流模型
    try:
        from models.workflow import Workflow, WorkflowStep, WorkflowExecution
        print("✅ 工作流模型导入成功")
    except Exception as e:
        print(f"❌ 工作流模型导入失败: {e}")
    
    # 测试核心模块
    try:
        from core.intelligence.main_agent import MainAgent
        print("✅ 主智能体导入成功")
    except Exception as e:
        print(f"❌ 主智能体导入失败: {e}")
    
    try:
        from core.intelligence.task_analysis import TaskAnalysisEngine
        print("✅ 任务分析引擎导入成功")
    except Exception as e:
        print(f"❌ 任务分析引擎导入失败: {e}")
    
    try:
        from core.workflow.waterfall_engine import WaterfallWorkflowEngine
        print("✅ 瀑布式工作流引擎导入成功")
    except Exception as e:
        print(f"❌ 瀑布式工作流引擎导入失败: {e}")
    
    # 测试工具模块
    try:
        from tools.mcp.tool_registry import MCPToolRegistry
        print("✅ MCP工具注册中心导入成功")
    except Exception as e:
        print(f"❌ MCP工具注册中心导入失败: {e}")
    
    # 测试基础设施模块
    try:
        from infrastructure.security.security_manager import SecurityManager
        print("✅ 安全管理器导入成功")
    except Exception as e:
        print(f"❌ 安全管理器导入失败: {e}")
    
    try:
        from infrastructure.persistence.persistence_manager import PersistenceManager
        print("✅ 持久化管理器导入成功")
    except Exception as e:
        print(f"❌ 持久化管理器导入失败: {e}")
    
    # 测试UI模块
    try:
        from ui.chat.chat_interface import ChatInterface
        print("✅ 聊天界面导入成功")
    except Exception as e:
        print(f"❌ 聊天界面导入失败: {e}")
    
    try:
        from ui.dashboard.dashboard_interface import DashboardInterface
        print("✅ 仪表板界面导入成功")
    except Exception as e:
        print(f"❌ 仪表板界面导入失败: {e}")
    
    # 测试提示词模块
    try:
        from prompts.role_prompts import RolePromptManager
        print("✅ 角色提示词管理器导入成功")
    except Exception as e:
        print(f"❌ 角色提示词管理器导入失败: {e}")
    
    try:
        from prompts.templates.template_manager import TemplateManager
        print("✅ 模板管理器导入成功")
    except Exception as e:
        print(f"❌ 模板管理器导入失败: {e}")
    
    try:
        from prompts.reminders.system_reminder import SystemReminder
        print("✅ 系统提醒导入成功")
    except Exception as e:
        print(f"❌ 系统提醒导入失败: {e}")
    
    print("\n🎯 导入测试完成！")

if __name__ == "__main__":
    test_imports()
