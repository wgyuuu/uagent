#!/usr/bin/env python3
"""
UAgent 简单测试脚本

直接运行测试，无需启动FastAPI服务
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入main.py中的组件
from api.main import initialize_core_components, cleanup_core_components


async def run_simple_test(task_description: str = "创建一个简单的Python Hello World程序", components: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    运行简单测试 - 初始化系统并执行一个任务
    
    Args:
        task_description: 任务描述
        components: 初始化后的组件实例
        
    Returns:
        Dict: 测试结果
    """
    try:
        print("开始运行简单测试...")
        
        # 1. 确保组件已初始化
        if not components:
            raise Exception("组件实例未提供")
            
        # 从组件字典中获取需要的组件
        llm_manager = components.get("llm_manager")
        main_agent = components.get("main_agent")
        workflow_engine = components.get("workflow_engine")
        workflow_orchestrator = components.get("workflow_orchestrator")
        
        init_faileds = []
        for name, component in {"llm_manager": llm_manager, "main_agent": main_agent, "workflow_engine": workflow_engine, "workflow_orchestrator": workflow_orchestrator}.items():
            if not component:
                init_faileds.append(name)
        if init_faileds:
            raise Exception(f"核心组件未初始化: {init_faileds}")
        
        # 2. 创建测试任务
        from models.base import Task, TaskDomain, TaskType, ComplexityLevel
        
        test_task = Task(
            title="简单测试任务",
            description=task_description,
            domain=TaskDomain.SOFTWARE_DEVELOPMENT,
            task_type=TaskType.NEW_DEVELOPMENT,
            complexity_level=ComplexityLevel.SIMPLE,
            created_by="test_user",
            priority=5
        )
        
        print(f"创建测试任务: {test_task.task_id}")
        
        # 3. 任务分析和角色推荐
        print("开始任务分析...")
        task_analysis, workflow_definition = await main_agent.analyze_and_plan_task(test_task)
        
        print(f"任务分析完成: 领域={task_analysis.primary_domain}, 类型={task_analysis.task_type}")
        print(f"推荐角色序列: {workflow_definition.roles}")
        
        # 4. 创建工作流
        print("创建工作流...")
        from core.workflow.workflow_orchestrator import WorkflowRequest
        
        workflow_request = WorkflowRequest(
            task=test_task,
            preferred_roles=workflow_definition.roles,
            priority=5
        )
        
        workflow_execution = await workflow_orchestrator.create_workflow(workflow_request)
        print(f"工作流创建完成: {workflow_execution.workflow_id}")
        
        # 5. 启动工作流执行
        print("启动工作流执行...")
        success = await workflow_orchestrator.start_workflow(workflow_execution.workflow_id)
        
        if not success:
            raise Exception("工作流启动失败")
        
        # 6. 等待执行完成
        print("等待工作流执行完成...")
        max_wait_time = 300  # 最大等待5分钟
        wait_interval = 2  # 每2秒检查一次
        
        start_time = datetime.now()
        while True:
            await asyncio.sleep(wait_interval)
            
            # 检查工作流状态
            workflow_info = await workflow_orchestrator.get_workflow_info(workflow_execution.workflow_id)
            if not workflow_info:
                raise Exception("无法获取工作流信息")
            
            status = workflow_info.get("status")
            print(f"工作流状态: {status}")
            
            if status in ["completed", "failed", "cancelled"]:
                break
            
            # 检查超时
            elapsed_time = (datetime.now() - start_time).total_seconds()
            if elapsed_time > max_wait_time:
                print("工作流执行超时")
                break
        
        # 7. 获取最终结果
        final_workflow_info = await workflow_orchestrator.get_workflow_info(workflow_execution.workflow_id)
        
        # 8. 整理测试结果
        test_result = {
            "success": True,
            "task_id": test_task.task_id,
            "workflow_id": workflow_execution.workflow_id,
            "task_analysis": {
                "primary_domain": task_analysis.primary_domain,
                "task_type": task_analysis.task_type,
                "complexity_level": task_analysis.complexity_level,
                "estimated_scope": task_analysis.estimated_scope
            },
            "role_recommendation": {
                "recommended_sequence": workflow_definition.roles,
                "total_roles": len(workflow_definition.roles)
            },
            "execution_result": {
                "status": final_workflow_info.get("status"),
                "total_execution_time": final_workflow_info.get("total_execution_time"),
                "role_results": final_workflow_info.get("role_results", {}),
                "errors": final_workflow_info.get("errors", [])
            },
            "test_timestamp": datetime.now().isoformat()
        }
        
        print("简单测试完成")
        return test_result
        
    except Exception as e:
        print(f"简单测试失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "test_timestamp": datetime.now().isoformat()
        }


async def main():
    """主测试函数"""
    print("🚀 开始UAgent简单测试...")
    
    try:
        # 1. 初始化系统组件
        print("📋 初始化系统组件...")
        components = await initialize_core_components()
        print("✅ 系统组件初始化完成")
        
        # 2. 运行简单测试
        print("\n🧪 运行简单测试...")
        test_description = "创建一个简单的Python Hello World程序，包含main函数和打印语句"
        
        result = await run_simple_test(test_description, components)
        
        # 3. 输出测试结果
        print("\n📊 测试结果:")
        print("=" * 50)
        
        if result["success"]:
            print(f"✅ 测试成功!")
            print(f"📝 任务ID: {result['task_id']}")
            print(f"🔄 工作流ID: {result['workflow_id']}")
            
            print(f"\n📋 任务分析:")
            analysis = result['task_analysis']
            print(f"  - 领域: {analysis['primary_domain']}")
            print(f"  - 类型: {analysis['task_type']}")
            print(f"  - 复杂度: {analysis['complexity_level']}")
            print(f"  - 预估范围: {analysis['estimated_scope']}")
            
            print(f"\n👥 角色推荐:")
            recommendation = result['role_recommendation']
            print(f"  - 推荐角色数: {recommendation['total_roles']}")
            print(f"  - 角色序列: {' → '.join(recommendation['recommended_sequence'])}")
            
            print(f"\n⚡ 执行结果:")
            execution = result['execution_result']
            print(f"  - 状态: {execution['status']}")
            print(f"  - 执行时间: {execution.get('total_execution_time', 'N/A')}秒")
            
            if execution.get('role_results'):
                print(f"  - 角色结果:")
                for role, role_result in execution['role_results'].items():
                    print(f"    * {role}: {role_result.get('status', 'N/A')}")
            
            if execution.get('errors'):
                print(f"  - 错误信息:")
                for error in execution['errors']:
                    print(f"    * {error}")
            
        else:
            print(f"❌ 测试失败!")
            print(f"🔴 错误类型: {result['error_type']}")
            print(f"📝 错误信息: {result['error']}")
        
        print(f"\n⏰ 测试时间: {result['test_timestamp']}")
        
    except Exception as e:
        print(f"❌ 测试执行异常: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 4. 清理资源
        print("\n🧹 清理系统资源...")
        try:
            await cleanup_core_components()
            print("✅ 资源清理完成")
        except Exception as e:
            print(f"⚠️ 资源清理异常: {e}")
    
    print("\n🏁 测试完成")


if __name__ == "__main__":
    # 检查环境变量
    required_env_vars = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print("⚠️ 警告: 以下环境变量未设置:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\n💡 提示: 请设置相应的API密钥以确保测试正常运行")
        print("   如果没有设置，测试可能会失败")
    
    print("\n" + "="*60)
    print("UAgent 简单测试脚本")
    print("="*60)
    
    # 运行测试
    asyncio.run(main())
