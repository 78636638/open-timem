"""
TiMem MiniMax LLM Adapter
Implements interface for MiniMax API (OpenAI-compatible)
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, AsyncIterator
import json
import aiohttp

from llm.base_llm import (
    BaseLLM, Message, MessageRole, ChatResponse, EmbeddingResponse, ModelConfig,
    ModelType, handle_llm_errors
)
from llm.file_prompt_collector import get_file_prompt_collector
from timem.utils.logging import get_logger

logger = get_logger(__name__)


class MiniMaxAdapter(BaseLLM):
    """MiniMax API Adapter (OpenAI-compatible interface)"""

    def __init__(self, config: Optional[ModelConfig] = None):
        from timem.utils.config_manager import get_llm_config

        llm_config = get_llm_config()
        minimax_config = llm_config.get("providers", {}).get("minimax", {})

        if config is None:
            config = ModelConfig(
                model_name=minimax_config.get("model", "MiniMax-M2.7"),
                temperature=minimax_config.get("temperature", 0.7),
                max_tokens=minimax_config.get("max_tokens", 2048),
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                stop=None,
                stream=False
            )

        super().__init__(config)
        self.api_key = minimax_config.get("api_key", "")
        self.base_url = minimax_config.get("base_url", "https://api.minimaxi.com/v1")
        self.timeout = minimax_config.get("timeout", 90)
        self.model_type = ModelType.CHAT
        self.logger = logger

        self._http_session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()

        if not self.api_key:
            self.logger.warning("MiniMax API key not configured. Please set MINIMAX_API_KEY environment variable or configure in config file")

        self.logger.info(f"Initializing MiniMax adapter: base_url={self.base_url}, model={config.model_name}")

        self.supported_models = [
            "MiniMax-M2.7",
            "MiniMax-M2.7-highspeed",
            "MiniMax-M2.5",
            "MiniMax-M2.5-highspeed",
            "MiniMax-M2.1",
            "MiniMax-M2.1-highspeed",
            "MiniMax-M2",
        ]

        self.chat_models = {
            "MiniMax-M2.7": {"max_tokens": 2048, "context_window": 204800},
            "MiniMax-M2.7-highspeed": {"max_tokens": 2048, "context_window": 204800},
            "MiniMax-M2.5": {"max_tokens": 2048, "context_window": 204800},
            "MiniMax-M2.5-highspeed": {"max_tokens": 2048, "context_window": 204800},
            "MiniMax-M2.1": {"max_tokens": 2048, "context_window": 204800},
            "MiniMax-M2.1-highspeed": {"max_tokens": 2048, "context_window": 204800},
            "MiniMax-M2": {"max_tokens": 2048, "context_window": 204800},
        }

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "TiMem/1.0"
        }

    def _message_to_dict(self, message: Message) -> Dict[str, str]:
        """Convert message to MiniMax format"""
        return {
            "role": message.role.value,
            "content": message.content
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self._http_session is None or self._http_session.closed:
            async with self._session_lock:
                if self._http_session is None or self._http_session.closed:
                    self._http_session = aiohttp.ClientSession(
                        headers=self._get_headers(),
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    )
        return self._http_session

    async def _ensure_session(self):
        """Ensure session is available"""
        await self._get_session()

    async def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        """Chat conversation"""
        await self._ensure_session()

        start_time = time.time()

        model = kwargs.get("model", self.config.model_name)
        temperature = kwargs.get("temperature", self.config.temperature)
        max_tokens = kwargs.get("max_tokens", self.config.max_tokens)

        if model not in self.supported_models:
            self.logger.warning(f"Model {model} not in supported list, proceeding anyway: {self.supported_models}")

        request_data = {
            "model": model,
            "messages": [self._message_to_dict(msg) for msg in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": kwargs.get("top_p", self.config.top_p),
        }

        if self.config.stop:
            request_data["stop"] = self.config.stop

        prompt_collector = get_file_prompt_collector()
        prompt_record_id = None
        if prompt_collector.enabled:
            messages_dict = [self._message_to_dict(msg) for msg in messages]
            prompt_record_id = prompt_collector.record_chat_prompt(
                messages=messages_dict,
                model=model,
                metadata=kwargs.get("metadata", {})
            )

        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/chat/completions",
                json=request_data
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"MiniMax API error ({response.status}): {error_text}")

                result = await response.json()

            response_time = time.time() - start_time
            choice = result["choices"][0]
            usage_data = result.get("usage", {})

            prompt_tokens = usage_data.get("prompt_tokens", 0)
            completion_tokens = usage_data.get("completion_tokens", 0)
            total_tokens = usage_data.get("total_tokens", prompt_tokens + completion_tokens)

            content = choice["message"]["content"]

            chat_response = ChatResponse(
                content=content,
                finish_reason=choice.get("finish_reason", "stop"),
                model=result.get("model", model),
                usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                },
                response_time=response_time,
                metadata={
                    "provider": "minimax",
                    "prompt_record_id": prompt_record_id
                }
            )

            self.logger.debug(f"MiniMax chat success, elapsed: {response_time:.2f}s, tokens: {total_tokens}")
            return chat_response

        except Exception as e:
            self.logger.error(f"MiniMax chat failed: {e}", exc_info=True)
            raise

    @handle_llm_errors
    async def chat_stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """Streaming chat conversation"""
        await self._ensure_session()

        model = kwargs.get("model", self.config.model_name)
        temperature = kwargs.get("temperature", self.config.temperature)
        max_tokens = kwargs.get("max_tokens", self.config.max_tokens)

        request_data = {
            "model": model,
            "messages": [self._message_to_dict(msg) for msg in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": kwargs.get("top_p", self.config.top_p),
            "stream": True
        }

        if self.config.stop:
            request_data["stop"] = self.config.stop

        collected_content = []

        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/chat/completions",
                json=request_data
            ) as response:

                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"MiniMax API error ({response.status}): {error_text}")

                async for line_bytes in response.content:
                    line = line_bytes.decode('utf-8').strip()

                    if line.startswith("data: "):
                        data_str = line[6:]

                        if data_str.strip() == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    content_chunk = delta["content"]
                                    collected_content.append(content_chunk)
                                    yield content_chunk
                        except json.JSONDecodeError:
                            continue

            full_content = "".join(collected_content)
            self.logger.debug(f"MiniMax stream complete, content length: {len(full_content)}")

        except Exception as e:
            self.logger.error(f"MiniMax stream failed: {e}", exc_info=True)
            raise

    @handle_llm_errors
    async def complete(self, prompt: str, **kwargs) -> str:
        """Text completion (implemented via chat interface)"""
        messages = [self.create_message(MessageRole.USER, prompt)]
        response = await self.chat(messages, **kwargs)
        return response.content

    @handle_llm_errors
    async def embed(self, text: str, **kwargs) -> EmbeddingResponse:
        """Text embedding (MiniMax does not provide embedding API, use fallback)"""
        raise NotImplementedError("MiniMax does not provide embedding API. Please configure a different embedding provider (e.g., qwen_local or openai)")

    @handle_llm_errors
    async def embed_batch(self, texts: List[str], **kwargs) -> List[EmbeddingResponse]:
        """Batch text embedding"""
        raise NotImplementedError("MiniMax does not provide embedding API. Please configure a different embedding provider (e.g., qwen_local or openai)")

    @handle_llm_errors
    async def summarize(self, text: str, **kwargs) -> str:
        """Text summarization (implemented via chat interface)"""
        messages = [
            self.create_message(MessageRole.SYSTEM, "You are a helpful assistant that summarizes text concisely."),
            self.create_message(MessageRole.USER, f"Please summarize the following text:\n\n{text}")
        ]
        response = await self.chat(messages, **kwargs)
        return response.content

    async def validate_model(self, model_name: str) -> bool:
        """Validate if model is available"""
        return model_name in self.supported_models

    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get model information"""
        if model_name in self.chat_models:
            return {
                "name": model_name,
                "type": "chat",
                **self.chat_models[model_name]
            }
        return {
            "name": model_name,
            "type": "unknown",
            "max_tokens": 2048,
            "context_window": 204800
        }

    async def close(self):
        """Close HTTP session"""
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()
            self._http_session = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
