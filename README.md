# UAgent - 通用化多角色协作Agent系统

## 概述

UAgent是一个基于角色专业化的通用Agent组装系统，通过瀑布式工作流和智能角色推荐，实现复杂任务的高效协作完成。系统借鉴了Claude Code的优秀设计理念，结合现代Agent架构的最佳实践，为软件开发领域提供了完整的AI协作解决方案。

## 核心特性

### 🎯 角色专业化协作
- **专家角色定义**: 方案规划师、编码专家、测试工程师、代码审查员等专业角色
- **瀑布式工作流**: 角色按预定顺序依次执行，确保质量和完整性
- **标准化交接**: 角色间通过标准化格式进行信息传递
- **完全上下文隔离**: 每个角色在独立环境中执行，避免相互干扰

### 🧠 智能决策系统
- **智能角色推荐**: 基于LLM的语义理解自动推荐最适合的角色组合
- **依赖分析**: 自动分析角色依赖关系，识别关键路径
- **错误恢复**: 智能错误分类和恢复策略生成
- **手动干预支持**: 支持用户手动干预和工作流调整

### 📝 分层提示词系统
- **角色身份定义**: 每个角色有明确的专业身份和能力边界
- **行为规则**: 详细的工作原则和输出标准
- **System-Reminder机制**: 借鉴Claude Code的无侵入式安全提醒
- **动态上下文感知**: 根据任务和工作流状态动态调整提示词

### 🗜️ 8段式上下文压缩
- **智能记忆管理**: 借鉴Claude Code的8段式压缩算法
- **信息优先级排序**: 基于重要性、时效性、相关性的多维度评估
- **质量验证**: 全面的信息丢失检测和压缩质量控制
- **自适应优化**: 根据压缩效果动态调整策略

### 🛠️ MCP工具生态
- **共享工具池**: 支持多个角色并发访问MCP工具
- **用户提问MCP**: 将用户交互也作为MCP服务
- **权限控制**: 基于角色的工具访问权限管理
- **负载均衡**: 智能的工具实例分配和故障恢复

### 💾 企业级数据管理
- **多数据库支持**: PostgreSQL、MySQL、Redis等多种后端
- **多级缓存**: 内存+Redis的高性能缓存体系
- **事务支持**: 完整的ACID事务保证
- **性能优化**: 连接池、查询优化、执行计划缓存

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    UAgent System v2.0                      │
├─────────────────────────────────────────────────────────────┤
│  Prompt Layer (分层提示词系统)                              │
│  ├── Role Identity Prompts (角色身份提示词)                │
│  ├── Behavior Rules Prompts (行为规则提示词)               │
│  ├── Security Reminder System (安全提醒系统)               │
│  └── Handoff Templates (交接模板)                          │
├─────────────────────────────────────────────────────────────┤
│  Intelligence Layer (智能决策层)                           │
│  ├── Main Agent (主Agent - 模型判断推荐)                  │
│  ├── Role Recommendation Engine (角色推荐引擎)             │
│  ├── Dependency Analyzer (依赖分析器)                      │
│  └── Error Recovery Controller (错误恢复控制器)            │
├─────────────────────────────────────────────────────────────┤
│  Workflow Layer (工作流层)                                │
│  ├── Waterfall Engine (瀑布式引擎)                        │
│  ├── Context Isolation Manager (上下文隔离管理器)          │
│  ├── 8-Segment Compression (8段式压缩)                    │
│  └── Handoff Orchestrator (交接编排器)                    │
├─────────────────────────────────────────────────────────────┤
│  SubAgent Layer (子Agent层)                               │
│  ├── Planning Expert (方案规划师)                         │
│  ├── Coding Expert (编码专家)                             │
│  ├── Testing Expert (测试工程师)                          │
│  └── Review Expert (代码审查员)                           │
├─────────────────────────────────────────────────────────────┤
│  Tool Layer (工具层)                                      │
│  ├── Shared MCP Pool (共享MCP资源池)                      │
│  ├── User Question MCP (用户提问MCP)                      │
│  └── Tool Access Controller (工具访问控制器)              │
├─────────────────────────────────────────────────────────────┤
│  Infrastructure Layer (基础设施层)                        │
│  ├── Persistence Interface (持久化接口)                   │
│  ├── Concurrent Execution Manager (并发执行管理)          │
│  └── Manual Intervention Interface (手动干预接口)         │
└─────────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 环境准备
```bash
# 克隆项目
git clone <repository-url>
cd uagent

# 安装依赖
pip install -r requirements.txt

# 配置数据库（可选，默认使用文件存储）
cp config/database.example.yaml config/database.yaml
# 编辑数据库配置
```

