"""
Template Manager

模板管理器 - 管理和渲染提示词模板
"""

from typing import Dict, List, Any, Optional, Union
import structlog
import os
import json
import yaml
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound
import re

logger = structlog.get_logger(__name__)


class TemplateType(Enum):
    """模板类型"""
    ROLE_PROMPT = "role_prompt"
    HANDOFF = "handoff"
    SYSTEM_MESSAGE = "system_message"
    ERROR_HANDLING = "error_handling"
    WORKFLOW_STEP = "workflow_step"
    USER_INTERACTION = "user_interaction"


class TemplateFormat(Enum):
    """模板格式"""
    JINJA2 = "jinja2"
    PLAIN_TEXT = "plain_text"
    MARKDOWN = "markdown"
    JSON = "json"


@dataclass
class TemplateMetadata:
    """模板元数据"""
    template_id: str
    name: str
    description: str
    template_type: TemplateType
    format: TemplateFormat
    version: str
    author: str
    created_at: datetime
    updated_at: datetime
    tags: List[str]
    variables: List[str]  # 模板中使用的变量
    required_variables: List[str]  # 必需的变量
    default_values: Dict[str, Any]  # 默认值
    examples: List[Dict[str, Any]]  # 使用示例


@dataclass
class PromptTemplate:
    """提示词模板"""
    template_id: str
    content: str
    metadata: TemplateMetadata
    is_active: bool = True
    compiled_template: Optional[Template] = None


