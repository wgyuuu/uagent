#!/usr/bin/env python3
"""
简单测试脚本 - 验证UAgent系统基本功能
"""

import asyncio
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_basic_functionality():
    """测试基本功能"""
    print("🚀 开始测试UAgent系统基本功能...")
    
    # 测试聊天界面
    try:
        from ui.chat.chat_interface import ChatInterface
        chat_interface = ChatInterface()
        print("✅ 聊天界面创建成功")
        
        # 测试创建会话
        session = await chat_interface.create_session("test_user", "测试会话")
        print(f"✅ 会话创建成功: {session.session_id}")
        
    except Exception as e:
        print(f"❌ 聊天界面测试失败: {e}")
    
    # 测试仪表板界面
    try:
        from ui.dashboard.dashboard_interface import DashboardInterface
        dashboard = DashboardInterface()
        print("✅ 仪表板界面创建成功")
        
        # 测试获取统计信息
        stats = await dashboard.get_dashboard_statistics()
        print(f"✅ 仪表板统计信息: {stats}")
        
    except Exception as e:
        print(f"❌ 仪表板界面测试失败: {e}")
    
    # 测试角色提示词管理器
    try:
        from prompts.role_prompts import RolePromptManager
        role_manager = RolePromptManager()
        print("✅ 角色提示词管理器创建成功")
        
        # 测试获取角色列表
        roles = await role_manager.list_roles()
        print(f"✅ 角色列表获取成功: {len(roles)} 个角色")
        
    except Exception as e:
        print(f"❌ 角色提示词管理器测试失败: {e}")
    
    # 测试模板管理器
    try:
        from prompts.templates.template_manager import TemplateManager
        template_manager = TemplateManager()
        print("✅ 模板管理器创建成功")
        
        # 测试获取模板列表
        templates = await template_manager.list_templates()
        print(f"✅ 模板列表获取成功: {len(templates)} 个模板")
        
    except Exception as e:
        print(f"❌ 模板管理器测试失败: {e}")
    
    # 测试系统提醒
    try:
        from prompts.reminders.system_reminder import SystemReminder
        reminder = SystemReminder()
        print("✅ 系统提醒创建成功")
        
        # 测试获取统计信息
        stats = await reminder.get_reminder_statistics()
        print(f"✅ 提醒统计信息: {stats}")
        
    except Exception as e:
        print(f"❌ 系统提醒测试失败: {e}")
    
    print("\n🎉 基本功能测试完成！")

def test_sync_functionality():
    """测试同步功能"""
    print("\n🔄 开始测试同步功能...")
    
    # 测试数据模型
    try:
        from models.base import BaseModel, TimestampMixin
        print("✅ 基础数据模型导入成功")
        
        # 测试创建基础模型实例
        class TestModel(BaseModel):
            name: str = "test"
            value: int = 42
        
        test_instance = TestModel()
        print(f"✅ 测试模型实例创建成功: {test_instance.name} = {test_instance.value}")
        
    except Exception as e:
        print(f"❌ 基础数据模型测试失败: {e}")
    
    print("🔄 同步功能测试完成！")

if __name__ == "__main__":
    print("=" * 60)
    print("UAgent 系统功能测试")
    print("=" * 60)
    
    # 测试同步功能
    test_sync_functionality()
    
    # 测试异步功能
    asyncio.run(test_basic_functionality())
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
