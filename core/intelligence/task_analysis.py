"""
UAgent Task Analysis Engine

任务分析引擎 - 负责深度理解和分类用户任务
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog
from langchain.llms.base import BaseLLM
from langchain.prompts import PromptTemplate
from langchain.schema import BaseMessage

from ...models.base import Task, TaskAnalysis, TaskDomain, TaskType, ComplexityLevel
from ...models.roles import RoleCapabilities

logger = structlog.get_logger(__name__)


class TaskAnalysisEngine:
    """
    任务分析引擎
    
    使用大语言模型深度理解用户任务，进行多维度分析和分类
    """
    
    def __init__(self, llm: BaseLLM):
        """
        初始化任务分析引擎
        
        Args:
            llm: 大语言模型实例
        """
        self.llm = llm
        self.analysis_cache: Dict[str, TaskAnalysis] = {}
        self.analysis_history: List[Dict[str, Any]] = []
        
        # 分析提示词模板
        self.analysis_prompt = PromptTemplate(
            template=self._get_analysis_prompt_template(),
            input_variables=["task_description", "task_context", "domain_context"]
        )
        
        logger.info("任务分析引擎初始化完成")
    
    async def analyze_task(self, task: Task) -> TaskAnalysis:
        """
        分析任务
        
        Args:
            task: 待分析的任务
            
        Returns:
            TaskAnalysis: 任务分析结果
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"开始分析任务: {task.task_id}")
            
            # 检查缓存
            cache_key = self._generate_cache_key(task)
            if cache_key in self.analysis_cache:
                logger.info(f"使用缓存的分析结果: {task.task_id}")
                return self.analysis_cache[cache_key]
            
            # 准备分析上下文
            task_context = await self._prepare_task_context(task)
            domain_context = await self._prepare_domain_context(task)
            
            # 构建提示词
            prompt = self.analysis_prompt.format(
                task_description=task.description,
                task_context=json.dumps(task_context, indent=2),
                domain_context=json.dumps(domain_context, indent=2)
            )
            
            # 调用LLM进行分析
            response = await self.llm.agenerate([prompt])
            analysis_text = response.generations[0][0].text
            
            # 解析分析结果
            analysis_result = await self._parse_analysis_response(analysis_text)
            
            # 创建TaskAnalysis对象
            task_analysis = TaskAnalysis(
                task_id=task.task_id,
                **analysis_result
            )
            
            # 验证分析结果
            validation_result = await self._validate_analysis(task_analysis, task)
            if not validation_result.is_valid:
                logger.warning(f"分析结果验证失败: {validation_result.error_message}")
                # 使用启发式方法生成备用分析
                task_analysis = await self._generate_fallback_analysis(task)
            
            # 缓存结果
            self.analysis_cache[cache_key] = task_analysis
            
            # 记录分析历史
            execution_time = (datetime.now() - start_time).total_seconds()
            await self._record_analysis_history(task, task_analysis, execution_time)
            
            logger.info(f"任务分析完成: {task.task_id}, 耗时: {execution_time:.2f}秒")
            return task_analysis
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"任务分析失败: {task.task_id}, 错误: {e}, 耗时: {execution_time:.2f}秒")
            
            # 生成备用分析
            return await self._generate_fallback_analysis(task)
    
    async def analyze_task_batch(self, tasks: List[Task]) -> List[TaskAnalysis]:
        """
        批量分析任务
        
        Args:
            tasks: 任务列表
            
        Returns:
            List[TaskAnalysis]: 分析结果列表
        """
        logger.info(f"开始批量分析{len(tasks)}个任务")
        
        # 并发分析任务
        analysis_tasks = [self.analyze_task(task) for task in tasks]
        results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        # 处理异常结果
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"任务{tasks[i].task_id}分析失败: {result}")
                # 生成备用分析
                fallback = await self._generate_fallback_analysis(tasks[i])
                valid_results.append(fallback)
            else:
                valid_results.append(result)
        
        logger.info(f"批量分析完成，成功{len(valid_results)}个")
        return valid_results
    
    async def get_analysis_insights(self) -> Dict[str, Any]:
        """
        获取分析洞察
        
        Returns:
            Dict: 分析洞察数据
        """
        if not self.analysis_history:
            return {"message": "暂无分析历史数据"}
        
        recent_analyses = self.analysis_history[-100:]
        
        # 统计任务领域分布
        domain_distribution = {}
        for analysis in recent_analyses:
            domain = analysis["analysis"].primary_domain.value
            domain_distribution[domain] = domain_distribution.get(domain, 0) + 1
        
        # 统计复杂度分布
        complexity_distribution = {}
        for analysis in recent_analyses:
            complexity = analysis["analysis"].complexity_level.value
            complexity_distribution[complexity] = complexity_distribution.get(complexity, 0) + 1
        
        # 计算平均分析时间
        avg_analysis_time = sum(a["execution_time"] for a in recent_analyses) / len(recent_analyses)
        
        return {
            "total_analyses": len(self.analysis_history),
            "recent_analyses": len(recent_analyses),
            "domain_distribution": domain_distribution,
            "complexity_distribution": complexity_distribution,
            "average_analysis_time": avg_analysis_time,
            "cache_hit_rate": len(self.analysis_cache) / max(len(self.analysis_history), 1)
        }
    
    # ===== 私有方法 =====
    
    def _get_analysis_prompt_template(self) -> str:
        """获取分析提示词模板"""
        return """
你是UAgent系统的任务分析专家，负责深度理解和分析用户任务。

## 任务描述
{task_description}

## 任务上下文
{task_context}

## 领域上下文
{domain_context}

## 分析框架
请对任务进行全面分析，并按以下结构提供分析结果：

### 1. 任务分类
- **主要领域**: [software_development|data_analysis|content_creation|information_processing|financial_analysis|market_research|technical_writing]
- **任务类型**: 
  - 开发类: [new_development|bug_fix|enhancement|refactoring|optimization]
  - 分析类: [data_analysis|financial_analysis|market_research|trend_analysis]
  - 创作类: [content_writing|documentation|report_generation|presentation]
  - 处理类: [document_reading|information_extraction|knowledge_organization]
- **复杂度级别**: [simple|moderate|complex|enterprise]
- **预估范围**: [small|medium|large|extra_large]

### 2. 需求分析
- **功能需求**: 列出关键功能需求
- **非功能需求**: 性能、安全、可扩展性需求
- **技术约束**: 技术栈、平台、集成要求
- **质量标准**: 代码质量、测试、文档需求

### 3. 成功标准
- **主要交付物**: 必须交付的内容
- **质量指标**: 成功的衡量标准
- **验收标准**: 任务完成的条件

### 4. 风险评估
- **技术风险**: 潜在的技术挑战
- **复杂度风险**: 高复杂度或不确定性区域
- **依赖风险**: 外部依赖或集成挑战

### 5. 子领域识别
基于任务内容，识别涉及的具体子领域（如：前端开发、数据可视化、技术文档等）

## 输出要求
请以JSON格式提供分析结果，确保所有字段都有值：

```json
{
    "primary_domain": "领域名称",
    "sub_domains": ["子领域1", "子领域2"],
    "task_type": "任务类型",
    "complexity_level": "复杂度级别",
    "estimated_scope": "预估范围",
    "functional_requirements": ["需求1", "需求2"],
    "non_functional_requirements": ["需求1", "需求2"],
    "technical_constraints": ["约束1", "约束2"],
    "quality_standards": ["标准1", "标准2"],
    "primary_deliverables": ["交付物1", "交付物2"],
    "quality_metrics": ["指标1", "指标2"],
    "acceptance_criteria": ["标准1", "标准2"],
    "technical_risks": ["风险1", "风险2"],
    "complexity_risks": ["风险1", "风险2"],
    "dependency_risks": ["风险1", "风险2"],
    "confidence_score": 0.9
}
```

请确保分析全面、准确，置信度分数反映分析的确定程度。
        """
    
    async def _prepare_task_context(self, task: Task) -> Dict[str, Any]:
        """准备任务上下文"""
        return {
            "task_id": task.task_id,
            "title": task.title,
            "domain": task.domain.value if task.domain else "unknown",
            "priority": task.priority,
            "requirements": task.requirements,
            "constraints": task.constraints,
            "quality_standards": task.quality_standards,
            "deadline": task.deadline.isoformat() if task.deadline else None,
            "created_by": task.created_by,
            "metadata": task.metadata
        }
    
    async def _prepare_domain_context(self, task: Task) -> Dict[str, Any]:
        """准备领域上下文"""
        domain_contexts = {
            TaskDomain.SOFTWARE_DEVELOPMENT: {
                "typical_roles": ["方案规划师", "编码专家", "测试工程师", "代码审查员"],
                "common_deliverables": ["代码", "文档", "测试", "架构设计"],
                "quality_factors": ["可维护性", "性能", "安全性", "可扩展性"]
            },
            TaskDomain.DATA_ANALYSIS: {
                "typical_roles": ["数据分析师", "技术写作专家"],
                "common_deliverables": ["数据洞察", "分析报告", "可视化图表"],
                "quality_factors": ["准确性", "统计显著性", "可解释性"]
            },
            TaskDomain.FINANCIAL_ANALYSIS: {
                "typical_roles": ["股票分析师", "调研分析师", "技术写作专家"],
                "common_deliverables": ["投资分析", "风险评估", "市场报告"],
                "quality_factors": ["准确性", "及时性", "风险披露", "合规性"]
            },
            TaskDomain.CONTENT_CREATION: {
                "typical_roles": ["技术写作专家", "调研分析师", "知识整理专家"],
                "common_deliverables": ["技术文档", "研究报告", "用户指南"],
                "quality_factors": ["清晰性", "准确性", "完整性", "可读性"]
            },
            TaskDomain.INFORMATION_PROCESSING: {
                "typical_roles": ["文档阅读专家", "知识整理专家"],
                "common_deliverables": ["信息摘要", "结构化数据", "知识图谱"],
                "quality_factors": ["准确性", "完整性", "结构化程度"]
            }
        }
        
        return domain_contexts.get(task.domain, {
            "typical_roles": ["通用专家"],
            "common_deliverables": ["分析结果"],
            "quality_factors": ["准确性", "完整性"]
        })
    
    async def _parse_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """解析LLM分析响应"""
        try:
            # 尝试提取JSON部分
            import re
            json_match = re.search(r'```json\s*\n(.*?)\n```', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                # 如果没有找到代码块，尝试直接解析
                json_text = response_text.strip()
            
            # 解析JSON
            analysis_data = json.loads(json_text)
            
            # 验证必需字段
            required_fields = [
                "primary_domain", "task_type", "complexity_level",
                "functional_requirements", "primary_deliverables"
            ]
            
            for field in required_fields:
                if field not in analysis_data:
                    analysis_data[field] = self._get_default_value(field)
            
            return analysis_data
            
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"LLM响应解析失败: {e}")
            # 使用启发式方法解析
            return await self._heuristic_parse(response_text)
    
    async def _heuristic_parse(self, response_text: str) -> Dict[str, Any]:
        """启发式解析分析响应"""
        analysis_data = {}
        
        # 领域识别
        domain_keywords = {
            "software_development": ["代码", "编程", "开发", "系统", "应用", "软件"],
            "data_analysis": ["数据", "分析", "统计", "模型", "预测"],
            "financial_analysis": ["股票", "投资", "金融", "财务", "市场"],
            "content_creation": ["文档", "报告", "写作", "内容", "文章"],
            "information_processing": ["文档", "信息", "提取", "整理", "知识"]
        }
        
        text_lower = response_text.lower()
        domain_scores = {}
        
        for domain, keywords in domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                domain_scores[domain] = score
        
        # 选择得分最高的领域
        if domain_scores:
            primary_domain = max(domain_scores.keys(), key=lambda k: domain_scores[k])
        else:
            primary_domain = "software_development"  # 默认
        
        # 复杂度识别
        complexity_keywords = {
            "simple": ["简单", "基础", "基本"],
            "moderate": ["中等", "适中", "一般"],
            "complex": ["复杂", "高级", "困难"],
            "enterprise": ["企业级", "大型", "复杂系统"]
        }
        
        complexity_level = "moderate"  # 默认
        for level, keywords in complexity_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                complexity_level = level
                break
        
        # 构建分析结果
        analysis_data = {
            "primary_domain": primary_domain,
            "sub_domains": self._extract_sub_domains(text_lower, primary_domain),
            "task_type": self._infer_task_type(text_lower, primary_domain),
            "complexity_level": complexity_level,
            "estimated_scope": self._estimate_scope(text_lower),
            "functional_requirements": self._extract_requirements(response_text),
            "non_functional_requirements": [],
            "technical_constraints": [],
            "quality_standards": ["基本质量要求"],
            "primary_deliverables": self._extract_deliverables(response_text, primary_domain),
            "quality_metrics": ["完成度", "准确性"],
            "acceptance_criteria": ["满足功能需求"],
            "technical_risks": [],
            "complexity_risks": [],
            "dependency_risks": [],
            "confidence_score": 0.6  # 启发式分析置信度较低
        }
        
        return analysis_data
    
    def _extract_sub_domains(self, text: str, primary_domain: str) -> List[str]:
        """提取子领域"""
        sub_domain_map = {
            "software_development": {
                "前端": ["前端", "ui", "界面", "用户界面"],
                "后端": ["后端", "api", "服务器", "数据库"],
                "全栈": ["全栈", "完整系统"],
                "移动": ["移动", "app", "手机应用"],
                "web": ["web", "网站", "网页"]
            },
            "data_analysis": {
                "统计分析": ["统计", "分析", "数据分析"],
                "机器学习": ["机器学习", "模型", "预测"],
                "数据可视化": ["可视化", "图表", "展示"]
            },
            "financial_analysis": {
                "股票分析": ["股票", "股价", "股市"],
                "投资分析": ["投资", "投资组合", "资产"],
                "风险分析": ["风险", "风险评估"]
            }
        }
        
        domain_map = sub_domain_map.get(primary_domain, {})
        found_sub_domains = []
        
        for sub_domain, keywords in domain_map.items():
            if any(keyword in text for keyword in keywords):
                found_sub_domains.append(sub_domain)
        
        return found_sub_domains or ["通用"]
    
    def _infer_task_type(self, text: str, primary_domain: str) -> str:
        """推断任务类型"""
        type_keywords = {
            "new_development": ["开发", "创建", "构建", "实现"],
            "bug_fix": ["修复", "bug", "错误", "问题"],
            "enhancement": ["增强", "改进", "优化", "升级"],
            "data_analysis": ["分析", "统计", "数据"],
            "financial_analysis": ["金融分析", "投资分析", "股票分析"],
            "content_writing": ["写作", "编写", "创作"],
            "documentation": ["文档", "说明", "手册"],
            "report_generation": ["报告", "总结", "汇报"]
        }
        
        for task_type, keywords in type_keywords.items():
            if any(keyword in text for keyword in keywords):
                return task_type
        
        # 基于领域的默认类型
        domain_defaults = {
            "software_development": "new_development",
            "data_analysis": "data_analysis",
            "financial_analysis": "financial_analysis",
            "content_creation": "content_writing",
            "information_processing": "document_reading"
        }
        
        return domain_defaults.get(primary_domain, "new_development")
    
    def _estimate_scope(self, text: str) -> str:
        """估算任务范围"""
        scope_indicators = {
            "small": ["简单", "小", "基础", "快速"],
            "medium": ["中等", "标准", "一般"],
            "large": ["大", "复杂", "完整", "全面"],
            "extra_large": ["企业级", "大型", "复杂系统", "平台"]
        }
        
        for scope, keywords in scope_indicators.items():
            if any(keyword in text for keyword in keywords):
                return scope
        
        return "medium"  # 默认中等范围
    
    def _extract_requirements(self, text: str) -> List[str]:
        """提取功能需求"""
        # 简单的关键词提取
        import re
        
        # 查找包含需求关键词的句子
        requirement_patterns = [
            r'需要.*?[。\n]',
            r'要求.*?[。\n]',
            r'必须.*?[。\n]',
            r'应该.*?[。\n]'
        ]
        
        requirements = []
        for pattern in requirement_patterns:
            matches = re.findall(pattern, text)
            requirements.extend([match.strip('。\n') for match in matches])
        
        return requirements[:10] if requirements else ["基本功能实现"]
    
    def _extract_deliverables(self, text: str, domain: str) -> List[str]:
        """提取交付物"""
        domain_deliverables = {
            "software_development": ["源代码", "技术文档", "测试用例"],
            "data_analysis": ["分析报告", "数据洞察", "可视化图表"],
            "financial_analysis": ["投资分析报告", "风险评估", "投资建议"],
            "content_creation": ["技术文档", "用户指南", "报告"],
            "information_processing": ["信息摘要", "结构化数据", "知识整理"]
        }
        
        return domain_deliverables.get(domain, ["分析结果", "总结报告"])
    
    def _get_default_value(self, field: str) -> Any:
        """获取字段默认值"""
        defaults = {
            "primary_domain": "software_development",
            "sub_domains": ["general"],
            "task_type": "new_development",
            "complexity_level": "moderate",
            "estimated_scope": "medium",
            "functional_requirements": ["基本功能实现"],
            "non_functional_requirements": [],
            "technical_constraints": [],
            "quality_standards": ["基本质量要求"],
            "primary_deliverables": ["完成的任务"],
            "quality_metrics": ["完成度"],
            "acceptance_criteria": ["满足基本要求"],
            "technical_risks": [],
            "complexity_risks": [],
            "dependency_risks": [],
            "confidence_score": 0.5
        }
        
        return defaults.get(field, "")
    
    async def _validate_analysis(self, analysis: TaskAnalysis, original_task: Task) -> ValidationResult:
        """验证分析结果"""
        errors = []
        warnings = []
        
        # 检查必需字段
        if not analysis.primary_domain:
            errors.append("主要领域不能为空")
        
        if not analysis.task_type:
            errors.append("任务类型不能为空")
        
        if not analysis.primary_deliverables:
            warnings.append("未识别到主要交付物")
        
        # 检查置信度
        if analysis.confidence_score < 0.5:
            warnings.append("分析置信度较低")
        
        # 检查领域一致性
        if original_task.domain and analysis.primary_domain != original_task.domain:
            warnings.append(f"分析领域({analysis.primary_domain})与任务领域({original_task.domain})不一致")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            error_message="; ".join(errors) if errors else None,
            warnings=warnings
        )
    
    async def _generate_fallback_analysis(self, task: Task) -> TaskAnalysis:
        """生成备用分析结果"""
        logger.info(f"为任务{task.task_id}生成备用分析")
        
        # 基于任务基本信息生成简单分析
        return TaskAnalysis(
            task_id=task.task_id,
            primary_domain=task.domain or TaskDomain.SOFTWARE_DEVELOPMENT,
            sub_domains=["general"],
            task_type=TaskType.NEW_DEVELOPMENT,
            complexity_level=ComplexityLevel.MODERATE,
            estimated_scope="medium",
            functional_requirements=[task.description],
            primary_deliverables=["任务完成"],
            quality_metrics=["基本完成度"],
            acceptance_criteria=["满足基本需求"],
            confidence_score=0.4,  # 备用分析置信度较低
            analysis_method="fallback"
        )
    
    def _generate_cache_key(self, task: Task) -> str:
        """生成缓存键"""
        # 基于任务关键信息生成缓存键
        key_components = [
            task.title,
            task.description,
            task.domain.value if task.domain else "unknown",
            str(task.priority),
            str(hash(str(task.requirements))),
            str(hash(str(task.constraints)))
        ]
        
        return hash("|".join(key_components))
    
    async def _record_analysis_history(self, 
                                     task: Task, 
                                     analysis: TaskAnalysis, 
                                     execution_time: float):
        """记录分析历史"""
        history_record = {
            "task_id": task.task_id,
            "analysis": analysis,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat(),
            "cache_used": False
        }
        
        self.analysis_history.append(history_record)
        
        # 保持历史记录在合理范围内
        if len(self.analysis_history) > 1000:
            self.analysis_history = self.analysis_history[-500:]
    
    def clear_cache(self):
        """清理分析缓存"""
        self.analysis_cache.clear()
        logger.info("任务分析缓存已清理")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "cache_size": len(self.analysis_cache),
            "history_size": len(self.analysis_history),
            "cache_hit_rate": self._calculate_cache_hit_rate()
        }
    
    def _calculate_cache_hit_rate(self) -> float:
        """计算缓存命中率"""
        if not self.analysis_history:
            return 0.0
        
        recent_analyses = self.analysis_history[-100:]
        cache_hits = sum(1 for a in recent_analyses if a.get("cache_used", False))
        
        return cache_hits / len(recent_analyses)
