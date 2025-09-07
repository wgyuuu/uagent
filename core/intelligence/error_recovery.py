"""
UAgent Error Recovery Controller

错误恢复控制器 - 智能错误分类和恢复策略生成
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog
from langchain.llms.base import BaseLLM
from langchain.prompts import PromptTemplate

from models.base import (
    ErrorClassification, RecoveryStrategy, RecoveryDecision,
    WorkflowExecution, ErrorSeverity
)
from .dependency_analyzer import FailureImpactAssessment
from tools.llm import LLMManager

logger = structlog.get_logger(__name__)


class ErrorRecoveryController:
    """
    错误恢复控制器
    
    负责错误分类、恢复策略生成和恢复决策制定
    """
    
    def __init__(self):
        """
        初始化错误恢复控制器
        """
        # 直接使用模块级函数获取LLM实例
        from tools.llm import get_llm_for_scene
        self.llm = get_llm_for_scene("error_recovery")
        self.recovery_history: List[Dict[str, Any]] = []
        self.recovery_strategies_cache: Dict[str, List[RecoveryStrategy]] = {}
        
        # 错误分类提示词模板
        self.classification_prompt = PromptTemplate(
            template=self._get_classification_prompt_template(),
            input_variables=["failed_role", "error_type", "error_message", "context"]
        )
        
        # 恢复策略生成提示词模板
        self.strategy_prompt = PromptTemplate(
            template=self._get_strategy_prompt_template(),
            input_variables=["error_classification", "workflow_context", "dependency_impact"]
        )
        
        logger.info("错误恢复控制器初始化完成")
    
    async def classify_error(self, 
                           failed_role: str,
                           error: Exception,
                           context: Dict[str, Any]) -> ErrorClassification:
        """
        分类错误
        
        Args:
            failed_role: 失败的角色
            error: 错误对象
            context: 错误上下文
            
        Returns:
            ErrorClassification: 错误分类结果
        """
        try:
            logger.info(f"开始错误分类: 角色={failed_role}, 错误类型={type(error).__name__}")
            
            # 构建分类提示词
            prompt = self.classification_prompt.format(
                failed_role=failed_role,
                error_type=type(error).__name__,
                error_message=str(error),
                context=json.dumps(context, indent=2, default=str)
            )
            
            # 调用LLM进行分类
            response = await self.llm.ainvoke(prompt)
            classification_text = response.content
            
            # 解析分类结果
            classification_data = await self._parse_classification_response(classification_text)
            
            # 创建错误分类对象
            error_classification = ErrorClassification(
                failed_role=failed_role,
                error_type=type(error).__name__,
                error_message=str(error),
                **classification_data
            )
            
            logger.info(f"错误分类完成: 严重程度={error_classification.severity}")
            return error_classification
            
        except Exception as e:
            logger.error(f"错误分类失败: {e}")
            
            # 生成默认分类
            return ErrorClassification(
                failed_role=failed_role,
                error_type=type(error).__name__,
                error_message=str(error),
                severity=ErrorSeverity.MAJOR,
                category="technical",
                recovery_feasibility="moderately_recoverable",
                workflow_impact="blocks_dependent",
                confidence_score=0.3
            )
    
    async def generate_recovery_strategies(self, 
                                         error_classification: ErrorClassification,
                                         workflow: WorkflowExecution,
                                         impact_assessment: FailureImpactAssessment) -> List[RecoveryStrategy]:
        """
        生成恢复策略
        
        Args:
            error_classification: 错误分类结果
            workflow: 工作流执行实例
            impact_assessment: 失败影响评估
            
        Returns:
            List[RecoveryStrategy]: 恢复策略列表
        """
        try:
            logger.info(f"生成恢复策略: 错误={error_classification.error_id}")
            
            # 检查错误修复适用性
            if error_classification.error_recovery_applicable == "requires_system_fix":
                logger.warning(f"错误 {error_classification.error_id} 属于系统级错误，无法通过错误修复功能解决")
                return []
            
            if error_classification.error_recovery_applicable == "requires_manual_intervention":
                logger.info(f"错误 {error_classification.error_id} 需要人工干预，不生成自动恢复策略")
                return []
            
            # 检查缓存
            cache_key = self._generate_strategy_cache_key(error_classification, impact_assessment)
            if cache_key in self.recovery_strategies_cache:
                return self.recovery_strategies_cache[cache_key]
            
            # 1. 基于规则的策略生成
            rule_based_strategies = await self._generate_rule_based_strategies(
                error_classification, impact_assessment
            )
            
            # 2. 基于LLM的策略生成
            llm_strategies = await self._generate_llm_based_strategies(
                error_classification, workflow, impact_assessment
            )
            
            # 3. 融合策略
            all_strategies = rule_based_strategies + llm_strategies
            
            # 4. 去重和排序
            unique_strategies = await self._deduplicate_and_rank_strategies(all_strategies)
            
            # 5. 缓存结果
            self.recovery_strategies_cache[cache_key] = unique_strategies
            
            logger.info(f"生成了{len(unique_strategies)}个恢复策略")
            return unique_strategies
            
        except Exception as e:
            logger.error(f"恢复策略生成失败: {e}")
            
            # 生成默认策略
            return await self._generate_default_strategies(error_classification)
    
    async def make_recovery_decision(self, 
                                   error_classification: ErrorClassification,
                                   recovery_strategies: List[RecoveryStrategy],
                                   workflow: WorkflowExecution) -> RecoveryDecision:
        """
        制定恢复决策
        
        Args:
            error_classification: 错误分类
            recovery_strategies: 恢复策略列表
            workflow: 工作流实例
            
        Returns:
            RecoveryDecision: 恢复决策
        """
        try:
            logger.info(f"制定恢复决策: 错误={error_classification.error_id}")
            
            # 1. 评估自动恢复可能性
            auto_recovery_feasible = await self._assess_auto_recovery_feasibility(
                error_classification, recovery_strategies
            )
            
            if auto_recovery_feasible:
                # 2. 选择最优策略
                best_strategy = await self._select_best_strategy(recovery_strategies)
                
                decision = RecoveryDecision(
                    decision_type="automatic",
                    selected_strategy=best_strategy,
                    rationale=f"错误可自动恢复，使用策略: {best_strategy.name}",
                    confidence_score=best_strategy.feasibility_score,
                    requires_user_approval=False
                )
            else:
                # 3. 需要手动干预
                decision = RecoveryDecision(
                    decision_type="manual_intervention",
                    available_options=recovery_strategies,
                    rationale="错误复杂或风险较高，需要人工决策",
                    confidence_score=0.8,
                    requires_user_approval=True
                )
            
            # 4. 记录决策历史
            await self._record_recovery_history(error_classification, decision)
            
            logger.info(f"恢复决策完成: 类型={decision.decision_type}")
            return decision
            
        except Exception as e:
            logger.error(f"恢复决策制定失败: {e}")
            
            # 默认决策：手动干预
            return RecoveryDecision(
                decision_type="manual_intervention",
                rationale=f"决策制定失败，需要手动干预: {str(e)}",
                confidence_score=0.3
            )
    
    # ===== 私有方法 =====
    
    def _get_classification_prompt_template(self) -> str:
        """获取错误分类提示词模板"""
        return """
