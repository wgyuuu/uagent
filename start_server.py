#!/usr/bin/env python3
"""
UAgent 服务器启动脚本
"""

import uvicorn
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def start_server():
    """启动UAgent服务器"""
    print("🚀 启动UAgent智能任务完成系统...")
    print("=" * 60)
    
    try:
        # 配置服务器参数
        host = "0.0.0.0"
        port = 8000
        reload = True
        
        print(f"📍 服务器地址: http://{host}:{port}")
        print(f"🔄 自动重载: {'启用' if reload else '禁用'}")
        print("=" * 60)
        
        # 启动服务器
        uvicorn.run(
            "api.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")
    except Exception as e:
        print(f"❌ 启动服务器失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_server()