class TemplateManager:
    """
    模板管理器
    
    管理提示词模板的加载、编译、渲染和版本控制
    """
    
    def __init__(self, template_directory: str = "templates"):
        self.template_directory = Path(template_directory)
        self.templates: Dict[str, PromptTemplate] = {}
        self.jinja_env: Optional[Environment] = None
        self.template_cache: Dict[str, Template] = {}
        
        # 初始化Jinja2环境
        self._initialize_jinja_environment()
        
        # 加载模板
        self._load_templates()
        
        logger.info("模板管理器初始化完成")
    
    def _initialize_jinja_environment(self):
        """初始化Jinja2环境"""
        try:
            if self.template_directory.exists():
                self.jinja_env = Environment(
                    loader=FileSystemLoader(str(self.template_directory)),
                    trim_blocks=True,
                    lstrip_blocks=True,
                    keep_trailing_newline=True
                )
                
                # 注册自定义过滤器
                self._register_custom_filters()
                
            logger.info("Jinja2环境已初始化")
            
        except Exception as e:
            logger.error(f"初始化Jinja2环境失败: {e}")
    
    def _register_custom_filters(self):
        """注册自定义过滤器"""
        if not self.jinja_env:
            return
        
        def format_timestamp(timestamp, format_str='%Y-%m-%d %H:%M:%S'):
            """格式化时间戳"""
            if isinstance(timestamp, datetime):
                return timestamp.strftime(format_str)
            return str(timestamp)
        
        def truncate_text(text, length=100, suffix='...'):
            """截断文本"""
            if len(text) <= length:
                return text
            return text[:length] + suffix
        
        def extract_variables(text):
            """提取模板变量"""
            pattern = r'\{\{\s*([^}]+)\s*\}\}'
            variables = re.findall(pattern, text)
            return [var.strip() for var in variables]
        
        def format_list(items, separator=', ', last_separator=' and '):
            """格式化列表"""
            if not items:
                return ''
            if len(items) == 1:
                return str(items[0])
            if len(items) == 2:
                return f"{items[0]}{last_separator}{items[1]}"
            return f"{separator.join(str(item) for item in items[:-1])}{last_separator}{items[-1]}"
        
        # 注册过滤器
        self.jinja_env.filters['format_timestamp'] = format_timestamp
        self.jinja_env.filters['truncate_text'] = truncate_text
        self.jinja_env.filters['extract_variables'] = extract_variables
        self.jinja_env.filters['format_list'] = format_list
    
    def _load_templates(self):
        """加载模板"""
        try:
            if not self.template_directory.exists():
                self.template_directory.mkdir(parents=True, exist_ok=True)
                self._create_default_templates()
                return
            
            # 扫描模板文件
            template_files = list(self.template_directory.rglob("*.j2")) + \
                            list(self.template_directory.rglob("*.txt")) + \
                            list(self.template_directory.rglob("*.md"))
            
            for template_file in template_files:
                try:
                    self._load_template_file(template_file)
                except Exception as e:
                    logger.error(f"加载模板文件失败 {template_file}: {e}")
            
            logger.info(f"已加载 {len(self.templates)} 个模板")
            
        except Exception as e:
            logger.error(f"加载模板失败: {e}")
    
    def _load_template_file(self, template_file: Path):
        """加载单个模板文件"""
        try:
            # 读取模板内容
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找元数据文件
            metadata_file = template_file.with_suffix('.meta.json')
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata_dict = json.load(f)
            else:
                # 从模板内容中提取元数据
                metadata_dict = self._extract_metadata_from_content(content, template_file)
            
            # 创建元数据对象
            metadata = self._create_metadata_from_dict(metadata_dict)
            
            # 编译模板
            compiled_template = None
            if metadata.format == TemplateFormat.JINJA2 and self.jinja_env:
                try:
                    compiled_template = self.jinja_env.from_string(content)
                except Exception as e:
                    logger.warning(f"编译Jinja2模板失败 {template_file}: {e}")
            
            # 创建模板对象
            template = PromptTemplate(
                template_id=metadata.template_id,
                content=content,
                metadata=metadata,
                compiled_template=compiled_template
            )
            
            self.templates[template.template_id] = template
            
            logger.debug(f"模板已加载: {template.template_id}")
            
        except Exception as e:
            logger.error(f"加载模板文件失败 {template_file}: {e}")
            raise
    
    def _extract_metadata_from_content(self, content: str, template_file: Path) -> Dict[str, Any]:
        """从模板内容中提取元数据"""
        # 查找YAML前置元数据
        yaml_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        if yaml_match:
            try:
                metadata = yaml.safe_load(yaml_match.group(1))
                if isinstance(metadata, dict):
                    return metadata
            except Exception as e:
                logger.warning(f"解析YAML元数据失败: {e}")
        
        # 默认元数据
        template_id = template_file.stem
        return {
            "template_id": template_id,
            "name": template_id.replace('_', ' ').title(),
            "description": f"模板: {template_id}",
            "template_type": "role_prompt",
            "format": "jinja2" if template_file.suffix == '.j2' else "plain_text",
            "version": "1.0.0",
            "author": "system",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "tags": [],
            "variables": self._extract_variables_from_content(content),
            "required_variables": [],
            "default_values": {},
            "examples": []
        }
    
    def _extract_variables_from_content(self, content: str) -> List[str]:
        """从模板内容中提取变量"""
        pattern = r'\{\{\s*([^}]+)\s*\}\}'
        variables = re.findall(pattern, content)
        return list(set(var.strip().split('.')[0] for var in variables))
    
    def _create_metadata_from_dict(self, metadata_dict: Dict[str, Any]) -> TemplateMetadata:
        """从字典创建元数据对象"""
        return TemplateMetadata(
            template_id=metadata_dict.get("template_id", "unknown"),
            name=metadata_dict.get("name", "Unknown Template"),
            description=metadata_dict.get("description", ""),
            template_type=TemplateType(metadata_dict.get("template_type", "role_prompt")),
            format=TemplateFormat(metadata_dict.get("format", "jinja2")),
            version=metadata_dict.get("version", "1.0.0"),
            author=metadata_dict.get("author", "unknown"),
            created_at=datetime.fromisoformat(metadata_dict.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(metadata_dict.get("updated_at", datetime.now().isoformat())),
            tags=metadata_dict.get("tags", []),
            variables=metadata_dict.get("variables", []),
            required_variables=metadata_dict.get("required_variables", []),
            default_values=metadata_dict.get("default_values", {}),
            examples=metadata_dict.get("examples", [])
        )
    
    def _create_default_templates(self):
        """创建默认模板"""
        default_templates = {
            "role_expert_coder": {
                "content": """---
template_id: role_expert_coder
name: 编码专家角色提示词
description: 编码专家的角色定义和行为模式
template_type: role_prompt
format: jinja2
version: 1.0.0
author: system
tags: [coding, expert, role]
variables: [task_description, requirements, context]
required_variables: [task_description]
default_values:
  requirements: "无特殊要求"
  context: "通用编程任务"
---

# 编码专家 (Coding Expert)

## 角色身份
你是一位经验丰富的软件开发专家，具备以下特质：
- 精通多种编程语言和框架
- 注重代码质量、性能和可维护性
- 具备丰富的系统设计和架构经验
- 熟悉最佳实践和设计模式

## 当前任务
{{ task_description }}

## 要求
{{ requirements }}

## 上下文信息
{{ context }}

## 工作原则
1. 编写清晰、可读的代码
2. 遵循编码规范和最佳实践
3. 考虑性能、安全性和可维护性
4. 提供必要的注释和文档
5. 进行适当的错误处理

## 输出格式
请按以下格式提供解决方案：
1. 分析和理解
2. 解决方案设计
3. 代码实现
4. 测试建议
5. 后续改进建议
""",
                "filename": "role_expert_coder.j2"
            },
            
            "handoff_template": {
                "content": """---
template_id: handoff_template
name: 角色交接模板
description: 角色间任务交接的标准模板
template_type: handoff
format: jinja2
version: 1.0.0
author: system
tags: [handoff, workflow, communication]
variables: [from_role, to_role, task_summary, completed_work, next_actions, context, artifacts]
required_variables: [from_role, to_role, task_summary]
---

# 任务交接文档

## 交接信息
- **交接方**: {{ from_role }}
- **接收方**: {{ to_role }}
- **交接时间**: {{ current_time | format_timestamp }}

## 任务概述
{{ task_summary }}

## 已完成工作
{% if completed_work %}
{{ completed_work }}
{% else %}
暂无已完成工作记录
{% endif %}

## 下一步行动
{% if next_actions %}
{{ next_actions }}
{% else %}
需要接收方确定下一步行动
{% endif %}

## 上下文信息
{% if context %}
{{ context }}
{% else %}
无额外上下文信息
{% endif %}

## 产出物和资源
{% if artifacts %}
{% for artifact in artifacts %}
- {{ artifact.name }}: {{ artifact.description }}
  位置: {{ artifact.location }}
{% endfor %}
{% else %}
暂无产出物
{% endif %}

## 注意事项
- 请确认理解任务要求
- 如有疑问请及时询问
- 保持工作连续性和一致性
""",
                "filename": "handoff_template.j2"
            },
            
            "error_handling": {
                "content": """---
template_id: error_handling
name: 错误处理模板
description: 错误情况的处理和恢复指导
template_type: error_handling
format: jinja2
version: 1.0.0
author: system
tags: [error, recovery, guidance]
variables: [error_type, error_message, context, recovery_options]
required_variables: [error_type, error_message]
---

# 错误处理指南

## 错误信息
- **错误类型**: {{ error_type }}
- **错误消息**: {{ error_message }}
- **发生时间**: {{ current_time | format_timestamp }}

## 上下文
{% if context %}
{{ context }}
{% else %}
无上下文信息
{% endif %}

## 恢复选项
{% if recovery_options %}
{% for option in recovery_options %}
### 选项 {{ loop.index }}: {{ option.name }}
**描述**: {{ option.description }}
**难度**: {{ option.difficulty }}
**风险**: {{ option.risk }}

{% endfor %}
{% else %}
需要人工分析确定恢复策略
{% endif %}

## 建议行动
1. 分析错误根本原因
2. 评估影响范围
3. 选择合适的恢复策略
4. 实施恢复措施
5. 验证恢复效果
6. 记录经验教训

## 预防措施
- 加强输入验证
- 完善错误处理机制
- 增加监控和告警
- 定期进行测试
""",
                "filename": "error_handling.j2"
            }
        }
        
        for template_id, template_data in default_templates.items():
            template_file = self.template_directory / template_data["filename"]
            
            try:
                with open(template_file, 'w', encoding='utf-8') as f:
                    f.write(template_data["content"])
                
                logger.info(f"默认模板已创建: {template_id}")
                
            except Exception as e:
                logger.error(f"创建默认模板失败 {template_id}: {e}")
    
    async def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """获取模板"""
        return self.templates.get(template_id)
    
    async def list_templates(
        self,
        template_type: Optional[TemplateType] = None,
        tags: Optional[List[str]] = None
    ) -> List[PromptTemplate]:
        """列出模板"""
        templates = list(self.templates.values())
        
        if template_type:
            templates = [t for t in templates if t.metadata.template_type == template_type]
        
        if tags:
            templates = [
                t for t in templates 
                if any(tag in t.metadata.tags for tag in tags)
            ]
        
        return templates
    
    async def render_template(
        self,
        template_id: str,
        variables: Dict[str, Any],
        validate_required: bool = True
    ) -> str:
        """渲染模板"""
        try:
            template = self.templates.get(template_id)
            if not template:
                raise ValueError(f"模板不存在: {template_id}")
            
            # 验证必需变量
            if validate_required:
                missing_vars = [
                    var for var in template.metadata.required_variables
                    if var not in variables
                ]
                if missing_vars:
                    raise ValueError(f"缺少必需变量: {missing_vars}")
            
            # 合并默认值
            render_vars = {**template.metadata.default_values, **variables}
            
            # 添加系统变量
            render_vars.update({
                'current_time': datetime.now(),
                'template_id': template_id,
                'template_version': template.metadata.version
            })
            
            # 渲染模板
            if template.compiled_template:
                return template.compiled_template.render(**render_vars)
            else:
                # 简单的字符串替换
                content = template.content
                for key, value in render_vars.items():
                    placeholder = f"{{{{{key}}}}}"
                    content = content.replace(placeholder, str(value))
                return content
                
        except Exception as e:
            logger.error(f"渲染模板失败 {template_id}: {e}")
            raise
    
    async def create_template(
        self,
        template_id: str,
        content: str,
        metadata: TemplateMetadata,
        save_to_file: bool = True
    ) -> bool:
        """创建模板"""
        try:
            # 编译模板
            compiled_template = None
            if metadata.format == TemplateFormat.JINJA2 and self.jinja_env:
                try:
                    compiled_template = self.jinja_env.from_string(content)
                except Exception as e:
                    logger.warning(f"编译Jinja2模板失败: {e}")
            
            # 创建模板对象
            template = PromptTemplate(
                template_id=template_id,
                content=content,
                metadata=metadata,
                compiled_template=compiled_template
            )
            
            self.templates[template_id] = template
            
            # 保存到文件
            if save_to_file:
                await self._save_template_to_file(template)
            
            logger.info(f"模板已创建: {template_id}")
            return True
            
        except Exception as e:
            logger.error(f"创建模板失败: {e}")
            return False
    
    async def update_template(
        self,
        template_id: str,
        content: Optional[str] = None,
        metadata: Optional[TemplateMetadata] = None,
        save_to_file: bool = True
    ) -> bool:
        """更新模板"""
        try:
            if template_id not in self.templates:
                return False
            
            template = self.templates[template_id]
            
            if content is not None:
                template.content = content
                
                # 重新编译
                if template.metadata.format == TemplateFormat.JINJA2 and self.jinja_env:
                    try:
                        template.compiled_template = self.jinja_env.from_string(content)
                    except Exception as e:
                        logger.warning(f"重新编译模板失败: {e}")
            
            if metadata is not None:
                template.metadata = metadata
            
            template.metadata.updated_at = datetime.now()
            
            # 保存到文件
            if save_to_file:
                await self._save_template_to_file(template)
            
            logger.info(f"模板已更新: {template_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新模板失败: {e}")
            return False
    
    async def delete_template(
        self,
        template_id: str,
        delete_files: bool = True
    ) -> bool:
        """删除模板"""
        try:
            if template_id not in self.templates:
                return False
            
            template = self.templates[template_id]
            
            # 删除文件
            if delete_files:
                await self._delete_template_files(template)
            
            del self.templates[template_id]
            
            logger.info(f"模板已删除: {template_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除模板失败: {e}")
            return False
    
    async def _save_template_to_file(self, template: PromptTemplate):
        """保存模板到文件"""
        try:
            # 确定文件扩展名
            if template.metadata.format == TemplateFormat.JINJA2:
                ext = ".j2"
            elif template.metadata.format == TemplateFormat.MARKDOWN:
                ext = ".md"
            else:
                ext = ".txt"
            
            # 保存模板内容
            template_file = self.template_directory / f"{template.template_id}{ext}"
            with open(template_file, 'w', encoding='utf-8') as f:
                f.write(template.content)
            
            # 保存元数据
            metadata_file = self.template_directory / f"{template.template_id}.meta.json"
            metadata_dict = asdict(template.metadata)
            # 转换datetime为字符串
            metadata_dict['created_at'] = template.metadata.created_at.isoformat()
            metadata_dict['updated_at'] = template.metadata.updated_at.isoformat()
            # 转换枚举为字符串
            metadata_dict['template_type'] = template.metadata.template_type.value
            metadata_dict['format'] = template.metadata.format.value
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata_dict, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"保存模板文件失败: {e}")
            raise
    
    async def _delete_template_files(self, template: PromptTemplate):
        """删除模板文件"""
        try:
            # 删除模板文件
            for ext in [".j2", ".md", ".txt"]:
                template_file = self.template_directory / f"{template.template_id}{ext}"
                if template_file.exists():
                    template_file.unlink()
            
            # 删除元数据文件
            metadata_file = self.template_directory / f"{template.template_id}.meta.json"
            if metadata_file.exists():
                metadata_file.unlink()
            
        except Exception as e:
            logger.error(f"删除模板文件失败: {e}")
    
    async def validate_template(self, template_id: str) -> Dict[str, Any]:
        """验证模板"""
        try:
            template = self.templates.get(template_id)
            if not template:
                return {"valid": False, "error": "模板不存在"}
            
            validation_result = {
                "valid": True,
                "warnings": [],
                "errors": [],
                "template_id": template_id,
                "metadata": asdict(template.metadata)
            }
            
            # 验证Jinja2语法
            if template.metadata.format == TemplateFormat.JINJA2:
                if not template.compiled_template:
                    validation_result["errors"].append("Jinja2模板编译失败")
                    validation_result["valid"] = False
            
            # 验证变量
            content_vars = self._extract_variables_from_content(template.content)
            declared_vars = template.metadata.variables
            
            # 检查未声明的变量
            undeclared_vars = set(content_vars) - set(declared_vars)
            if undeclared_vars:
                validation_result["warnings"].append(f"未声明的变量: {list(undeclared_vars)}")
            
            # 检查未使用的变量
            unused_vars = set(declared_vars) - set(content_vars)
            if unused_vars:
                validation_result["warnings"].append(f"未使用的变量: {list(unused_vars)}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"验证模板失败: {e}")
            return {"valid": False, "error": str(e)}
    
    async def get_template_statistics(self) -> Dict[str, Any]:
        """获取模板统计信息"""
        total_templates = len(self.templates)
        
        # 按类型统计
        type_stats = {}
        for template in self.templates.values():
            template_type = template.metadata.template_type.value
            type_stats[template_type] = type_stats.get(template_type, 0) + 1
        
        # 按格式统计
        format_stats = {}
        for template in self.templates.values():
            format_type = template.metadata.format.value
            format_stats[format_type] = format_stats.get(format_type, 0) + 1
        
        # 按作者统计
        author_stats = {}
        for template in self.templates.values():
            author = template.metadata.author
            author_stats[author] = author_stats.get(author, 0) + 1
        
        # 编译状态统计
        compiled_count = len([t for t in self.templates.values() if t.compiled_template])
        
        return {
            "total_templates": total_templates,
            "type_distribution": type_stats,
            "format_distribution": format_stats,
            "author_distribution": author_stats,
            "compiled_templates": compiled_count,
            "template_directory": str(self.template_directory),
            "cache_size": len(self.template_cache)
        }
