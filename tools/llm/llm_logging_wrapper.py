"""
LLM Logging Wrapper

LLM日志包装器 - 为所有LLM调用添加完整的日志记录功能
"""

import asyncio
import inspect
import traceback
import uuid
from datetime import datetime
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Union
from dataclasses import dataclass, asdict

import structlog
from langchain.llms.base import BaseLLM
from langchain.schema import BaseMessage, LLMResult
from langchain.callbacks.manager import CallbackManagerForLLMRun, AsyncCallbackManagerForLLMRun
from langchain.schema.output import Generation
from .llm_logging_utils import get_logging_manager

logger = structlog.get_logger(__name__)


@dataclass
class CallContext:
    """调用上下文信息"""
    file: str
    line: int
    function: str
    call_stack: List[str]
    timestamp: str


@dataclass
class LLMRequestLog:
    """LLM请求日志"""
    request_id: str
    call_context: CallContext
    model_info: Dict[str, Any]
    prompt: str
    parameters: Dict[str, Any]
    stream: bool
    timestamp: str


@dataclass
class LLMResponseLog:
    """LLM响应日志"""
    response_id: str
    request_id: str
    content: str
    stream_chunks: List[str]
    token_usage: Dict[str, Any]
    performance: Dict[str, Any]
    finish_reason: str
    error: Optional[str]
    timestamp: str


