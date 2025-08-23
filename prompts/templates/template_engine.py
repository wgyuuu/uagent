"""
Template Engine

模板引擎 - 高级模板渲染和处理功能
"""

from typing import Dict, List, Any, Optional, Callable
import structlog
import re
import json
from datetime import datetime
from jinja2 import Environment, BaseLoader, Template

logger = structlog.get_logger(__name__)


class TemplateEngine:
    """
    模板引擎
    
    提供高级模板渲染和处理功能
    """
    
    def __init__(self):
        self.custom_filters: Dict[str, Callable] = {}
        self.custom_functions: Dict[str, Callable] = {}
        self.template_cache: Dict[str, Template] = {}
        
        # 初始化默认过滤器和函数
        self._register_default_filters()
        self._register_default_functions()
        
        logger.info("模板引擎初始化完成")
    
    def _register_default_filters(self):
        """注册默认过滤器"""
        self.custom_filters.update({
            'timestamp': lambda x, fmt='%Y-%m-%d %H:%M:%S': 
                x.strftime(fmt) if isinstance(x, datetime) else str(x),
            'truncate': lambda x, length=50: x[:length] + '...' if len(str(x)) > length else str(x),
            'capitalize_words': lambda x: ' '.join(word.capitalize() for word in str(x).split()),
            'remove_html': lambda x: re.sub(r'<[^>]+>', '', str(x)),
            'json_pretty': lambda x: json.dumps(x, indent=2, ensure_ascii=False) if x else ''
        })
    
    def _register_default_functions(self):
        """注册默认函数"""
        self.custom_functions.update({
            'now': lambda: datetime.now(),
            'range': range,
            'len': len,
            'max': max,
            'min': min,
            'sum': sum
        })
    
    def register_filter(self, name: str, filter_func: Callable):
        """注册自定义过滤器"""
        self.custom_filters[name] = filter_func
        logger.info(f"自定义过滤器已注册: {name}")
    
    def register_function(self, name: str, func: Callable):
        """注册自定义函数"""
        self.custom_functions[name] = func
        logger.info(f"自定义函数已注册: {name}")
    
    async def render_template(
        self,
        template_content: str,
        variables: Dict[str, Any],
        cache_key: Optional[str] = None
    ) -> str:
        """渲染模板"""
        try:
            # 检查缓存
            if cache_key and cache_key in self.template_cache:
                template = self.template_cache[cache_key]
            else:
                # 创建Jinja2环境
                env = Environment(loader=BaseLoader())
                
                # 注册自定义过滤器
                for name, filter_func in self.custom_filters.items():
                    env.filters[name] = filter_func
                
                # 注册自定义函数
                env.globals.update(self.custom_functions)
                
                # 编译模板
                template = env.from_string(template_content)
                
                # 缓存模板
                if cache_key:
                    self.template_cache[cache_key] = template
            
            # 渲染模板
            return template.render(**variables)
            
        except Exception as e:
            logger.error(f"渲染模板失败: {e}")
            raise
    
    def clear_cache(self):
        """清空模板缓存"""
        self.template_cache.clear()
        logger.info("模板缓存已清空")