### 2. 基本配置
```python
# config/uagent_config.yaml
system:
  max_concurrency: 10
  default_timeout: 300
  
roles:
  - name: "方案规划师"
    type: "planner"
    prompt_template: "prompts/planner.txt"
    tools: ["user_question", "web_search"]
    
  - name: "编码专家" 
    type: "coder"
    prompt_template: "prompts/coder.txt"
    tools: ["file_operations", "git_operations"]

mcp_servers:
  - name: "local_tools"
    url: "http://localhost:8080"
```

### 3. 启动系统
```python
from uagent import UAgentSystem

# 初始化系统
system = UAgentSystem(config_path="config/uagent_config.yaml")

# 启动服务
await system.start()

# 提交任务
task_id = await system.submit_task(
    description="实现一个用户管理系统",
    requirements={
        "technology": "Python FastAPI",
        "database": "PostgreSQL",
        "features": ["用户注册", "登录认证", "权限管理"]
    }
)

# 监控进度
status = await system.get_task_status(task_id)
print(f"任务状态: {status}")
```

## 详细文档

### 技术文档
- [01_系统架构设计](tech/01_系统架构设计.md) - 整体架构和设计理念
- [02_分层提示词系统](tech/02_分层提示词系统.md) - 提示词设计和System-Reminder机制
- [03_智能决策层设计](tech/03_智能决策层设计.md) - 角色推荐和错误恢复
- [04_瀑布式工作流引擎](tech/04_瀑布式工作流引擎.md) - 工作流执行和上下文管理
- [05_MCP工具集成架构](tech/05_MCP工具集成架构.md) - 工具集成和用户交互
- [06_8段式上下文压缩算法](tech/06_8段式上下文压缩算法.md) - 智能记忆管理
- [07_数据持久化接口设计](tech/07_数据持久化接口设计.md) - 数据存储和缓存策略

### API文档
```bash
# 启动API服务
python -m uagent.api.main

# 访问API文档
open http://localhost:8000/docs
```

## 使用示例

### 角色配置示例
```python
from uagent.models import AgentConfig, IsolationLevel

# 配置方案规划师
planner_config = AgentConfig(
    name="senior_architect",
    agent_type="方案规划师",
    prompt_template="""
    你是一位资深的方案规划师，专门负责需求分析和技术方案设计。
    
    核心职责：
    - 深入理解用户需求，识别关键功能点
    - 设计合理的技术架构和实现路径
    - 制定详细的开发计划和里程碑
    - 识别潜在风险和技术难点
    """,
    tools=["user_question", "web_search", "documentation"],
    isolation_level=IsolationLevel.STRICT,
    resource_limits={
        "memory_mb": 1024,
        "cpu_cores": 2,
        "timeout_seconds": 600
    }
)
```

### 任务提交示例
```python
# 提交复杂开发任务
task_result = await system.submit_task(
    description="开发一个电商平台的订单管理系统",
    requirements={
        "功能需求": [
            "订单创建和编辑",
            "支付集成",
            "库存管理",
            "物流跟踪"
        ],
        "技术要求": {
            "后端": "Python FastAPI",
            "数据库": "PostgreSQL + Redis",
            "前端": "React + TypeScript"
        },
        "质量要求": {
            "测试覆盖率": "> 80%",
            "性能": "支持1000并发",
            "安全": "OWASP合规"
        }
    },
    preferred_roles=["方案规划师", "编码专家", "测试工程师", "代码审查员"]
)
```