你是UAgent系统的错误分析专家，负责分析和分类系统错误。

## 错误信息
- **失败角色**: {failed_role}
- **错误类型**: {error_type}
- **错误消息**: {error_message}
- **上下文**: {context}

## 重要说明
⚠️ **错误修复限制**: 错误修复功能仅限于修复任务执行过程中的决策错误，不适用于系统级错误。

## 分类框架
请按以下维度对错误进行分类：

### 1. 错误严重程度
- **critical**: 系统级错误，系统自身问题，无法继续执行，不属于错误修复范围
- **major**: 重要功能受影响，但可能有变通方案
- **minor**: 影响有限，可以稍后处理
- **trivial**: 外观或非功能性问题

### 2. 错误类别
- **system_bug**: 系统级错误，系统自身问题，无法通过错误修复解决
- **task_decision_error**: 任务执行过程中的决策错误，属于错误修复范围
- **technical**: 代码错误、配置问题、技术故障
- **resource**: 缺少依赖、访问问题、资源约束
- **logic**: 需求理解错误、设计缺陷
- **external**: 第三方服务故障、网络问题
- **user**: 用户输入错误、权限问题

### 3. 恢复可行性
- **easily_recoverable**: 简单修复，重试可能成功（仅适用于任务决策错误）
- **moderately_recoverable**: 需要一些干预，中等努力（仅适用于任务决策错误）
- **difficult_to_recover**: 需要复杂修复，高努力（仅适用于任务决策错误）
- **non_recoverable**: 根本性问题，需要重新设计或系统修复

