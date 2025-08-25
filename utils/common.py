import uuid
from datetime import datetime

def generate_id(prefix: str = "") -> str:
    """生成唯一ID"""
    if prefix:
        return f"{prefix}_{uuid.uuid4().hex[:8]}"
    return uuid.uuid4().hex[:8]

def current_timestamp() -> datetime:
    """获取当前时间戳"""
    return datetime.now()

def get_attr(obj, attr_name, default=None):
    """获取对象属性，如果属性不存在则返回默认值"""
    if hasattr(obj, attr_name):
        return getattr(obj, attr_name)
    return default