# UAgent 系统部署和使用指南

## 🚀 快速开始

### 1. 环境要求

- Python 3.10+
- 推荐使用 `uv` 包管理器（更快、更可靠）

### 2. 安装依赖

```bash
# 使用 uv 安装依赖（推荐）
uv pip install -r requirements.txt

# 或者使用传统 pip
pip install -r requirements.txt
```

### 3. 启动系统

#### 方式1: 使用启动脚本（推荐）
```bash
uv run python start_server.py
```

#### 方式2: 直接使用 uvicorn
```bash
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 方式3: 使用 Python 模块
```bash
uv run python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 访问系统

- **API文档**: http://localhost:8000/docs
- **ReDoc文档**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health

## 🔧 系统测试

### 运行功能测试
```bash
# 测试基本功能
uv run python run_simple_test.py

# 测试模块导入
uv run python test_imports.py
```

## 📁 系统结构

```
uagent/
├── api/                    # API层
│   ├── main.py           # FastAPI主应用
│   └── routes.py         # API路由定义
├── core/                  # 核心业务逻辑
│   ├── intelligence/     # 智能决策层
│   ├── workflow/         # 工作流引擎
│   └── context/          # 上下文管理
├── models/                # 数据模型
├── tools/                 # 工具层
│   └── mcp/             # MCP工具管理
├── infrastructure/        # 基础设施层
│   ├── security/         # 安全管理
│   ├── persistence/      # 持久化管理
│   ├── monitoring/       # 监控管理
│   └── concurrency/      # 并发管理
├── ui/                    # 用户界面层
│   ├── chat/             # 聊天界面
│   └── dashboard/        # 仪表板界面
├── prompts/               # 提示词层
│   ├── role_prompts.py   # 角色提示词管理
│   ├── templates/        # 模板管理
│   └── reminders/        # 智能提醒
└── requirements.txt       # 依赖配置
```

## 🌟 核心功能

### 1. 智能任务分析
- 自动分析用户任务需求
- 智能推荐合适的角色组合
- 动态工作流编排

### 2. 角色化多智能体
- 编码专家 (Coding Expert)
- 方案规划师 (Planner)
- 测试工程师 (Tester)
- 代码审查员 (Reviewer)
- 支持自定义角色扩展

### 3. 瀑布式工作流
- 任务在角色间有序传递
- 上下文隔离和交接管理
- 错误恢复和重试机制

### 4. 智能提醒系统
- 基于上下文的智能提示
- 最佳实践建议
- 安全风险提醒

### 5. 可配置工具层
- HTTP MCP服务器集成
- 内置常用工具服务
- 用户交互MCP服务

## 🔌 API接口

### 主要端点

- `POST /api/v1/tasks` - 创建新任务
- `GET /api/v1/tasks/{task_id}` - 获取任务状态
- `POST /api/v1/workflows` - 创建工作流
- `GET /api/v1/workflows/{workflow_id}` - 获取工作流状态
- `GET /api/v1/roles` - 获取可用角色列表
- `POST /api/v1/chat/sessions` - 创建聊天会话

## 🛠️ 配置说明

### 环境变量
```bash
# 数据库配置
DATABASE_URL=postgresql://user:password@localhost/uagent

# Redis配置
REDIS_URL=redis://localhost:6379

# 安全配置
SECRET_KEY=your-secret-key
ENCRYPTION_KEY=your-encryption-key

# 日志配置
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 配置文件
系统支持多种配置格式：
- YAML (.yaml/.yml)
- JSON (.json)
- 环境变量 (.env)

## 📊 监控和日志

### 日志系统
- 结构化日志 (JSON格式)
- 多级别日志记录
- 性能指标收集

### 监控指标
- 系统资源使用率
- 工作流执行统计
- API请求性能
- 错误率和响应时间

## 🔒 安全特性

### 认证和授权
- JWT令牌认证
- 基于角色的权限控制
- 会话管理和超时控制

### 数据安全
- 敏感数据加密存储
- 输入验证和清理
- SQL注入防护

## 🚨 故障排除

### 常见问题

1. **依赖安装失败**
   ```bash
   # 清理缓存重新安装
   uv pip cache clean
   uv pip install -r requirements.txt
   ```

2. **模块导入错误**
   ```bash
   # 检查Python路径
   python -c "import sys; print(sys.path)"
   
   # 使用uv运行
   uv run python your_script.py
   ```

3. **端口占用**
   ```bash
   # 检查端口使用
   lsof -i :8000
   
   # 修改端口
   uvicorn api.main:app --port 8001
   ```

### 日志查看
```bash
# 查看应用日志
tail -f logs/uagent.log

# 查看错误日志
grep "ERROR" logs/uagent.log
```

## 📈 性能优化

### 建议配置
- 使用异步数据库连接池
- 启用Redis缓存
- 配置适当的并发限制
- 使用负载均衡器

### 监控建议
- 设置性能告警阈值
- 定期检查资源使用情况
- 监控API响应时间
- 跟踪工作流执行效率

## 🤝 贡献指南

### 开发环境设置
```bash
# 克隆仓库
git clone <repository-url>
cd uagent

# 安装开发依赖
uv pip install -r requirements-dev.txt

# 运行测试
uv run pytest

# 代码格式化
uv run black .
uv run isort .
```

### 代码规范
- 遵循PEP 8编码规范
- 使用类型注解
- 编写单元测试
- 添加文档字符串

## 📞 支持

### 获取帮助
- 查看API文档: `/docs`
- 检查系统状态: `/health`
- 查看日志文件
- 提交Issue或PR

### 联系方式
- 项目仓库: [GitHub Repository]
- 问题反馈: [Issues]
- 功能建议: [Discussions]

---

**UAgent - 智能任务完成系统** 🚀

让AI助手更智能，让任务完成更高效！
