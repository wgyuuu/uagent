"""
Data Validation Tools

数据验证工具 - 提供数据格式和内容验证功能
"""

from typing import Dict, Any, List
from .base_tool import BaseTool, ToolSchema


class DataValidateTool(BaseTool):
    """数据验证工具"""
    
    def get_tool_id(self) -> str:
        return "data_validate"
    
    def get_name(self) -> str:
        return "数据验证"
    
    def get_description(self) -> str:
        return "验证数据格式和内容"
    
    def get_category(self) -> str:
        return "data_validation"
    
    def get_tags(self) -> list:
        return ["validation", "schema", "data"]
    
    def get_metadata(self) -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "author": "uagent",
            "supports_async": True,
            "supported_types": ["string", "integer", "float", "boolean", "object", "array"],
            "validation_levels": ["basic", "strict", "custom"]
        }
    
    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            input_schema={
                "type": "object",
                "properties": {
                    "data": {"description": "要验证的数据"},
                    "schema": {"type": "object", "description": "验证模式"},
                    "strict": {"type": "boolean", "default": False, "description": "是否严格验证"}
                },
                "required": ["data", "schema"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "is_valid": {"type": "boolean", "description": "是否有效"},
                    "errors": {"type": "array", "description": "错误列表"},
                    "warnings": {"type": "array", "description": "警告列表"}
                }
            }
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行数据验证"""
        self.validate_input(kwargs)
        
        data = kwargs["data"]
        schema = kwargs["schema"]
        strict = kwargs.get("strict", False)
        
        errors = []
        warnings = []
        
        try:
            # 基本类型验证
            if "type" in schema:
                type_errors = self._validate_type(data, schema["type"])
                errors.extend(type_errors)
            
            # 对象字段验证
            if isinstance(data, dict) and "properties" in schema:
                field_errors, field_warnings = self._validate_object_fields(data, schema, strict)
                errors.extend(field_errors)
                warnings.extend(field_warnings)
            
            # 必需字段验证
            if isinstance(data, dict) and "required" in schema:
                required_errors = self._validate_required_fields(data, schema["required"])
                errors.extend(required_errors)
            
            # 数组验证
            if isinstance(data, list) and "items" in schema:
                array_errors = self._validate_array_items(data, schema["items"])
                errors.extend(array_errors)
            
            # 值范围验证
            if "minimum" in schema and isinstance(data, (int, float)):
                if data < schema["minimum"]:
                    errors.append(f"值 {data} 小于最小值 {schema['minimum']}")
            
            if "maximum" in schema and isinstance(data, (int, float)):
                if data > schema["maximum"]:
                    errors.append(f"值 {data} 大于最大值 {schema['maximum']}")
            
            if "minLength" in schema and isinstance(data, str):
                if len(data) < schema["minLength"]:
                    errors.append(f"字符串长度 {len(data)} 小于最小长度 {schema['minLength']}")
            
            if "maxLength" in schema and isinstance(data, str):
                if len(data) > schema["maxLength"]:
                    errors.append(f"字符串长度 {len(data)} 大于最大长度 {schema['maxLength']}")
            
            is_valid = len(errors) == 0
            
            return {
                "is_valid": is_valid,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "is_valid": False,
                "errors": [f"验证过程出错: {str(e)}"],
                "warnings": []
            }
    
    def _validate_type(self, data: Any, expected_type: str) -> List[str]:
        """验证数据类型"""
        errors = []
        
        if expected_type == "string" and not isinstance(data, str):
            errors.append(f"期望字符串类型，实际类型: {type(data).__name__}")
        elif expected_type == "integer" and not isinstance(data, int):
            errors.append(f"期望整数类型，实际类型: {type(data).__name__}")
        elif expected_type == "number" and not isinstance(data, (int, float)):
            errors.append(f"期望数字类型，实际类型: {type(data).__name__}")
        elif expected_type == "boolean" and not isinstance(data, bool):
            errors.append(f"期望布尔类型，实际类型: {type(data).__name__}")
        elif expected_type == "object" and not isinstance(data, dict):
            errors.append(f"期望对象类型，实际类型: {type(data).__name__}")
        elif expected_type == "array" and not isinstance(data, list):
            errors.append(f"期望数组类型，实际类型: {type(data).__name__}")
        
        return errors
    
    def _validate_object_fields(self, data: Dict[str, Any], schema: Dict[str, Any], strict: bool) -> tuple:
        """验证对象字段"""
        errors = []
        warnings = []
        
        properties = schema.get("properties", {})
        
        for field_name, field_value in data.items():
            if field_name in properties:
                # 验证字段值
                field_schema = properties[field_name]
                field_errors = self._validate_type(field_value, field_schema.get("type", "any"))
                errors.extend([f"字段 '{field_name}': {error}" for error in field_errors])
            elif strict:
                warnings.append(f"未知字段: {field_name}")
        
        return errors, warnings
    
    def _validate_required_fields(self, data: Dict[str, Any], required_fields: List[str]) -> List[str]:
        """验证必需字段"""
        errors = []
        
        for field in required_fields:
            if field not in data:
                errors.append(f"缺少必需字段: {field}")
        
        return errors
    
    def _validate_array_items(self, data: List[Any], item_schema: Dict[str, Any]) -> List[str]:
        """验证数组项"""
        errors = []
        
        for i, item in enumerate(data):
            if "type" in item_schema:
                item_errors = self._validate_type(item, item_schema["type"])
                errors.extend([f"数组项[{i}]: {error}" for error in item_errors])
        
        return errors
