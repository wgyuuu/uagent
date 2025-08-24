"""
UAgent Role Recommendation Engine

角色推荐引擎 - 基于任务分析智能推荐最适合的角色组合
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog
from langchain.llms.base import BaseLLM
from langchain.prompts import PromptTemplate
import traceback

from models.base import ComplexityLevel, TaskAnalysis, RoleRecommendation, ValidationResult
from models.roles import RoleFactory, RoleCapabilities, ExpertRole
from models.workflow import WorkflowTemplate, StandardWorkflowTemplates
from tools.llm import LLMManager

logger = structlog.get_logger(__name__)


class RoleRecommendationEngine:
    """
    角色推荐引擎
    
    基于任务分析结果和角色能力矩阵，智能推荐最优的角色组合
    """
    
    def __init__(self, llm_manager: LLMManager):
        """
        初始化角色推荐引擎
        
        Args:
            llm_manager: LLM管理器实例
        """
        self.llm = llm_manager.get_llm_for_scene("role_recommendation")
        self.role_factory = RoleFactory()
        self.recommendation_cache: Dict[str, RoleRecommendation] = {}
        self.recommendation_history: List[Dict[str, Any]] = []
        
        # 加载角色能力矩阵
        self.role_capabilities = self._load_role_capabilities()
        
        # 推荐提示词模板
        self.recommendation_prompt = PromptTemplate(
            template=self._get_recommendation_prompt_template(),
            input_variables=["task_analysis", "available_roles", "role_capabilities"]
        )
        
        logger.info("角色推荐引擎初始化完成")
    
    async def recommend_roles(self, task_analysis: TaskAnalysis) -> RoleRecommendation:
        """
        推荐角色
        
        Args:
            task_analysis: 任务分析结果
            
        Returns:
            RoleRecommendation: 角色推荐结果
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"开始角色推荐: 任务={task_analysis.task_id}")
            
            # 检查缓存
            cache_key = self._generate_cache_key(task_analysis)
            if cache_key in self.recommendation_cache:
                logger.info(f"使用缓存的推荐结果: {task_analysis.task_id}")
                return self.recommendation_cache[cache_key]
            
            # 1. 基于规则的预筛选
            candidate_roles = await self._pre_filter_roles(task_analysis)
            logger.info(f"预筛选得到{len(candidate_roles)}个候选角色")
            
            # 2. 优先使用LLM智能推荐
            llm_recommendation = await self._llm_based_recommendation(
                task_analysis, candidate_roles
            )
            
            # 3. 检查LLM推荐是否有效，无效时使用模板推荐作为兜底
            if await self._is_llm_recommendation_valid(llm_recommendation):
                final_recommendation = llm_recommendation
                logger.info("使用LLM推荐结果")
            else:
                # 4. LLM推荐无效时，使用模板推荐作为兜底
                logger.warning("LLM推荐无效，使用模板推荐作为兜底")
                template_recommendation = await self._template_based_recommendation(task_analysis)
                
                if template_recommendation:
                    final_recommendation = template_recommendation
                    logger.info("使用模板推荐结果")
                else:
                    # 5. 双重兜底：生成备用推荐
                    logger.warning("模板推荐也失败，使用备用推荐")
                    final_recommendation = await self._generate_fallback_recommendation(task_analysis)
            
            # 5. 验证推荐结果
            validation_result = await self._validate_recommendation(
                final_recommendation, task_analysis
            )
            
            if not validation_result.is_valid:
                logger.warning(f"推荐结果验证失败: {validation_result.error_message}")
                # 使用备用推荐
                final_recommendation = await self._generate_fallback_recommendation(task_analysis)
            
            # 6. 缓存结果
            self.recommendation_cache[cache_key] = final_recommendation
            
            # 7. 记录推荐历史
            execution_time = (datetime.now() - start_time).total_seconds()
            await self._record_recommendation_history(
                task_analysis, final_recommendation, execution_time
            )
            
            logger.info(f"角色推荐完成: {final_recommendation.recommended_sequence}")
            return final_recommendation
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"角色推荐失败: {e}, 耗时: {execution_time:.2f}秒")
            
            # 生成备用推荐
            return await self._generate_fallback_recommendation(task_analysis)
    
    async def calculate_role_fit_scores(self, 
                                      task_analysis: TaskAnalysis) -> Dict[str, float]:
        """
        计算所有角色的匹配分数
        
        Args:
            task_analysis: 任务分析结果
            
        Returns:
            Dict[str, float]: 角色匹配分数字典
        """
        scores = {}
        available_roles = self.role_factory.get_available_roles()
        
        for role_name in available_roles:
            score = await self._calculate_single_role_fit(role_name, task_analysis)
            scores[role_name] = score
        
        return scores
    
    async def optimize_role_sequence(self, 
                                   roles: List[str],
                                   task_analysis: TaskAnalysis) -> List[str]:
        """
        优化角色序列
        
        Args:
            roles: 原始角色列表
            task_analysis: 任务分析结果
            
        Returns:
            List[str]: 优化后的角色序列
        """
        try:
            # 1. 基于依赖关系排序
            dependency_sorted = await self._sort_by_dependencies(roles)
            
            # 2. 基于任务特点调整
            task_optimized = await self._optimize_for_task(dependency_sorted, task_analysis)
            
            # 3. 基于性能历史调整
            performance_optimized = await self._optimize_for_performance(task_optimized)
            
            return performance_optimized
            
        except Exception as e:
            logger.error(f"角色序列优化失败: {e}")
            return roles  # 返回原始序列
    
    # ===== 私有方法 =====
    
    def _load_role_capabilities(self) -> Dict[str, RoleCapabilities]:
        """加载角色能力矩阵"""
        capabilities = {}
        available_roles = self.role_factory.get_available_roles()
        
        for role_name in available_roles:
            role = self.role_factory.create_role(role_name)
            if role:
                capabilities[role_name] = role.config.capabilities
        
        return capabilities
    
    def _get_recommendation_prompt_template(self) -> str:
        """获取推荐提示词模板"""
        return """
你是UAgent系统的角色推荐专家，负责基于任务分析推荐最优的专家角色组合。

## 任务分析结果
{task_analysis}

## 可用角色和能力
{available_roles}

## 角色能力详情
{role_capabilities}

## 推荐指导原则
1. **必需角色**: 任务完成绝对必要的角色
2. **可选角色**: 能提升质量但非严格必需的角色
3. **序列逻辑**: 为什么这个顺序对特定任务最优
4. **跳过条件**: 什么情况下某些角色可以跳过

## 多领域角色说明

### 软件开发领域
- **方案规划师**: 需求分析、架构设计、实施规划
- **编码专家**: 代码实现、技术开发、功能构建
- **测试工程师**: 质量保证、测试设计、bug检测
- **代码审查员**: 代码质量、安全审查、最佳实践

### 数据分析领域
- **数据分析师**: 数据处理、统计分析、模式识别
- **股票分析师**: 金融数据分析、市场研究、投资评估

### 内容创作领域
- **技术写作专家**: 技术文档、报告编写、内容结构化
- **调研分析师**: 信息收集、市场研究、竞争分析

### 信息处理领域
- **文档阅读专家**: 文档分析、信息提取、内容总结
- **知识整理专家**: 信息组织、知识结构化、内容策划

## 推荐策略
1. 根据任务主要领域选择核心角色
2. 考虑任务复杂度决定角色数量
3. 基于依赖关系确定执行顺序
4. 考虑质量要求决定可选角色

## 输出格式
请以JSON格式提供推荐结果：

```json
{{
    "recommended_sequence": ["角色1", "角色2", "角色3"],
    "mandatory_roles": ["角色1", "角色2"],
    "optional_roles": ["角色3"],
    "reasoning": {{
        "角色1": "为什么需要这个角色以及为什么排在第一位",
        "角色2": "为什么需要这个角色以及它的位置",
        "角色3": "为什么这个角色能增加价值"
    }},
    "skip_conditions": {{
        "角色3": "什么情况下可以跳过这个角色"
    }},
    "estimated_timeline": {{
        "角色1": "2-4小时",
        "角色2": "4-6小时",
        "角色3": "1-2小时"
    }},
    "success_metrics": [
        "清晰的技术规范",
        "可工作的实现",
        "全面的测试覆盖"
    ],
    "confidence_score": 0.9
}}
```

请提供你的推荐。
        """
    
    async def _pre_filter_roles(self, task_analysis: TaskAnalysis) -> List[str]:
        """基于规则预筛选角色"""
        candidate_roles = []
        
        # 基于主要领域筛选
        domain_role_map = {
            "software_development": ["方案规划师", "编码专家", "测试工程师", "代码审查员"],
            "data_analysis": ["数据分析师", "技术写作专家", "知识整理专家"],
            "financial_analysis": ["股票分析师", "调研分析师", "技术写作专家"],
            "content_creation": ["技术写作专家", "调研分析师", "知识整理专家"],
            "information_processing": ["文档阅读专家", "知识整理专家", "技术写作专家"]
        }
        
        primary_domain = task_analysis.primary_domain.value
        candidate_roles = domain_role_map.get(primary_domain, [])
        
        # 基于子领域进一步筛选
        if "financial" in task_analysis.sub_domains:
            if "股票分析师" not in candidate_roles:
                candidate_roles.append("股票分析师")
        
        if "documentation" in task_analysis.sub_domains:
            if "技术写作专家" not in candidate_roles:
                candidate_roles.append("技术写作专家")
        
        return candidate_roles
    
    async def _template_based_recommendation(self, task_analysis: TaskAnalysis) -> Optional[RoleRecommendation]:
        """基于模板的推荐"""
        try:
            # 查找匹配的工作流模板
            templates = {
                "software_development": StandardWorkflowTemplates.software_development_template(),
                "data_analysis": StandardWorkflowTemplates.data_analysis_template(),
                "financial_analysis": StandardWorkflowTemplates.financial_analysis_template(),
                "content_creation": StandardWorkflowTemplates.content_creation_template(),
                "document_processing": StandardWorkflowTemplates.document_processing_template()
            }
            
            domain = task_analysis.primary_domain.value
            template = templates.get(domain)
            
            if template and template.is_applicable(task_analysis):
                logger.info(f"使用模板推荐: {template.role_sequence}")
                return RoleRecommendation(
                    task_id=task_analysis.task_id,
                    recommended_sequence=template.role_sequence,
                    mandatory_roles=template.role_sequence,
                    optional_roles=template.optional_roles,
                    reasoning={role: f"模板推荐的{role}" for role in template.role_sequence},
                    success_metrics=template.success_criteria,
                    confidence_score=0.7,
                    recommendation_method="template_based"
                )
            
            logger.info("没有找到适用的工作流模板")
            return None
            
        except Exception as e:
            logger.warning(f"模板推荐失败: {e}")
            return None
    
    async def _is_llm_recommendation_valid(self, recommendation: RoleRecommendation) -> bool:
        """检测LLM推荐结果是否有效"""
        try:
            # 检查推荐序列不为空
            if not recommendation.recommended_sequence:
                logger.warning("LLM推荐序列为空")
                return False
            
            # 检查置信度是否合理
            if recommendation.confidence_score < 0.3:
                logger.warning(f"LLM推荐置信度过低: {recommendation.confidence_score}")
                return False
            
            # 检查推荐方法标识
            if recommendation.recommendation_method != "llm_based":
                logger.warning(f"LLM推荐方法标识错误: {recommendation.recommendation_method}")
                return False
            
            # 检查必需角色是否在推荐序列中
            for mandatory_role in recommendation.mandatory_roles:
                if mandatory_role not in recommendation.recommended_sequence:
                    logger.warning(f"必需角色不在推荐序列中: {mandatory_role}")
                    return False
            
            # 检查角色是否存在
            available_roles = self.role_factory.get_available_roles()
            for role in recommendation.recommended_sequence:
                if role not in available_roles:
                    logger.warning(f"推荐的角色不存在: {role}")
                    return False
            
            logger.info("LLM推荐结果验证通过")
            return True
            
        except Exception as e:
            logger.error(f"LLM推荐验证异常: {e}")
            return False

    async def _llm_based_recommendation(self, 
                                      task_analysis: TaskAnalysis,
                                      candidate_roles: List[str]) -> RoleRecommendation:
        """基于LLM的智能推荐"""
        try:
            # 准备角色信息
            role_info = {}
            for role_name in candidate_roles:
                role = self.role_factory.create_role(role_name)
                if role:
                    role_info[role_name] = {
                        "description": role.config.description,
                        "capabilities": role.config.capabilities.dict(),
                        "dependencies": role.config.dependencies.dict()
                    }
            
            # 构建提示词
            prompt = self.recommendation_prompt.format(
                task_analysis=task_analysis.model_dump_json(indent=2),
                available_roles=", ".join(candidate_roles),
                role_capabilities=json.dumps(role_info, indent=2, ensure_ascii=False)
            )
            
            # 调用LLM
            response = await self.llm.ainvoke(prompt)
            response_text = response.content
            
            # 解析推荐结果
            recommendation_data = await self._parse_recommendation_response(response_text)
            
            # 验证解析结果
            if not recommendation_data or "recommended_sequence" not in recommendation_data:
                logger.error("LLM响应解析失败，推荐数据不完整")
                raise ValueError("LLM推荐数据不完整")
            
            # 创建推荐对象
            recommendation = RoleRecommendation(
                task_id=task_analysis.task_id,
                recommendation_method="llm_based",
                **recommendation_data
            )
            
            logger.info(f"LLM推荐成功: {recommendation.recommended_sequence}")
            return recommendation
            
        except Exception as e:
            logger.error(f"LLM推荐失败: {e}, 堆栈信息: {traceback.format_exc()}")
            # 返回一个标记为无效的推荐对象，让调用方知道需要兜底
            return RoleRecommendation(
                task_id=task_analysis.task_id,
                recommended_sequence=[],
                mandatory_roles=[],
                optional_roles=[],
                reasoning={},
                success_metrics=[],
                confidence_score=0.0,
                recommendation_method="llm_based"
            )
    

    

    
    async def _calculate_single_role_fit(self, role_name: str, task_analysis: TaskAnalysis) -> float:
        """计算单个角色的匹配分数"""
        capabilities = self.role_capabilities.get(role_name)
        if not capabilities:
            return 0.0
        
        score = 0.0
        
        # 主领域匹配度 (40%)
        domain_match = task_analysis.primary_domain in capabilities.primary_domains
        score += 0.4 if domain_match else 0.0
        
        # 子领域匹配度 (20%)
        sub_domain_matches = sum(1 for sub in task_analysis.sub_domains 
                               if sub in capabilities.sub_domains)
        sub_domain_score = min(sub_domain_matches / max(len(capabilities.sub_domains), 1), 1.0)
        score += 0.2 * sub_domain_score
        
        # 复杂度偏好匹配 (20%)
        complexity_match = task_analysis.complexity_level in capabilities.complexity_preference
        score += 0.2 if complexity_match else 0.0
        
        # 任务类型匹配 (15%)
        task_type_match = task_analysis.task_type in capabilities.preferred_task_types
        score += 0.15 if task_type_match else 0.0
        
        # 输出需求匹配 (5%)
        output_matches = sum(1 for deliverable in task_analysis.primary_deliverables
                           if any(output in deliverable.lower() for output in capabilities.output_types))
        output_score = min(output_matches / max(len(task_analysis.primary_deliverables), 1), 1.0)
        score += 0.05 * output_score
        
        return score
    
    async def _parse_recommendation_response(self, response_text: str) -> Dict[str, Any]:
        """解析LLM推荐响应"""
        try:
            # 提取JSON部分
            import re
            json_match = re.search(r'```json\s*\n(.*?)\n```', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                json_text = response_text.strip()
            
            # 解析JSON
            recommendation_data = json.loads(json_text)
            
            # 验证必需字段
            required_fields = ["recommended_sequence", "mandatory_roles", "reasoning"]
            for field in required_fields:
                if field not in recommendation_data:
                    recommendation_data[field] = self._get_default_recommendation_value(field)
            
            return recommendation_data
            
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"推荐响应解析失败: {e}")
            # 使用启发式解析
            return await self._heuristic_parse_recommendation(response_text)
    
    async def _heuristic_parse_recommendation(self, response_text: str) -> Dict[str, Any]:
        """启发式解析推荐响应"""
        # 基于任务分析的简单推荐逻辑
        return {
            "recommended_sequence": ["方案规划师", "编码专家"],
            "mandatory_roles": ["编码专家"],
            "optional_roles": [],
            "reasoning": {
                "方案规划师": "需要进行需求分析和设计",
                "编码专家": "需要实现具体功能"
            },
            "skip_conditions": {},
            "estimated_timeline": {
                "方案规划师": "2-3小时",
                "编码专家": "4-6小时"
            },
            "success_metrics": ["功能实现", "质量达标"],
            "confidence_score": 0.5
        }
    
    def _get_default_recommendation_value(self, field: str) -> Any:
        """获取推荐字段默认值"""
        defaults = {
            "recommended_sequence": ["编码专家"],
            "mandatory_roles": ["编码专家"],
            "optional_roles": [],
            "reasoning": {"编码专家": "默认推荐"},
            "skip_conditions": {},
            "estimated_timeline": {"编码专家": "2-4小时"},
            "success_metrics": ["任务完成"],
            "confidence_score": 0.5
        }
        
        return defaults.get(field, "")
    
    async def _validate_recommendation(self, 
                                     recommendation: RoleRecommendation,
                                     task_analysis: TaskAnalysis) -> ValidationResult:
        """验证推荐结果"""
        errors = []
        warnings = []
        
        # 检查推荐序列不为空
        if not recommendation.recommended_sequence:
            errors.append("推荐角色序列不能为空")
        
        # 检查角色是否存在
        available_roles = self.role_factory.get_available_roles()
        for role in recommendation.recommended_sequence:
            if role not in available_roles:
                errors.append(f"推荐的角色不存在: {role}")
        
        # 检查必需角色是否在推荐序列中
        for role in recommendation.mandatory_roles:
            if role not in recommendation.recommended_sequence:
                errors.append(f"必需角色不在推荐序列中: {role}")
        
        # 检查置信度
        if recommendation.confidence_score < 0.3:
            warnings.append("推荐置信度过低")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            error_message="; ".join(errors) if errors else None,
            warnings=warnings
        )
    
    async def _generate_fallback_recommendation(self, task_analysis: TaskAnalysis) -> RoleRecommendation:
        """生成备用推荐"""
        logger.info(f"为任务{task_analysis.task_id}生成备用推荐")
        
        # 基于领域的简单推荐逻辑
        domain_fallbacks = {
            "software_development": ["方案规划师", "编码专家"],
            "data_analysis": ["数据分析师"],
            "financial_analysis": ["股票分析师"],
            "content_creation": ["技术写作专家"],
            "information_processing": ["文档阅读专家"]
        }
        
        domain = task_analysis.primary_domain.value
        fallback_roles = domain_fallbacks.get(domain, ["编码专家"])
        
        return RoleRecommendation(
            task_id=task_analysis.task_id,
            recommended_sequence=fallback_roles,
            mandatory_roles=fallback_roles,
            optional_roles=[],
            reasoning={role: f"备用推荐的{role}" for role in fallback_roles},
            success_metrics=["基本任务完成"],
            confidence_score=0.4,
            recommendation_method="fallback"
        )
    
    async def _sort_by_dependencies(self, roles: List[str]) -> List[str]:
        """基于依赖关系排序角色"""
        # 简化的拓扑排序实现
        dependencies = {
            "编码专家": ["方案规划师"],
            "测试工程师": ["编码专家"],
            "代码审查员": ["编码专家"],
            "技术写作专家": ["数据分析师", "股票分析师", "调研分析师"],
            "知识整理专家": ["文档阅读专家", "技术写作专家"]
        }
        
        sorted_roles = []
        remaining_roles = roles.copy()
        
        while remaining_roles:
            # 找到没有未满足依赖的角色
            ready_roles = []
            for role in remaining_roles:
                role_deps = dependencies.get(role, [])
                if all(dep in sorted_roles or dep not in roles for dep in role_deps):
                    ready_roles.append(role)
            
            if not ready_roles:
                # 如果没有准备好的角色，选择第一个（可能存在循环依赖）
                ready_roles = [remaining_roles[0]]
            
            # 添加准备好的角色
            for role in ready_roles:
                sorted_roles.append(role)
                remaining_roles.remove(role)
        
        return sorted_roles
    
    async def _optimize_for_task(self, roles: List[str], task_analysis: TaskAnalysis) -> List[str]:
        """基于任务特点优化角色序列"""
        optimized = roles.copy()
        
        # 如果是简单任务，可能不需要方案规划师
        if (task_analysis.complexity_level == ComplexityLevel.SIMPLE and 
            "方案规划师" in optimized and len(optimized) > 2):
            optimized.remove("方案规划师")
        
        # 如果是紧急任务，可能跳过代码审查
        if (task_analysis.task_type in ["bug_fix"] and 
            "代码审查员" in optimized):
            # 将代码审查员移到可选角色
            pass
        
        return optimized
    
    async def _optimize_for_performance(self, roles: List[str]) -> List[str]:
        """基于性能历史优化角色序列"""
        # 这里可以基于历史执行数据进行优化
        # 暂时返回原序列
        return roles
    
    def _generate_cache_key(self, task_analysis: TaskAnalysis) -> str:
        """生成缓存键"""
        key_components = [
            task_analysis.primary_domain.value,
            task_analysis.task_type.value,
            task_analysis.complexity_level.value,
            str(hash(str(task_analysis.sub_domains))),
            str(hash(str(task_analysis.functional_requirements)))
        ]
        
        return hash("|".join(key_components))
    
    async def _record_recommendation_history(self, 
                                           task_analysis: TaskAnalysis,
                                           recommendation: RoleRecommendation,
                                           execution_time: float):
        """记录推荐历史"""
        history_record = {
            "task_id": task_analysis.task_id,
            "task_analysis": task_analysis,
            "recommendation": recommendation,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }
        
        self.recommendation_history.append(history_record)
        
        # 保持历史记录在合理范围内
        if len(self.recommendation_history) > 1000:
            self.recommendation_history = self.recommendation_history[-500:]
    
    def clear_cache(self):
        """清理推荐缓存"""
        self.recommendation_cache.clear()
        logger.info("角色推荐缓存已清理")
    
    def get_recommendation_stats(self) -> Dict[str, Any]:
        """获取推荐统计"""
        if not self.recommendation_history:
            return {"message": "暂无推荐历史数据"}
        
        recent_recommendations = self.recommendation_history[-100:]
        
        # 统计推荐方法分布
        method_distribution = {}
        for rec in recent_recommendations:
            method = rec["recommendation"].recommendation_method
            method_distribution[method] = method_distribution.get(method, 0) + 1
        
        # 统计平均置信度
        avg_confidence = sum(r["recommendation"].confidence_score for r in recent_recommendations) / len(recent_recommendations)
        
        # 统计平均推荐时间
        avg_time = sum(r["execution_time"] for r in recent_recommendations) / len(recent_recommendations)
        
        return {
            "total_recommendations": len(self.recommendation_history),
            "recent_recommendations": len(recent_recommendations),
            "method_distribution": method_distribution,
            "average_confidence": avg_confidence,
            "average_recommendation_time": avg_time,
            "cache_size": len(self.recommendation_cache)
        }