### 4. 工作流影响
- **blocks_all**: 整个工作流无法继续
- **blocks_dependent**: 只有依赖此角色的角色被阻塞
- **degrades_quality**: 工作流可以继续但质量降低
- **no_impact**: 其他角色可以正常进行

### 5. 错误修复适用性
- **fixable_by_error_recovery**: 可以通过错误修复功能解决（仅限任务决策错误）
- **requires_system_fix**: 需要系统级修复，不属于错误修复范围
- **requires_manual_intervention**: 需要人工干预和指导

## 分类指导原则
1. 如果错误是系统运行报错、系统bug、系统自身问题，应分类为：
   - severity: critical
   - category: system_bug
   - recovery_feasibility: non_recoverable
   - 错误修复适用性: requires_system_fix

2. 如果错误是任务执行过程中的决策错误，应分类为：
   - severity: major 或 minor
   - category: task_decision_error
   - recovery_feasibility: easily_recoverable 或 moderately_recoverable
   - 错误修复适用性: fixable_by_error_recovery

## 输出格式
请以JSON格式提供分类结果：

```json
{{
    "severity": "错误严重程度",
    "category": "错误类别",
    "recovery_feasibility": "恢复可行性",
    "workflow_impact": "工作流影响",
    "error_recovery_applicable": "错误修复适用性",
    "blocked_roles": ["被阻塞的角色"],
    "degraded_roles": ["降级的角色"],
    "confidence_score": 0.9,
    "analysis_notes": "详细分析说明"
}}
```
        """
    
    def _get_strategy_prompt_template(self) -> str:
        """获取策略生成提示词模板"""
        return """
你是UAgent系统的恢复策略专家，负责为错误情况生成恢复策略。

## 重要说明
⚠️ **错误修复限制**: 错误修复功能仅限于修复任务执行过程中的决策错误，不适用于系统级错误。

## 错误分类结果
{error_classification}

## 工作流上下文
{workflow_context}

## 依赖影响分析
{dependency_impact}

## 错误修复适用性检查
在生成恢复策略之前，请确认错误是否属于错误修复范围：

- **fixable_by_error_recovery**: 可以通过错误修复功能解决（仅限任务决策错误）
- **requires_system_fix**: 需要系统级修复，不属于错误修复范围
- **requires_manual_intervention**: 需要人工干预和指导

## 可用恢复选项（仅适用于可修复的错误）
1. **retry**: 使用相同或修改的参数重试同一角色
2. **skip**: 跳过此角色，继续下一个角色
3. **replace**: 用类似能力的角色替换失败角色
4. **manual_intervention**: 暂停等待人工干预和指导
5. **workflow_modification**: 调整工作流序列或参数
6. **abort**: 终止整个工作流

## 策略生成指导
**重要**: 只有错误修复适用性为 "fixable_by_error_recovery" 的错误才能生成恢复策略。

为每个可行的恢复选项提供：
- **可行性**: 成功的可能性
- **风险评估**: 潜在的负面后果
- **资源需求**: 时间、精力或资源需求
- **成功标准**: 如何判断策略是否有效

## 输出格式
请以JSON格式提供策略：

```json
{{
    "strategies": [
        {{
            "name": "策略名称",
            "description": "策略描述",
            "action_type": "操作类型",
            "feasibility_score": 0.8,
            "risk_level": "风险级别",
            "success_probability": 0.7,
            "required_resources": ["资源1", "资源2"],
            "parameters": {{"参数": "值"}},
            "success_criteria": ["成功标准1", "成功标准2"]
        }}
    ],
    "recommended_strategy": "推荐的策略名称",
    "confidence_score": 0.9,
    "error_recovery_applicable": "错误修复适用性状态"
}}
```

