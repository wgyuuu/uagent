#!/usr/bin/env python3
"""
UAgent Server Startup Script

启动UAgent服务器的主脚本
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 现在可以正常导入了
import uvicorn

if __name__ == "__main__":
    print("启动UAgent服务器...")
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8099,
        reload=True,
        log_level="info"
    )
