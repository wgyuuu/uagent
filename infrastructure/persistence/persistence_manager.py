"""
Persistence Manager

持久化管理器 - 管理系统数据持久化和存储
"""

from typing import Dict, List, Any, Optional, Union, Type
import structlog
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
import pickle
from abc import ABC, abstractmethod

logger = structlog.get_logger(__name__)


@dataclass
class StorageConfig:
    """存储配置"""
    storage_type: str  # "database", "file", "cache", "hybrid"
    database_url: Optional[str] = None
    file_path: Optional[str] = None
    cache_config: Optional[Dict[str, Any]] = None
    backup_enabled: bool = True
    backup_interval: int = 3600  # 秒
    compression_enabled: bool = False
    encryption_enabled: bool = False


class StorageInterface(ABC):
    """存储接口抽象类"""
    
    @abstractmethod
    async def save(self, key: str, data: Any) -> bool:
        """保存数据"""
        pass
    
    @abstractmethod
    async def load(self, key: str) -> Optional[Any]:
        """加载数据"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除数据"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查数据是否存在"""
        pass
    
    @abstractmethod
    async def list_keys(self, pattern: str = "*") -> List[str]:
        """列出匹配的键"""
        pass


class DatabaseStorage(StorageInterface):
    """数据库存储实现"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.connection = None
        
        logger.info(f"数据库存储初始化: {database_url}")
    
    async def save(self, key: str, data: Any) -> bool:
        """保存数据到数据库"""
        try:
            # 这里应该实现具体的数据库操作
            # 目前只是模拟
            logger.info(f"保存数据到数据库: {key}")
            return True
        except Exception as e:
            logger.error(f"保存数据到数据库失败: {e}")
            return False
    
    async def load(self, key: str) -> Optional[Any]:
        """从数据库加载数据"""
        try:
            # 这里应该实现具体的数据库操作
            # 目前只是模拟
            logger.info(f"从数据库加载数据: {key}")
            return None
        except Exception as e:
            logger.error(f"从数据库加载数据失败: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """从数据库删除数据"""
        try:
            # 这里应该实现具体的数据库操作
            # 目前只是模拟
            logger.info(f"从数据库删除数据: {key}")
            return True
        except Exception as e:
            logger.error(f"从数据库删除数据失败: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查数据库中的数据是否存在"""
        try:
            # 这里应该实现具体的数据库操作
            # 目前只是模拟
            return False
        except Exception as e:
            logger.error(f"检查数据库数据存在性失败: {e}")
            return False
    
    async def list_keys(self, pattern: str = "*") -> List[str]:
        """列出数据库中的键"""
        try:
            # 这里应该实现具体的数据库操作
            # 目前只是模拟
            return []
        except Exception as e:
            logger.error(f"列出数据库键失败: {e}")
            return []