## 特殊情况处理
如果错误不属于错误修复范围（如系统级错误），请返回：
```json
{{
    "strategies": [],
    "recommended_strategy": "none",
    "confidence_score": 0.0,
    "error_recovery_applicable": "requires_system_fix",
    "reason": "此错误属于系统级错误，无法通过错误修复功能解决"
}}
```
        """
    
    async def _parse_classification_response(self, response_text: str) -> Dict[str, Any]:
        """解析错误分类响应"""
        try:
            # 提取JSON部分
            import re
            json_match = re.search(r'```json\s*\n(.*?)\n```', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                json_text = response_text.strip()
            
            classification_data = json.loads(json_text)
            
            # 验证必需字段
            required_fields = ["severity", "category", "recovery_feasibility", "workflow_impact"]
            for field in required_fields:
                if field not in classification_data:
                    classification_data[field] = self._get_default_classification_value(field)
            
            return classification_data
            
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"分类响应解析失败: {e}")
            return await self._heuristic_classify_error(response_text)
    
    async def _heuristic_classify_error(self, response_text: str) -> Dict[str, Any]:
        """启发式错误分类"""
        text_lower = response_text.lower()
        
        # 严重程度识别
        if any(keyword in text_lower for keyword in ["critical", "严重", "致命", "崩溃"]):
            severity = "critical"
        elif any(keyword in text_lower for keyword in ["major", "重要", "主要"]):
            severity = "major"
        elif any(keyword in text_lower for keyword in ["minor", "轻微", "小"]):
            severity = "minor"
        else:
            severity = "major"  # 默认为主要错误
        
        # 类别识别
        if any(keyword in text_lower for keyword in ["network", "connection", "网络", "连接"]):
            category = "external"
        elif any(keyword in text_lower for keyword in ["permission", "auth", "权限", "认证"]):
            category = "user"
        elif any(keyword in text_lower for keyword in ["resource", "memory", "disk", "资源"]):
            category = "resource"
        else:
            category = "technical"
        
        # 错误修复适用性识别
        if severity == "critical" or any(keyword in text_lower for keyword in ["system", "bug", "崩溃", "系统"]):
            error_recovery_applicable = "requires_system_fix"
        elif any(keyword in text_lower for keyword in ["decision", "决策", "选择", "判断"]):
            error_recovery_applicable = "fixable_by_error_recovery"
        else:
            error_recovery_applicable = "requires_manual_intervention"
        
        return {
            "severity": severity,
            "category": category,
            "recovery_feasibility": "moderately_recoverable",
            "workflow_impact": "blocks_dependent",
            "error_recovery_applicable": error_recovery_applicable,
            "blocked_roles": [],
            "degraded_roles": [],
            "confidence_score": 0.5
        }
    
    async def _generate_rule_based_strategies(self, 
                                            error_classification: ErrorClassification,
                                            impact_assessment: FailureImpactAssessment) -> List[RecoveryStrategy]:
        """基于规则生成恢复策略"""
        strategies = []
        
        # 1. 重试策略
        if error_classification.recovery_feasibility in ["easily_recoverable", "moderately_recoverable"]:
            retry_strategy = RecoveryStrategy(
                name="重试执行",
                description=f"重新执行失败的角色: {error_classification.failed_role}",
                action_type="retry",
                feasibility_score=0.7 if error_classification.recovery_feasibility == "easily_recoverable" else 0.5,
                risk_level="low" if error_classification.severity in ["minor", "trivial"] else "medium",
                success_probability=0.6,
                required_resources=["compute"],
                parameters={"retry_count": 1, "delay_seconds": 5},
                success_criteria=["角色执行成功", "无新错误产生"]
            )
            strategies.append(retry_strategy)
        
        # 2. 跳过策略
        if not impact_assessment.blocked_roles:
            skip_strategy = RecoveryStrategy(
                name="跳过角色",
                description=f"跳过失败的角色: {error_classification.failed_role}",
                action_type="skip",
                feasibility_score=0.8,
                risk_level="medium",
                success_probability=0.7,
                required_resources=[],
                parameters={"skip_role": error_classification.failed_role},
                success_criteria=["工作流继续执行", "后续角色正常运行"]
            )
            strategies.append(skip_strategy)
        
        # 3. 手动干预策略
        manual_strategy = RecoveryStrategy(
            name="手动干预",
            description="暂停工作流，等待人工干预",
            action_type="manual_intervention",
            feasibility_score=0.9,
            risk_level="low",
            success_probability=0.8,
            required_resources=["human_operator"],
            parameters={"intervention_type": "error_resolution"},
            success_criteria=["问题得到解决", "工作流可以继续"]
        )
        strategies.append(manual_strategy)
        
        return strategies
    
    async def _generate_llm_based_strategies(self, 
                                           error_classification: ErrorClassification,
                                           workflow: WorkflowExecution,
                                           impact_assessment: FailureImpactAssessment) -> List[RecoveryStrategy]:
        """基于LLM生成恢复策略"""
        try:
            # 准备上下文
            workflow_context = {
                "workflow_id": workflow.workflow_id,
                "current_role_index": workflow.current_role_index,
                "remaining_roles": workflow.get_remaining_roles(),
                "completed_roles": workflow.roles[:workflow.current_role_index],
                "total_execution_time": workflow.total_execution_time
            }
            
            # 构建策略生成提示词
            prompt = self.strategy_prompt.format(
                error_classification=error_classification.model_dump_json(indent=2),
                workflow_context=json.dumps(workflow_context, indent=2, default=str),
                dependency_impact=impact_assessment.__dict__
            )
            
            # 调用LLM生成策略
            response = await self.llm.ainvoke(prompt)
            strategy_text = response.content
            
            # 解析策略
            strategy_data = await self._parse_strategy_response(strategy_text)
            
            # 创建策略对象
            strategies = []
            for strategy_info in strategy_data.get("strategies", []):
                strategy = RecoveryStrategy(**strategy_info)
                strategies.append(strategy)
            
            return strategies
            
        except Exception as e:
            logger.error(f"LLM策略生成失败: {e}")
            return []
    
    async def _parse_strategy_response(self, response_text: str) -> Dict[str, Any]:
        """解析策略响应"""
        try:
            # 提取JSON部分
            import re
            json_match = re.search(r'```json\s*\n(.*?)\n```', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                json_text = response_text.strip()
            
            strategy_data = json.loads(json_text)
            
            # 验证策略格式
            if "strategies" not in strategy_data:
                strategy_data = {"strategies": []}
            
            return strategy_data
            
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"策略响应解析失败: {e}")
            return {"strategies": []}
    
    async def _assess_auto_recovery_feasibility(self, 
                                              error_classification: ErrorClassification,
                                              strategies: List[RecoveryStrategy]) -> bool:
        """评估自动恢复可行性"""
        # 检查错误修复适用性
        if error_classification.error_recovery_applicable == "requires_system_fix":
            logger.info(f"错误 {error_classification.error_id} 属于系统级错误，无法自动恢复")
            return False
        
        if error_classification.error_recovery_applicable == "requires_manual_intervention":
            logger.info(f"错误 {error_classification.error_id} 需要人工干预，无法自动恢复")
            return False
        
        # 严重错误需要人工干预
        if error_classification.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.MAJOR]:
            return False
        
        # 难以恢复的错误需要人工干预
        if error_classification.recovery_feasibility in ["difficult_to_recover", "non_recoverable"]:
            return False
        
        # 检查是否有高可信度的恢复策略
        high_confidence_strategies = [
            s for s in strategies 
            if s.feasibility_score > 0.7 and s.risk_level in ["low", "medium"]
        ]
        
        return len(high_confidence_strategies) > 0
    
    async def _select_best_strategy(self, strategies: List[RecoveryStrategy]) -> RecoveryStrategy:
        """选择最优策略"""
        if not strategies:
            raise ValueError("没有可用的恢复策略")
        
        # 计算策略综合分数
        def calculate_score(strategy: RecoveryStrategy) -> float:
            return (
                strategy.feasibility_score * 0.5 +
                strategy.success_probability * 0.3 +
                (1.0 - {"low": 0.1, "medium": 0.5, "high": 0.9}.get(strategy.risk_level, 0.5)) * 0.2
            )
        
        # 选择得分最高的策略
        best_strategy = max(strategies, key=calculate_score)
        return best_strategy
    
    async def _deduplicate_and_rank_strategies(self, strategies: List[RecoveryStrategy]) -> List[RecoveryStrategy]:
        """去重和排序策略"""
        # 基于action_type去重
        unique_strategies = {}
        for strategy in strategies:
            key = strategy.action_type
            if key not in unique_strategies or strategy.feasibility_score > unique_strategies[key].feasibility_score:
                unique_strategies[key] = strategy
        
        # 按可行性分数排序
        sorted_strategies = sorted(
            unique_strategies.values(),
            key=lambda s: s.feasibility_score,
            reverse=True
        )
        
        return sorted_strategies[:5]  # 最多返回5个策略
    
    async def _generate_default_strategies(self, error_classification: ErrorClassification) -> List[RecoveryStrategy]:
        """生成默认恢复策略"""
        # 检查错误修复适用性
        if error_classification.error_recovery_applicable == "requires_system_fix":
            logger.warning(f"错误 {error_classification.error_id} 属于系统级错误，不生成默认恢复策略")
            return []
        
        if error_classification.error_recovery_applicable == "requires_manual_intervention":
            logger.info(f"错误 {error_classification.error_id} 需要人工干预，不生成默认恢复策略")
            return []
        
        default_strategies = [
            RecoveryStrategy(
                name="手动干预",
                description="暂停工作流，等待人工处理",
                action_type="manual_intervention",
                feasibility_score=0.9,
                risk_level="low",
                success_probability=0.8,
                required_resources=["human_operator"],
                success_criteria=["问题解决", "工作流恢复"]
            )
        ]
        
        # 如果错误不太严重，添加重试策略
        if error_classification.severity in [ErrorSeverity.MINOR, ErrorSeverity.TRIVIAL]:
            retry_strategy = RecoveryStrategy(
                name="简单重试",
                description="重试失败的角色",
                action_type="retry",
                feasibility_score=0.6,
                risk_level="medium",
                success_probability=0.5,
                required_resources=["compute"],
                success_criteria=["重试成功"]
            )
            default_strategies.insert(0, retry_strategy)
        
        return default_strategies
    
    def _get_default_classification_value(self, field: str) -> str:
        """获取分类字段默认值"""
        defaults = {
            "severity": "major",
            "category": "technical", 
            "recovery_feasibility": "moderately_recoverable",
            "workflow_impact": "blocks_dependent",
            "error_recovery_applicable": "requires_manual_intervention"
        }
        
        return defaults.get(field, "unknown")
    
    def _generate_strategy_cache_key(self, 
                                   error_classification: ErrorClassification,
                                   impact_assessment: FailureImpactAssessment) -> str:
        """生成策略缓存键"""
        key_components = [
            error_classification.severity.value,
            error_classification.category,
            error_classification.recovery_feasibility,
            error_classification.error_recovery_applicable,
            impact_assessment.impact_level,
            str(len(impact_assessment.blocked_roles)),
            str(len(impact_assessment.degraded_roles))
        ]
        
        return hash("|".join(key_components))
    
    async def _record_recovery_history(self, 
                                     error_classification: ErrorClassification,
                                     decision: RecoveryDecision):
        """记录恢复历史"""
        history_record = {
            "error_id": error_classification.error_id,
            "decision_id": decision.decision_id,
            "error_classification": error_classification,
            "decision": decision,
            "timestamp": datetime.now().isoformat()
        }
        
        self.recovery_history.append(history_record)
        
        # 保持历史记录在合理范围内
        if len(self.recovery_history) > 1000:
            self.recovery_history = self.recovery_history[-500:]
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """获取恢复统计"""
        if not self.recovery_history:
            return {"message": "暂无恢复历史数据"}
        
        recent_recoveries = self.recovery_history[-100:]
        
        # 统计决策类型分布
        decision_types = {}
        for recovery in recent_recoveries:
            decision_type = recovery["decision"].decision_type
            decision_types[decision_type] = decision_types.get(decision_type, 0) + 1
        
        # 统计错误严重程度分布
        severity_distribution = {}
        for recovery in recent_recoveries:
            severity = recovery["error_classification"].severity.value
            severity_distribution[severity] = severity_distribution.get(severity, 0) + 1
        
        # 统计恢复成功率（这里需要外部反馈）
        # 暂时使用模拟数据
        success_rate = 0.8  # 假设80%的恢复成功率
        
        return {
            "total_recoveries": len(self.recovery_history),
            "recent_recoveries": len(recent_recoveries),
            "decision_type_distribution": decision_types,
            "severity_distribution": severity_distribution,
            "estimated_success_rate": success_rate,
            "cache_size": len(self.recovery_strategies_cache)
        }
    
    def clear_cache(self):
        """清理缓存"""
        self.recovery_strategies_cache.clear()
        logger.info("错误恢复缓存已清理")