### 工作流监控
```python
# 实时监控工作流进度
async def monitor_workflow(task_id: str):
    while True:
        status = await system.get_task_status(task_id)
        
        print(f"当前状态: {status['workflow_status']}")
        print(f"当前角色: {status['current_role']}")
        print(f"进度: {status['progress']}")
        
        if status['workflow_status'] in ['completed', 'failed']:
            break
        
        await asyncio.sleep(10)

# 获取详细执行历史
history = await system.get_execution_history(task_id)
for step in history:
    print(f"{step['role']}: {step['summary']}")
```

## 扩展开发

### 添加新角色
```python
from uagent.models import BaseAgent

class SecurityExpert(BaseAgent):
    """安全专家角色"""
    
    async def execute_task(self, task):
        # 实现安全审查逻辑
        security_report = await self.analyze_security_risks(task)
        recommendations = await self.generate_security_recommendations(security_report)
        
        return {
            "security_report": security_report,
            "recommendations": recommendations,
            "risk_level": self.assess_risk_level(security_report)
        }
    
    async def cleanup(self):
        # 清理资源
        pass

# 注册新角色
system.register_role("安全专家", SecurityExpert)
```

### 自定义MCP工具
```python
from uagent.tools import MCPTool

class CustomAnalysisTool(MCPTool):
    """自定义分析工具"""
    
    def __init__(self):
        super().__init__(
            name="custom_analysis",
            description="执行自定义代码分析",
            input_schema={
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "analysis_type": {"type": "string"}
                }
            }
        )
    
    async def execute(self, parameters):
        code = parameters["code"]
        analysis_type = parameters["analysis_type"]
        
        # 实现分析逻辑
        result = await self.analyze_code(code, analysis_type)
        
        return {
            "analysis_result": result,
            "recommendations": self.generate_recommendations(result)
        }

# 注册工具
system.register_tool(CustomAnalysisTool())
```

## 性能优化

### 并发配置
```yaml
# config/performance.yaml
concurrency:
  max_workflows: 50
  max_roles_per_workflow: 10
  connection_pool_size: 20

caching:
  context_cache_ttl: 600
  result_cache_ttl: 3600
  redis_url: "redis://localhost:6379"

optimization:
  enable_query_cache: true
  enable_connection_pooling: true
  compression_ratio: 0.6
```

### 监控和调优
```python
# 性能监控
performance_stats = await system.get_performance_stats()
print(f"平均任务完成时间: {performance_stats['avg_completion_time']}")
print(f"成功率: {performance_stats['success_rate']}")
print(f"缓存命中率: {performance_stats['cache_hit_rate']}")

# 系统调优
await system.optimize_performance({
    "compression_ratio": 0.7,  # 调整压缩比例
    "cache_ttl": 900,          # 调整缓存时间
    "connection_pool_size": 30  # 调整连接池大小
})
```

## 部署指南

### Docker部署
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "-m", "uagent.api.main"]
```

### Kubernetes部署
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: uagent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: uagent
  template:
    metadata:
      labels:
        app: uagent
    spec:
      containers:
      - name: uagent
        image: uagent:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          value: "postgresql://user:pass@postgres:5432/uagent"
        - name: REDIS_URL
          value: "redis://redis:6379"
```

## 贡献指南

1. Fork项目并创建功能分支
2. 编写代码并添加测试
3. 确保所有测试通过
4. 提交Pull Request

### 开发环境设置
```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
pytest tests/

# 代码格式化
black uagent/
isort uagent/

# 类型检查
mypy uagent/
```

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 联系方式

- 项目主页: https://github.com/your-org/uagent
- 问题反馈: https://github.com/your-org/uagent/issues
- 技术讨论: https://github.com/your-org/uagent/discussions

## 致谢

- 感谢 [Claude Code](https://claude.ai/code) 项目提供的设计灵感
- 感谢 [MCP Protocol](https://modelcontextprotocol.io) 提供的工具集成标准
- 感谢所有贡献者的辛勤工作

---

**UAgent - 让AI协作更智能，让开发更高效** 🚀