class FileStorage(StorageInterface):
    """文件存储实现"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.data: Dict[str, Any] = {}
        
        # 加载现有数据
        self._load_data()
        
        logger.info(f"文件存储初始化: {file_path}")
    
    def _load_data(self):
        """加载现有数据"""
        try:
            import os
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                logger.info(f"从文件加载了 {len(self.data)} 条数据")
        except Exception as e:
            logger.error(f"加载文件数据失败: {e}")
            self.data = {}
    
    def _save_data(self):
        """保存数据到文件"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"保存文件数据失败: {e}")
    
    async def save(self, key: str, data: Any) -> bool:
        """保存数据到文件"""
        try:
            self.data[key] = data
            self._save_data()
            logger.info(f"保存数据到文件: {key}")
            return True
        except Exception as e:
            logger.error(f"保存数据到文件失败: {e}")
            return False
    
    async def load(self, key: str) -> Optional[Any]:
        """从文件加载数据"""
        try:
            data = self.data.get(key)
            logger.info(f"从文件加载数据: {key}")
            return data
        except Exception as e:
            logger.error(f"从文件加载数据失败: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """从文件删除数据"""
        try:
            if key in self.data:
                del self.data[key]
                self._save_data()
                logger.info(f"从文件删除数据: {key}")
                return True
            return False
        except Exception as e:
            logger.error(f"从文件删除数据失败: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查文件中的数据是否存在"""
        try:
            return key in self.data
        except Exception as e:
            logger.error(f"检查文件数据存在性失败: {e}")
            return False
    
    async def list_keys(self, pattern: str = "*") -> List[str]:
        """列出文件中的键"""
        try:
            if pattern == "*":
                return list(self.data.keys())
            else:
                # 简单的模式匹配
                import fnmatch
                return [key for key in self.data.keys() if fnmatch.fnmatch(key, pattern)]
        except Exception as e:
            logger.error(f"列出文件键失败: {e}")
            return []


class CacheStorage(StorageInterface):
    """缓存存储实现"""
    
    def __init__(self, cache_config: Dict[str, Any]):
        self.cache_config = cache_config
        self.cache: Dict[str, Any] = {}
        self.expiry_times: Dict[str, datetime] = {}
        self.max_size = cache_config.get("max_size", 1000)
        self.default_ttl = cache_config.get("default_ttl", 3600)  # 秒
        
        # 启动清理任务
        self.cleanup_task = None
        self._start_cleanup_task()
        
        logger.info("缓存存储初始化完成")
    
    def _start_cleanup_task(self):
        """启动清理任务"""
        async def cleanup_loop():
            while True:
                try:
                    await self._cleanup_expired_items()
                    await asyncio.sleep(60)  # 每分钟清理一次
                except Exception as e:
                    logger.error(f"缓存清理任务出错: {e}")
                    await asyncio.sleep(60)
        
        self.cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info("缓存清理任务已启动")
    
    async def _cleanup_expired_items(self):
        """清理过期项目"""
        try:
            current_time = datetime.now()
            expired_keys = []
            
            for key, expiry_time in self.expiry_times.items():
                if current_time > expiry_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                await self.delete(key)
            
            if expired_keys:
                logger.info(f"清理了 {len(expired_keys)} 个过期缓存项")
                
        except Exception as e:
            logger.error(f"清理过期缓存项失败: {e}")
    
    async def save(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """保存数据到缓存"""
        try:
            # 检查缓存大小限制
            if len(self.cache) >= self.max_size:
                await self._evict_oldest()
            
            self.cache[key] = data
            ttl_seconds = ttl or self.default_ttl
            self.expiry_times[key] = datetime.now() + timedelta(seconds=ttl_seconds)
            
            logger.info(f"保存数据到缓存: {key}, TTL: {ttl_seconds}秒")
            return True
            
        except Exception as e:
            logger.error(f"保存数据到缓存失败: {e}")
            return False
    
    async def load(self, key: str) -> Optional[Any]:
        """从缓存加载数据"""
        try:
            if key not in self.cache:
                return None
            
            # 检查是否过期
            if key in self.expiry_times:
                if datetime.now() > self.expiry_times[key]:
                    await self.delete(key)
                    return None
            
            data = self.cache[key]
            logger.info(f"从缓存加载数据: {key}")
            return data
            
        except Exception as e:
            logger.error(f"从缓存加载数据失败: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """从缓存删除数据"""
        try:
            if key in self.cache:
                del self.cache[key]
            
            if key in self.expiry_times:
                del self.expiry_times[key]
            
            logger.info(f"从缓存删除数据: {key}")
            return True
            
        except Exception as e:
            logger.error(f"从缓存删除数据失败: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查缓存中的数据是否存在"""
        try:
            if key not in self.cache:
                return False
            
            # 检查是否过期
            if key in self.expiry_times:
                if datetime.now() > self.expiry_times[key]:
                    await self.delete(key)
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查缓存数据存在性失败: {e}")
            return False
    
    async def list_keys(self, pattern: str = "*") -> List[str]:
        """列出缓存中的键"""
        try:
            if pattern == "*":
                return list(self.cache.keys())
            else:
                # 简单的模式匹配
                import fnmatch
                return [key for key in self.cache.keys() if fnmatch.fnmatch(key, pattern)]
        except Exception as e:
            logger.error(f"列出缓存键失败: {e}")
            return []
    
    async def _evict_oldest(self):
        """驱逐最旧的项目"""
        try:
            if not self.expiry_times:
                return
            
            # 找到最旧的项目
            oldest_key = min(self.expiry_times.keys(), key=lambda k: self.expiry_times[k])
            await self.delete(oldest_key)
            
        except Exception as e:
            logger.error(f"驱逐最旧缓存项失败: {e}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "total_items": len(self.cache),
            "max_size": self.max_size,
            "usage_percent": (len(self.cache) / self.max_size) * 100,
            "expired_items": len([k for k, v in self.expiry_times.items() if datetime.now() > v]),
            "default_ttl": self.default_ttl
        }
    
    async def shutdown(self):
        """关闭缓存存储"""
        try:
            if self.cleanup_task:
                self.cleanup_task.cancel()
                try:
                    await self.cleanup_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("缓存存储已关闭")
            
        except Exception as e:
            logger.error(f"关闭缓存存储失败: {e}")
            raise


class PersistenceManager:
    """
    持久化管理器
    
    管理系统数据持久化，支持多种存储后端
    """
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self.storages: Dict[str, StorageInterface] = {}
        self.backup_task: Optional[asyncio.Task] = None
        
        # 初始化存储后端
        self._initialize_storages()
        
        # 启动备份任务
        if config.backup_enabled:
            self._start_backup_task()
        
        logger.info("持久化管理器初始化完成")
    
    def _initialize_storages(self):
        """初始化存储后端"""
        try:
            if self.config.storage_type in ["database", "hybrid"] and self.config.database_url:
                self.storages["database"] = DatabaseStorage(self.config.database_url)
            
            if self.config.storage_type in ["file", "hybrid"] and self.config.file_path:
                self.storages["file"] = FileStorage(self.config.file_path)
            
            if self.config.storage_type in ["cache", "hybrid"] and self.config.cache_config:
                self.storages["cache"] = CacheStorage(self.config.cache_config)
            
            logger.info(f"存储后端初始化完成: {list(self.storages.keys())}")
            
        except Exception as e:
            logger.error(f"初始化存储后端失败: {e}")
            raise
    
    def _start_backup_task(self):
        """启动备份任务"""
        async def backup_loop():
            while True:
                try:
                    await self._perform_backup()
                    await asyncio.sleep(self.config.backup_interval)
                except Exception as e:
                    logger.error(f"备份任务出错: {e}")
                    await asyncio.sleep(self.config.backup_interval)
        
        self.backup_task = asyncio.create_task(backup_loop())
        logger.info("备份任务已启动")
    
    async def _perform_backup(self):
        """执行备份"""
        try:
            logger.info("开始执行数据备份")
            
            for storage_name, storage in self.storages.items():
                if hasattr(storage, '_save_data'):
                    # 文件存储的备份
                    await storage._save_data()
                elif hasattr(storage, 'get_cache_stats'):
                    # 缓存存储的备份
                    stats = await storage.get_cache_stats()
                    logger.info(f"缓存存储统计: {stats}")
            
            logger.info("数据备份完成")
            
        except Exception as e:
            logger.error(f"执行数据备份失败: {e}")
    
    async def save(
        self,
        key: str,
        data: Any,
        storage_type: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        保存数据
        
        Args:
            key: 数据键
            data: 数据内容
            storage_type: 存储类型，如果为None则使用默认策略
            **kwargs: 其他参数（如TTL等）
            
        Returns:
            是否保存成功
        """
        try:
            if storage_type:
                # 指定存储类型
                if storage_type not in self.storages:
                    raise ValueError(f"不支持的存储类型: {storage_type}")
                
                storage = self.storages[storage_type]
                if storage_type == "cache":
                    ttl = kwargs.get("ttl")
                    return await storage.save(key, data, ttl)
                else:
                    return await storage.save(key, data)
            
            else:
                # 使用默认策略
                if "cache" in self.storages:
                    # 优先使用缓存
                    ttl = kwargs.get("ttl", 3600)
                    return await self.storages["cache"].save(key, data, ttl)
                elif "file" in self.storages:
                    # 其次使用文件
                    return await self.storages["file"].save(key, data)
                elif "database" in self.storages:
                    # 最后使用数据库
                    return await self.storages["database"].save(key, data)
                else:
                    raise RuntimeError("没有可用的存储后端")
            
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
            return False
    
    async def load(
        self,
        key: str,
        storage_type: Optional[str] = None
    ) -> Optional[Any]:
        """
        加载数据
        
        Args:
            key: 数据键
            storage_type: 存储类型，如果为None则使用默认策略
            
        Returns:
            数据内容
        """
        try:
            if storage_type:
                # 指定存储类型
                if storage_type not in self.storages:
                    raise ValueError(f"不支持的存储类型: {storage_type}")
                
                return await self.storages[storage_type].load(key)
            
            else:
                # 使用默认策略：缓存 -> 文件 -> 数据库
                for storage_name in ["cache", "file", "database"]:
                    if storage_name in self.storages:
                        data = await self.storages[storage_name].load(key)
                        if data is not None:
                            # 如果从非缓存加载到数据，可以缓存到缓存中
                            if storage_name != "cache" and "cache" in self.storages:
                                asyncio.create_task(
                                    self.storages["cache"].save(key, data, ttl=3600)
                                )
                            return data
                
                return None
            
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            return None
    
    async def delete(
        self,
        key: str,
        storage_type: Optional[str] = None
    ) -> bool:
        """
        删除数据
        
        Args:
            key: 数据键
            storage_type: 存储类型，如果为None则从所有存储中删除
            
        Returns:
            是否删除成功
        """
        try:
            if storage_type:
                # 指定存储类型
                if storage_type not in self.storages:
                    raise ValueError(f"不支持的存储类型: {storage_type}")
                
                return await self.storages[storage_type].delete(key)
            
            else:
                # 从所有存储中删除
                success = True
                for storage in self.storages.values():
                    if not await storage.delete(key):
                        success = False
                
                return success
            
        except Exception as e:
            logger.error(f"删除数据失败: {e}")
            return False
    
    async def exists(
        self,
        key: str,
        storage_type: Optional[str] = None
    ) -> bool:
        """
        检查数据是否存在
        
        Args:
            key: 数据键
            storage_type: 存储类型，如果为None则检查所有存储
            
        Returns:
            数据是否存在
        """
        try:
            if storage_type:
                # 指定存储类型
                if storage_type not in self.storages:
                    raise ValueError(f"不支持的存储类型: {storage_type}")
                
                return await self.storages[storage_type].exists(key)
            
            else:
                # 检查所有存储
                for storage in self.storages.values():
                    if await storage.exists(key):
                        return True
                
                return False
            
        except Exception as e:
            logger.error(f"检查数据存在性失败: {e}")
            return False
    
    async def list_keys(
        self,
        pattern: str = "*",
        storage_type: Optional[str] = None
    ) -> List[str]:
        """
        列出匹配的键
        
        Args:
            pattern: 匹配模式
            storage_type: 存储类型，如果为None则从所有存储中列出
            
        Returns:
            匹配的键列表
        """
        try:
            if storage_type:
                # 指定存储类型
                if storage_type not in self.storages:
                    raise ValueError(f"不支持的存储类型: {storage_type}")
                
                return await self.storages[storage_type].list_keys(pattern)
            
            else:
                # 从所有存储中列出
                all_keys = set()
                for storage in self.storages.values():
                    keys = await storage.list_keys(pattern)
                    all_keys.update(keys)
                
                return list(all_keys)
            
        except Exception as e:
            logger.error(f"列出键失败: {e}")
            return []
    
    async def get_storage_info(self) -> Dict[str, Any]:
        """获取存储信息"""
        info = {
            "storage_type": self.config.storage_type,
            "storages_available": list(self.storages.keys()),
            "backup_enabled": self.config.backup_enabled,
            "backup_interval": self.config.backup_interval
        }
        
        # 获取各存储的统计信息
        for storage_name, storage in self.storages.items():
            try:
                if hasattr(storage, 'get_cache_stats'):
                    info[f"{storage_name}_stats"] = await storage.get_cache_stats()
                elif hasattr(storage, 'data'):
                    info[f"{storage_name}_stats"] = {"total_items": len(storage.data)}
            except Exception as e:
                logger.error(f"获取存储 {storage_name} 统计信息失败: {e}")
        
        return info
    
    async def shutdown(self):
        """关闭持久化管理器"""
        try:
            # 停止备份任务
            if self.backup_task:
                self.backup_task.cancel()
                try:
                    await self.backup_task
                except asyncio.CancelledError:
                    pass
            
            # 关闭各存储
            for storage_name, storage in self.storages.items():
                if hasattr(storage, 'shutdown'):
                    await storage.shutdown()
            
            logger.info("持久化管理器已关闭")
            
        except Exception as e:
            logger.error(f"关闭持久化管理器失败: {e}")
            raise