class LLMLoggingWrapper(BaseLLM):
    """LLM日志包装器 - 为所有LLM调用添加完整的日志记录功能"""
    
    def __init__(self, llm: BaseLLM, model_info: Dict[str, Any], **kwargs):
        """
        初始化日志包装器
        
        Args:
            llm: 原始的LLM实例
            model_info: 模型信息（名称、提供商、参数等）
        """
        super().__init__(**kwargs)
        self._llm = llm
        self._model_info = model_info
        self._logging_manager = get_logging_manager()
        
        logger.info("LLM日志包装器初始化完成", model_info=model_info)
    
    @property
    def llm(self) -> BaseLLM:
        """获取原始LLM实例"""
        return self._llm
    
    @property
    def model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return self._model_info
    
    @property
    def logging_manager(self):
        """获取日志管理器"""
        return self._logging_manager
    
    def _capture_call_context(self) -> CallContext:
        """自动捕获调用上下文"""
        try:
            frame = inspect.currentframe()
            # 向上查找调用者帧
            caller_frame = None
            for _ in range(10):  # 最多向上查找10层
                if frame:
                    frame = frame.f_back
                    if frame and frame.f_code.co_name not in ['ainvoke', 'stream', '_capture_call_context']:
                        caller_frame = frame
                        break
            
            if caller_frame:
                return CallContext(
                    file=caller_frame.f_code.co_filename,
                    line=caller_frame.f_lineno,
                    function=caller_frame.f_code.co_name,
                    call_stack=traceback.format_stack()[-5:],  # 最近5层调用栈
                    timestamp=datetime.now().isoformat()
                )
        except Exception as e:
            logger.warning(f"捕获调用上下文失败: {e}")
        
        # 返回默认上下文
        return CallContext(
            file="unknown",
            line=0,
            function="unknown",
            call_stack=[],
            timestamp=datetime.now().isoformat()
        )
    
    def _filter_duplicate_params(self, explicit_params: dict, kwargs: dict) -> dict:
        """
        智能过滤重复参数，避免参数重复传递
        
        Args:
            explicit_params: 显式传递的参数
            kwargs: 关键字参数
            
        Returns:
            dict: 过滤后的kwargs
        """
        try:
            filtered_kwargs = kwargs.copy()
            
            for key, value in explicit_params.items():
                if key in filtered_kwargs:
                    # 记录参数冲突，便于调试
                    logger.debug(f"参数冲突: {key} = {value} (显式) vs {filtered_kwargs[key]} (kwargs)")
                    # 移除kwargs中的重复参数，显式参数优先级更高
                    del filtered_kwargs[key]
            
            return filtered_kwargs
            
        except Exception as e:
            logger.warning(f"参数过滤失败: {e}，使用原始kwargs")
            return kwargs
    
    def _extract_content(self, result) -> str:
        """
        通用内容提取方法，兼容不同版本的LangChain返回结果
        
        Args:
            result: LLM调用返回的结果
            
        Returns:
            str: 提取的文本内容
        """
        try:
            # 处理AIMessage对象（新版本LangChain）
            if hasattr(result, 'content'):
                return str(result.content)
            
            # 处理LLMResult对象（旧版本LangChain）
            if hasattr(result, 'generations') and result.generations:
                if isinstance(result.generations[0], list) and result.generations[0]:
                    return str(result.generations[0][0].text)
                elif result.generations[0]:
                    return str(result.generations[0].text)
            
            # 处理其他可能的返回类型
            if hasattr(result, 'text'):
                return str(result.text)
            
            # 如果都无法提取，返回字符串表示
            return str(result)
            
        except Exception as e:
            logger.warning(f"内容提取失败: {e}，使用字符串表示")
            return str(result)
    
    def _extract_token_usage(self, result) -> dict:
        """
        通用token使用量提取方法
        
        Args:
            result: LLM调用返回的结果
            
        Returns:
            dict: token使用量信息
        """
        try:
            # 尝试从不同属性中提取token使用量
            if hasattr(result, 'llm_output') and result.llm_output:
                return result.llm_output.get('token_usage', {})
            elif hasattr(result, 'usage'):
                return result.usage
            elif hasattr(result, 'token_usage'):
                return result.token_usage
            else:
                return {}
        except Exception as e:
            logger.debug(f"Token使用量提取失败: {e}")
            return {}
    
    def _create_request_log(self, prompt: str, parameters: Dict[str, Any], stream: bool = False) -> LLMRequestLog:
        """创建请求日志"""
        return LLMRequestLog(
            request_id=str(uuid.uuid4()),
            call_context=self._capture_call_context(),
            model_info=self.model_info,
            prompt=prompt,
            parameters=parameters,
            stream=stream,
            timestamp=datetime.now().isoformat()
        )
    
    def _create_response_log(self, request_log: LLMRequestLog, content: str, 
                           stream_chunks: List[str], token_usage: Dict[str, Any],
                           performance: Dict[str, Any], finish_reason: str,
                           error: Optional[str] = None) -> LLMResponseLog:
        """创建响应日志"""
        return LLMResponseLog(
            response_id=str(uuid.uuid4()),
            request_id=request_log.request_id,
            content=content,
            stream_chunks=stream_chunks,
            token_usage=token_usage,
            performance=performance,
            finish_reason=finish_reason,
            error=error,
            timestamp=datetime.now().isoformat()
        )
    
    def _log_request(self, request_log: LLMRequestLog):
        """记录请求日志"""
        self.logging_manager.log_request(asdict(request_log))
    
    def _log_response(self, response_log: LLMResponseLog):
        """记录响应日志"""
        self.logging_manager.log_response(asdict(response_log))
        
        # 记录性能统计
        scene_key = self.model_info.get("scene_key", "unknown")
        model_name = self.model_info.get("model_name", "unknown")
        performance = response_log.performance
        duration = performance.get("duration", 0)
        token_count = len(response_log.content.split())  # 简单估算token数量
        success = response_log.error is None
        
        self.logging_manager.record_performance(
            scene_key, model_name, duration, token_count, success, response_log.error
        )
    
    def invoke(self, prompt: str, stop: Optional[List[str]] = None, 
               run_manager: Optional[CallbackManagerForLLMRun] = None, **kwargs) -> LLMResult:
        """同步调用LLM"""
        start_time = datetime.now()
        request_log = self._create_request_log(prompt, kwargs, stream=False)
        
        try:
            # 记录请求日志
            self._log_request(request_log)
            
            # 调用原始LLM
            result = self.llm.invoke(prompt, stop=stop, run_manager=run_manager, **kwargs)
            
            # 计算性能指标
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 提取响应内容
            content = result.generations[0][0].text if result.generations else ""
            
            # 创建响应日志
            response_log = self._create_response_log(
                request_log=request_log,
                content=content,
                stream_chunks=[content],
                token_usage=getattr(result, 'llm_output', {}).get('token_usage', {}),
                performance={
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration": duration,
                    "tokens_per_second": len(content.split()) / duration if duration > 0 else 0
                },
                finish_reason="stop"
            )
            
            # 记录响应日志
            self._log_response(response_log)
            
            return result
            
        except Exception as e:
            # 记录错误日志
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            error_log = self._create_response_log(
                request_log=request_log,
                content="",
                stream_chunks=[],
                token_usage={},
                performance={
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration": duration,
                    "tokens_per_second": 0
                },
                finish_reason="error",
                error=str(e)
            )
            
            self._log_response(error_log)
            raise
    
    async def ainvoke(self, prompt: str, stop: Optional[List[str]] = None,
                      run_manager: Optional[AsyncCallbackManagerForLLMRun] = None, **kwargs) -> LLMResult:
        """
        异步调用LLM
        
        Args:
            prompt: 输入提示词
            stop: 停止词列表
            run_manager: 异步回调管理器
            **kwargs: 其他LLM参数
            
        Returns:
            LLMResult: LLM响应结果
            
        Note:
            自动过滤重复参数，避免参数冲突
        """
        start_time = datetime.now()
        request_log = self._create_request_log(prompt, kwargs, stream=False)
        
        try:
            # 记录请求日志
            self._log_request(request_log)
            
            # 过滤重复参数，避免参数重复传递
            explicit_params = {"stop": stop, "run_manager": run_manager}
            filtered_kwargs = self._filter_duplicate_params(explicit_params, kwargs)
            
            # 调用原始LLM，只传递过滤后的kwargs，避免重复参数
            result = await self.llm.ainvoke(prompt, **filtered_kwargs)
            
            # 计算性能指标
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 提取响应内容
            content = self._extract_content(result)
            
            # 创建响应日志
            response_log = self._create_response_log(
                request_log=request_log,
                content=content,
                stream_chunks=[content],
                token_usage=self._extract_token_usage(result),
                performance={
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration": duration,
                    "tokens_per_second": len(content.split()) / duration if duration > 0 else 0
                },
                finish_reason="stop"
            )
            
            # 记录响应日志
            self._log_response(response_log)
            
            return result
            
        except Exception as e:
            # 记录错误日志
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            error_log = self._create_response_log(
                request_log=request_log,
                content="",
                stream_chunks=[],
                token_usage={},
                performance={
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration": duration,
                    "tokens_per_second": 0
                },
                finish_reason="error",
                error=str(e)
            )
            
            self._log_response(error_log)
            raise
    
    def stream(self, prompt: str, stop: Optional[List[str]] = None,
               run_manager: Optional[CallbackManagerForLLMRun] = None, **kwargs) -> Iterator[Generation]:
        """
        同步流式调用LLM
        
        Args:
            prompt: 输入提示词
            stop: 停止词列表
            run_manager: 同步回调管理器
            **kwargs: 其他LLM参数
            
        Returns:
            Iterator[Generation]: 流式生成结果
            
        Note:
            自动过滤重复参数，避免参数冲突
        """
        start_time = datetime.now()
        request_log = self._create_request_log(prompt, kwargs, stream=True)
        stream_chunks = []
        full_content = ""
        
        try:
            # 记录请求日志
            self._log_request(request_log)
            
            # 过滤重复参数，避免参数重复传递
            explicit_params = {"stop": stop, "run_manager": run_manager}
            filtered_kwargs = self._filter_duplicate_params(explicit_params, kwargs)
            
            # 调用原始LLM流式接口，只传递过滤后的kwargs，避免重复参数
            for chunk in self.llm.stream(prompt, **filtered_kwargs):
                content = chunk.text if hasattr(chunk, 'text') else str(chunk)
                stream_chunks.append(content)
                full_content += content
                yield chunk
            
            # 计算性能指标
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 创建响应日志
            response_log = self._create_response_log(
                request_log=request_log,
                content=full_content,
                stream_chunks=stream_chunks,
                token_usage={},  # 流式响应通常没有token统计
                performance={
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration": duration,
                    "tokens_per_second": len(full_content.split()) / duration if duration > 0 else 0
                },
                finish_reason="stop"
            )
            
            # 记录响应日志
            self._log_response(response_log)
            
        except Exception as e:
            # 记录错误日志
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            error_log = self._create_response_log(
                request_log=request_log,
                content=full_content,
                stream_chunks=stream_chunks,
                token_usage={},
                performance={
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration": duration,
                    "tokens_per_second": 0
                },
                finish_reason="error",
                error=str(e)
            )
            
            self._log_response(error_log)
            raise
    
    async def astream(self, prompt: str, stop: Optional[List[str]] = None,
                      run_manager: Optional[AsyncCallbackManagerForLLMRun] = None, **kwargs) -> AsyncIterator[Generation]:
        """异步流式调用LLM"""
        start_time = datetime.now()
        request_log = self._create_request_log(prompt, kwargs, stream=True)
        stream_chunks = []
        full_content = ""
        
        try:
            # 记录请求日志
            self._log_request(request_log)
            
            # 调用原始LLM异步流式接口
            async for chunk in self.llm.astream(prompt, stop=stop, run_manager=run_manager, **kwargs):
                content = chunk.text if hasattr(chunk, 'text') else str(chunk)
                stream_chunks.append(content)
                full_content += content
                yield chunk
            
            # 计算性能指标
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 创建响应日志
            response_log = self._create_response_log(
                request_log=request_log,
                content=full_content,
                stream_chunks=stream_chunks,
                token_usage={},  # 流式响应通常没有token统计
                performance={
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration": duration,
                    "tokens_per_second": len(full_content.split()) / duration if duration > 0 else 0
                },
                finish_reason="stop"
            )
            
            # 记录响应日志
            self._log_response(response_log)
            
        except Exception as e:
            # 记录错误日志
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            error_log = self._create_response_log(
                request_log=request_log,
                content=full_content,
                stream_chunks=stream_chunks,
                token_usage={},
                performance={
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration": duration,
                    "tokens_per_second": 0
                },
                finish_reason="error",
                error=str(e)
            )
            
            self._log_response(error_log)
            raise
    
    @property
    def _llm_type(self) -> str:
        """LLM类型（内部属性）"""
        return f"logging_wrapper_{self.llm._llm_type if hasattr(self.llm, '_llm_type') else self.llm.llm_type}"
    
    @property
    def llm_type(self) -> str:
        """LLM类型（公共属性）"""
        return self._llm_type
    
    def _generate(self, prompts: List[str], stop: Optional[List[str]] = None,
                  run_manager: Optional[CallbackManagerForLLMRun] = None, **kwargs) -> LLMResult:
        """生成方法（LangChain要求）"""
        # 这里我们使用invoke方法，因为我们已经实现了它
        results = []
        for prompt in prompts:
            result = self.invoke(prompt, stop=stop, run_manager=run_manager, **kwargs)
            results.append(result)
        
        # 合并结果
        if results:
            return results[0]  # 简化处理，返回第一个结果
        else:
            return LLMResult(generations=[])
    
    def get_num_tokens(self, text: str) -> int:
        """获取token数量"""
        return self.llm.get_num_tokens(text)
    
    def get_token_ids(self, text: str) -> List[int]:
        """获取token ID列表"""
        return self.llm.get_token_ids(text)
    
    def close(self):
        """关闭包装器"""
        # 关闭原始LLM
        if hasattr(self.llm, 'close'):
            self.llm.close()
    
    async def aclose(self):
        """异步关闭包装器"""
        # 关闭原始LLM
        if hasattr(self.llm, 'aclose'):
            await self.llm.aclose()
