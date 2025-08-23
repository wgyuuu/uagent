"""
Template Loader

模板加载器 - 从各种来源加载模板
"""

from typing import Dict, List, Any, Optional
import structlog
import json
import yaml
import aiofiles
from pathlib import Path
from datetime import datetime

logger = structlog.get_logger(__name__)


class TemplateLoader:
    """
    模板加载器
    
    从文件系统、数据库或远程源加载模板
    """
    
    def __init__(self, base_path: str = "templates"):
        self.base_path = Path(base_path)
        self.loaded_templates: Dict[str, Dict[str, Any]] = {}
        
        logger.info("模板加载器初始化完成")
    
    async def load_from_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """从文件加载模板"""
        try:
            full_path = self.base_path / file_path
            
            if not full_path.exists():
                logger.warning(f"模板文件不存在: {full_path}")
                return None
            
            async with aiofiles.open(full_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # 根据文件扩展名解析
            if full_path.suffix == '.json':
                template_data = json.loads(content)
            elif full_path.suffix in ['.yaml', '.yml']:
                template_data = yaml.safe_load(content)
            else:
                # 纯文本模板
                template_data = {
                    "content": content,
                    "metadata": {
                        "file_path": str(full_path),
                        "loaded_at": datetime.now().isoformat()
                    }
                }
            
            self.loaded_templates[file_path] = template_data
            logger.info(f"模板已加载: {file_path}")
            
            return template_data
            
        except Exception as e:
            logger.error(f"加载模板文件失败 {file_path}: {e}")
            return None
    
    async def load_from_directory(self, directory: str = ".") -> Dict[str, Dict[str, Any]]:
        """从目录加载所有模板"""
        try:
            dir_path = self.base_path / directory
            
            if not dir_path.exists():
                logger.warning(f"模板目录不存在: {dir_path}")
                return {}
            
            templates = {}
            
            # 扫描模板文件
            for file_path in dir_path.rglob("*"):
                if file_path.is_file() and file_path.suffix in ['.json', '.yaml', '.yml', '.txt', '.md', '.j2']:
                    relative_path = file_path.relative_to(self.base_path)
                    template_data = await self.load_from_file(str(relative_path))
                    
                    if template_data:
                        templates[str(relative_path)] = template_data
            
            logger.info(f"从目录 {directory} 加载了 {len(templates)} 个模板")
            return templates
            
        except Exception as e:
            logger.error(f"从目录加载模板失败 {directory}: {e}")
            return {}
    
    async def save_template(self, file_path: str, template_data: Dict[str, Any]):
        """保存模板到文件"""
        try:
            full_path = self.base_path / file_path
            
            # 确保目录存在
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 根据文件扩展名保存
            if full_path.suffix == '.json':
                content = json.dumps(template_data, indent=2, ensure_ascii=False)
            elif full_path.suffix in ['.yaml', '.yml']:
                content = yaml.dump(template_data, default_flow_style=False, allow_unicode=True)
            else:
                # 如果是字典且包含content字段，保存content
                if isinstance(template_data, dict) and 'content' in template_data:
                    content = template_data['content']
                else:
                    content = str(template_data)
            
            async with aiofiles.open(full_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            self.loaded_templates[file_path] = template_data
            logger.info(f"模板已保存: {file_path}")
            
        except Exception as e:
            logger.error(f"保存模板失败 {file_path}: {e}")
            raise
    
    def get_loaded_template(self, file_path: str) -> Optional[Dict[str, Any]]:
        """获取已加载的模板"""
        return self.loaded_templates.get(file_path)
    
    def list_loaded_templates(self) -> List[str]:
        """列出已加载的模板"""
        return list(self.loaded_templates.keys())
    
    def clear_cache(self):
        """清空缓存"""
        self.loaded_templates.clear()
        logger.info("模板缓存已清空")
