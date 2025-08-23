"""
LLM Manager Usage Example

LLM管理器使用示例
"""

import asyncio
import os
import sys
sys.path.append('/Users/wgyuuu/Workspace/myaigc/uagent')
from tools.llm import LLMManager

async def example_usage():
    """使用示例"""
    try:
        # 初始化LLM管理器
        print("正在初始化LLM管理器...")
        llm_manager = LLMManager()
        
        # 获取可用场景列表
        available_scenes = llm_manager.get_available_scenes()
        print(f"可用场景: {available_scenes}")
        
        # 获取任务分析场景的LLM
        print("\n获取任务分析场景的LLM...")
        task_analysis_llm = llm_manager.get_llm_for_scene("task_analysis")
        print(f"任务分析LLM类型: {type(task_analysis_llm)}")
        
        # 获取角色推荐场景的LLM
        print("\n获取角色推荐场景的LLM...")
        role_recommendation_llm = llm_manager.get_llm_for_scene("role_recommendation")
        print(f"角色推荐LLM类型: {type(role_recommendation_llm)}")
        
        # 获取模型信息
        print("\n获取模型信息...")
        task_analysis_info = llm_manager.get_model_info("task_analysis")
        print(f"任务分析模型信息: {task_analysis_info}")
        
        role_recommendation_info = llm_manager.get_model_info("role_recommendation")
        print(f"角色推荐模型信息: {role_recommendation_info}")
        
        # 测试LLM调用（需要有效的API密钥）
        print("\n测试LLM调用...")
        try:
            response = await task_analysis_llm.agenerate(["请简单介绍一下你自己"])
            print(f"LLM响应: {response.generations[0][0].text}")
        except Exception as e:
            print(f"LLM调用失败（这是正常的，因为需要有效的API密钥）: {e}")
        
        print("\nLLM管理器使用示例完成！")
        
    except Exception as e:
        print(f"示例执行失败: {e}")

def check_environment():
    """检查环境变量"""
    print("检查环境变量...")
    
    required_vars = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY"
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: 已设置")
        else:
            print(f"✗ {var}: 未设置")
    
    print("\n注意：要完整测试LLM功能，需要设置相应的API密钥")

if __name__ == "__main__":
    print("=== LLM管理器使用示例 ===\n")
    
    # 检查环境变量
    check_environment()
    
    print("\n" + "="*50 + "\n")
    
    # 运行示例
    asyncio.run(example_usage())
