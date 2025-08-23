"""
UAgent Dependency Analyzer

依赖分析器 - 分析角色依赖关系和关键路径
"""

import asyncio
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
import structlog
from dataclasses import dataclass

from models.base import ValidationResult
from models.roles import RoleCapabilities, RoleDependencies, RoleFactory

logger = structlog.get_logger(__name__)


@dataclass
class CriticalPathAnalysis:
    """关键路径分析结果"""
    critical_roles: List[str]
    optional_roles: List[str]
    dependency_violations: List[str]
    execution_order: List[str]
    parallel_opportunities: List[List[str]]


@dataclass
class FailureImpactAssessment:
    """失败影响评估"""
    failed_role: str
    impact_level: str  # minor, moderate, critical
    blocked_roles: List[str]
    degraded_roles: List[str]
    recovery_options: List[str]
    estimated_delay: int  # 预估延迟时间(分钟)


class DependencyAnalyzer:
    """
    依赖分析器
    
    分析角色间的依赖关系，识别关键路径，评估失败影响
    """
    
    def __init__(self):
        """初始化依赖分析器"""
        self.role_factory = RoleFactory()
        self.dependency_graph = self._build_dependency_graph()
        self.analysis_cache: Dict[str, Any] = {}
        
        logger.info("依赖分析器初始化完成")
    
    async def validate_role_sequence(self, role_sequence: List[str]) -> ValidationResult:
        """
        验证角色序列的依赖关系
        
        Args:
            role_sequence: 角色序列
            
        Returns:
            ValidationResult: 验证结果
        """
        try:
            errors = []
            warnings = []
            
            # 检查每个角色的依赖关系
            for i, role in enumerate(role_sequence):
                dependencies = self.dependency_graph.get(role, {})
                
                # 检查强依赖
                strong_deps = dependencies.get("strong_dependencies", [])
                for dep in strong_deps:
                    if dep not in role_sequence:
                        errors.append(f"角色 {role} 的强依赖 {dep} 不在序列中")
                    elif role_sequence.index(dep) > i:
                        errors.append(f"角色 {role} 的强依赖 {dep} 应该在它之前执行")
                
                # 检查弱依赖
                weak_deps = dependencies.get("weak_dependencies", [])
                for dep in weak_deps:
                    if dep in role_sequence and role_sequence.index(dep) > i:
                        warnings.append(f"角色 {role} 的弱依赖 {dep} 建议在它之前执行")
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                error_message="; ".join(errors) if errors else None,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"角色序列验证失败: {e}")
            return ValidationResult(
                is_valid=False,
                error_message=f"验证过程出错: {str(e)}"
            )
    
    async def adjust_role_sequence(self, role_sequence: List[str]) -> List[str]:
        """
        调整角色序列以满足依赖关系
        
        Args:
            role_sequence: 原始角色序列
            
        Returns:
            List[str]: 调整后的角色序列
        """
        try:
            logger.info(f"调整角色序列: {role_sequence}")
            
            # 使用拓扑排序调整序列
            adjusted_sequence = await self._topological_sort(role_sequence)
            
            logger.info(f"序列调整完成: {adjusted_sequence}")
            return adjusted_sequence
            
        except Exception as e:
            logger.error(f"角色序列调整失败: {e}")
            return role_sequence  # 返回原序列
    
    async def analyze_critical_path(self, role_sequence: List[str]) -> CriticalPathAnalysis:
        """
        分析关键路径
        
        Args:
            role_sequence: 角色序列
            
        Returns:
            CriticalPathAnalysis: 关键路径分析结果
        """
        try:
            critical_roles = []
            optional_roles = []
            dependency_violations = []
            
            # 分析每个角色的关键性
            for role in role_sequence:
                if await self._is_critical_role(role, role_sequence):
                    critical_roles.append(role)
                else:
                    optional_roles.append(role)
            
            # 检查依赖违反
            dependency_violations = await self._check_dependency_violations(role_sequence)
            
            # 确定执行顺序
            execution_order = await self._determine_execution_order(role_sequence)
            
            # 识别并行机会
            parallel_opportunities = await self._identify_parallel_opportunities(role_sequence)
            
            return CriticalPathAnalysis(
                critical_roles=critical_roles,
                optional_roles=optional_roles,
                dependency_violations=dependency_violations,
                execution_order=execution_order,
                parallel_opportunities=parallel_opportunities
            )
            
        except Exception as e:
            logger.error(f"关键路径分析失败: {e}")
            return CriticalPathAnalysis(
                critical_roles=role_sequence,
                optional_roles=[],
                dependency_violations=[],
                execution_order=role_sequence,
                parallel_opportunities=[]
            )
    
    async def assess_failure_impact(self, 
                                  failed_role: str, 
                                  remaining_roles: List[str]) -> FailureImpactAssessment:
        """
        评估角色失败的影响
        
        Args:
            failed_role: 失败的角色
            remaining_roles: 剩余角色列表
            
        Returns:
            FailureImpactAssessment: 失败影响评估
        """
        try:
            blocked_roles = []
            degraded_roles = []
            recovery_options = []
            
            # 检查哪些角色会被阻塞
            for role in remaining_roles:
                dependencies = self.dependency_graph.get(role, {})
                
                if failed_role in dependencies.get("strong_dependencies", []):
                    blocked_roles.append(role)
                elif failed_role in dependencies.get("weak_dependencies", []):
                    degraded_roles.append(role)
            
            # 确定影响级别
            if blocked_roles:
                impact_level = "critical"
            elif degraded_roles:
                impact_level = "moderate"
            else:
                impact_level = "minor"
            
            # 生成恢复选项
            recovery_options = await self._generate_recovery_options(
                failed_role, blocked_roles, degraded_roles
            )
            
            # 估算延迟时间
            estimated_delay = await self._estimate_failure_delay(
                failed_role, blocked_roles, degraded_roles
            )
            
            return FailureImpactAssessment(
                failed_role=failed_role,
                impact_level=impact_level,
                blocked_roles=blocked_roles,
                degraded_roles=degraded_roles,
                recovery_options=recovery_options,
                estimated_delay=estimated_delay
            )
            
        except Exception as e:
            logger.error(f"失败影响评估失败: {e}")
            return FailureImpactAssessment(
                failed_role=failed_role,
                impact_level="unknown",
                blocked_roles=[],
                degraded_roles=[],
                recovery_options=["manual_intervention"],
                estimated_delay=60
            )
    
    async def find_alternative_paths(self, 
                                   failed_role: str,
                                   original_sequence: List[str]) -> List[List[str]]:
        """
        寻找替代执行路径
        
        Args:
            failed_role: 失败的角色
            original_sequence: 原始角色序列
            
        Returns:
            List[List[str]]: 替代路径列表
        """
        try:
            alternative_paths = []
            
            # 1. 跳过失败角色的路径
            skip_path = [role for role in original_sequence if role != failed_role]
            if await self._is_valid_path(skip_path):
                alternative_paths.append(skip_path)
            
            # 2. 替换失败角色的路径
            replacement_roles = await self._find_replacement_roles(failed_role)
            for replacement in replacement_roles:
                replacement_path = original_sequence.copy()
                failed_index = replacement_path.index(failed_role)
                replacement_path[failed_index] = replacement
                
                if await self._is_valid_path(replacement_path):
                    alternative_paths.append(replacement_path)
            
            # 3. 重新排序的路径
            if len(original_sequence) > 2:
                reordered_path = await self._try_reorder_sequence(original_sequence, failed_role)
                if reordered_path and await self._is_valid_path(reordered_path):
                    alternative_paths.append(reordered_path)
            
            return alternative_paths
            
        except Exception as e:
            logger.error(f"寻找替代路径失败: {e}")
            return []
    
    # ===== 私有方法 =====
    
    def _build_dependency_graph(self) -> Dict[str, Dict[str, List[str]]]:
        """构建依赖关系图"""
        dependency_graph = {}
        available_roles = self.role_factory.get_available_roles()
        
        for role_name in available_roles:
            role = self.role_factory.create_role(role_name)
            if role:
                dependency_graph[role_name] = {
                    "strong_dependencies": role.config.dependencies.strong_dependencies,
                    "weak_dependencies": role.config.dependencies.weak_dependencies,
                    "provides_for": role.config.dependencies.provides_for
                }
        
        return dependency_graph
    
    async def _topological_sort(self, roles: List[str]) -> List[str]:
        """拓扑排序"""
        # 构建角色子图
        in_degree = {role: 0 for role in roles}
        adj_list = {role: [] for role in roles}
        
        # 计算入度和邻接表
        for role in roles:
            dependencies = self.dependency_graph.get(role, {})
            strong_deps = dependencies.get("strong_dependencies", [])
            
            for dep in strong_deps:
                if dep in roles:
                    adj_list[dep].append(role)
                    in_degree[role] += 1
        
        # Kahn算法
        queue = [role for role in roles if in_degree[role] == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            for neighbor in adj_list[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # 如果存在循环依赖，添加剩余角色
        if len(result) < len(roles):
            remaining = [role for role in roles if role not in result]
            result.extend(remaining)
        
        return result
    
    async def _is_critical_role(self, role: str, role_sequence: List[str]) -> bool:
        """判断角色是否关键"""
        dependencies = self.dependency_graph.get(role, {})
        
        # 检查是否有其他角色强依赖于此角色
        for other_role in role_sequence:
            if other_role != role:
                other_deps = self.dependency_graph.get(other_role, {})
                if role in other_deps.get("strong_dependencies", []):
                    return True
        
        # 检查是否是起始角色（无强依赖）
        if not dependencies.get("strong_dependencies", []):
            return True
        
        return False
    
    async def _check_dependency_violations(self, role_sequence: List[str]) -> List[str]:
        """检查依赖违反"""
        violations = []
        
        for i, role in enumerate(role_sequence):
            dependencies = self.dependency_graph.get(role, {})
            strong_deps = dependencies.get("strong_dependencies", [])
            
            for dep in strong_deps:
                if dep not in role_sequence:
                    violations.append(f"角色 {role} 的强依赖 {dep} 不在序列中")
                elif role_sequence.index(dep) > i:
                    violations.append(f"角色 {role} 的强依赖 {dep} 应该在它之前")
        
        return violations
    
    async def _determine_execution_order(self, role_sequence: List[str]) -> List[str]:
        """确定执行顺序"""
        # 基于拓扑排序确定最优执行顺序
        return await self._topological_sort(role_sequence)
    
    async def _identify_parallel_opportunities(self, role_sequence: List[str]) -> List[List[str]]:
        """识别并行执行机会"""
        parallel_groups = []
        
        # 查找可以并行执行的角色组
        for i in range(len(role_sequence)):
            parallel_group = [role_sequence[i]]
            
            # 查找可以与当前角色并行的其他角色
            for j in range(i + 1, len(role_sequence)):
                candidate = role_sequence[j]
                
                # 检查是否可以并行
                if await self._can_execute_parallel(role_sequence[i], candidate, role_sequence):
                    parallel_group.append(candidate)
            
            if len(parallel_group) > 1:
                parallel_groups.append(parallel_group)
        
        return parallel_groups
    
    async def _can_execute_parallel(self, role1: str, role2: str, context_roles: List[str]) -> bool:
        """检查两个角色是否可以并行执行"""
        # 获取依赖关系
        deps1 = self.dependency_graph.get(role1, {})
        deps2 = self.dependency_graph.get(role2, {})
        
        # 检查是否存在直接依赖
        if role1 in deps2.get("strong_dependencies", []) or role1 in deps2.get("weak_dependencies", []):
            return False
        
        if role2 in deps1.get("strong_dependencies", []) or role2 in deps1.get("weak_dependencies", []):
            return False
        
        # 检查是否有共同的强依赖都已满足
        common_strong_deps = set(deps1.get("strong_dependencies", [])) & set(deps2.get("strong_dependencies", []))
        for dep in common_strong_deps:
            if dep in context_roles:
                dep_index = context_roles.index(dep)
                role1_index = context_roles.index(role1)
                role2_index = context_roles.index(role2)
                
                if dep_index > min(role1_index, role2_index):
                    return False
        
        return True
    
    async def _generate_recovery_options(self, 
                                       failed_role: str,
                                       blocked_roles: List[str],
                                       degraded_roles: List[str]) -> List[str]:
        """生成恢复选项"""
        options = []
        
        # 1. 重试选项
        options.append("retry")
        
        # 2. 跳过选项（如果影响不大）
        if not blocked_roles:
            options.append("skip")
        
        # 3. 替换选项
        replacement_roles = await self._find_replacement_roles(failed_role)
        if replacement_roles:
            options.append("replace")
        
        # 4. 手动干预选项
        options.append("manual_intervention")
        
        # 5. 工作流修改选项
        if blocked_roles:
            options.append("modify_workflow")
        
        return options
    
    async def _find_replacement_roles(self, failed_role: str) -> List[str]:
        """寻找替换角色"""
        replacements = []
        
        # 基于能力相似性寻找替换角色
        failed_role_obj = self.role_factory.create_role(failed_role)
        if not failed_role_obj:
            return replacements
        
        failed_capabilities = failed_role_obj.config.capabilities
        available_roles = self.role_factory.get_available_roles()
        
        for role_name in available_roles:
            if role_name == failed_role:
                continue
            
            role_obj = self.role_factory.create_role(role_name)
            if role_obj:
                similarity = await self._calculate_capability_similarity(
                    failed_capabilities, role_obj.config.capabilities
                )
                
                if similarity > 0.6:  # 相似度阈值
                    replacements.append(role_name)
        
        return replacements
    
    async def _calculate_capability_similarity(self, 
                                             cap1: RoleCapabilities,
                                             cap2: RoleCapabilities) -> float:
        """计算能力相似度"""
        # 领域相似度
        domain_similarity = len(set(cap1.primary_domains) & set(cap2.primary_domains)) / max(
            len(set(cap1.primary_domains) | set(cap2.primary_domains)), 1
        )
        
        # 子领域相似度
        sub_domain_similarity = len(set(cap1.sub_domains) & set(cap2.sub_domains)) / max(
            len(set(cap1.sub_domains) | set(cap2.sub_domains)), 1
        )
        
        # 输出类型相似度
        output_similarity = len(set(cap1.output_types) & set(cap2.output_types)) / max(
            len(set(cap1.output_types) | set(cap2.output_types)), 1
        )
        
        # 综合相似度
        similarity = (domain_similarity * 0.5 + sub_domain_similarity * 0.3 + output_similarity * 0.2)
        
        return similarity
    
    async def _estimate_failure_delay(self, 
                                    failed_role: str,
                                    blocked_roles: List[str],
                                    degraded_roles: List[str]) -> int:
        """估算失败导致的延迟"""
        base_delay = 30  # 基础延迟30分钟
        
        # 基于影响范围调整延迟
        impact_multiplier = 1.0
        
        if blocked_roles:
            impact_multiplier += len(blocked_roles) * 0.5
        
        if degraded_roles:
            impact_multiplier += len(degraded_roles) * 0.2
        
        # 基于角色重要性调整
        if failed_role in ["方案规划师", "编码专家"]:
            impact_multiplier *= 1.5
        
        return int(base_delay * impact_multiplier)
    
    async def _is_valid_path(self, role_sequence: List[str]) -> bool:
        """检查路径是否有效"""
        validation_result = await self.validate_role_sequence(role_sequence)
        return validation_result.is_valid
    
    async def _try_reorder_sequence(self, 
                                  original_sequence: List[str],
                                  failed_role: str) -> Optional[List[str]]:
        """尝试重新排序序列"""
        # 移除失败角色
        remaining_roles = [role for role in original_sequence if role != failed_role]
        
        # 重新排序
        reordered = await self._topological_sort(remaining_roles)
        
        return reordered if reordered != remaining_roles else None
    
    def get_dependency_graph(self) -> Dict[str, Dict[str, List[str]]]:
        """获取依赖关系图"""
        return self.dependency_graph.copy()
    
    def get_role_dependencies(self, role: str) -> Optional[Dict[str, List[str]]]:
        """获取角色依赖关系"""
        return self.dependency_graph.get(role)
    
    def visualize_dependencies(self) -> str:
        """可视化依赖关系"""
        lines = ["# 角色依赖关系图\n"]
        
        for role, deps in self.dependency_graph.items():
            lines.append(f"## {role}")
            
            strong_deps = deps.get("strong_dependencies", [])
            if strong_deps:
                lines.append(f"  强依赖: {', '.join(strong_deps)}")
            
            weak_deps = deps.get("weak_dependencies", [])
            if weak_deps:
                lines.append(f"  弱依赖: {', '.join(weak_deps)}")
            
            provides_for = deps.get("provides_for", [])
            if provides_for:
                lines.append(f"  提供给: {', '.join(provides_for)}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def get_dependency_stats(self) -> Dict[str, Any]:
        """获取依赖统计"""
        total_roles = len(self.dependency_graph)
        total_strong_deps = sum(len(deps.get("strong_dependencies", [])) 
                              for deps in self.dependency_graph.values())
        total_weak_deps = sum(len(deps.get("weak_dependencies", [])) 
                            for deps in self.dependency_graph.values())
        
        # 找出最复杂的角色（依赖最多）
        most_dependent_role = max(
            self.dependency_graph.keys(),
            key=lambda r: len(self.dependency_graph[r].get("strong_dependencies", []))
        )
        
        # 找出最重要的角色（被依赖最多）
        dependency_counts = {}
        for role, deps in self.dependency_graph.items():
            for dep in deps.get("strong_dependencies", []):
                dependency_counts[dep] = dependency_counts.get(dep, 0) + 1
        
        most_important_role = max(dependency_counts.keys(), key=lambda r: dependency_counts[r]) if dependency_counts else None
        
        return {
            "total_roles": total_roles,
            "total_strong_dependencies": total_strong_deps,
            "total_weak_dependencies": total_weak_deps,
            "average_dependencies_per_role": total_strong_deps / max(total_roles, 1),
            "most_dependent_role": most_dependent_role,
            "most_important_role": most_important_role,
            "dependency_counts": dependency_counts
        }
