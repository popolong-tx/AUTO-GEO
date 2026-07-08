"""OCI GenAI client wrapper using OpenAI SDK compatible interface."""

import os
import json
import base64
import asyncio
import logging
from typing import AsyncGenerator, Optional

try:
    from openai import AsyncOpenAI, RateLimitError
except ImportError:  # pragma: no cover - fallback for test/runtime environments without openai installed
    AsyncOpenAI = None
    RateLimitError = Exception

logger = logging.getLogger(__name__)

SUPPORTED_MODELS = {
    "xai.grok-4.20-multi-agent-0309": {
        "name": "Grok 4.20 Multi-Agent",
        "description": "多智能体模型，适合复杂分析任务",
        "default": True,
    },
    "xai.grok-4.3": {
        "name": "Grok 4.3",
        "description": "通用模型，适合快速分析",
        "default": False,
    },
}

DEFAULT_MODEL = "xai.grok-4.20-multi-agent-0309"


class GenAIClient:

    def _estimate_image_tokens(self, image_inputs: list[dict]) -> int:
        total = 0
        for img in image_inputs or []:
            w = int(img.get("width") or 512)
            h = int(img.get("height") or 512)
            # very rough heuristic for vision token budgets
            total += max(256, min(1792, int((w * h) / (512 * 512) * 1610)))
        return total

    def _compress_image_base64(self, b64: str, max_chars: int = 220000) -> str:
        if len(b64) <= max_chars:
            return b64
        return b64[:max_chars]

    def _normalize_image_inputs(self, image_inputs: Optional[list[dict]] = None, token_budget: int = 200000) -> list[dict]:
        normalized = []
        used = 0
        for img in image_inputs or []:
            b64 = img.get("base64") or ""
            if not b64:
                continue
            b64 = self._compress_image_base64(b64)
            est = max(256, min(1792, int((img.get("width") or 512) * (img.get("height") or 512) / (512 * 512) * 1610)))
            if used + est > token_budget:
                break
            used += est
            normalized.append({
                **img,
                "base64": b64,
                "estimated_tokens": est,
            })
        return normalized

    """OCI GenAI client for Grok model inference."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        self.api_key = (
            api_key
            or os.getenv("OPENAI_API_KEY", "")
            or os.getenv("OCI_GENAI_API_KEY", "")
        )
        self.base_url = (
            base_url
            or os.getenv("OPENAI_BASE_URL", "")
            or os.getenv("OCI_GENAI_ENDPOINT",
                         "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/v1")
        )
        self.default_model = default_model or os.getenv("OCI_GENAI_MODEL", os.getenv("OPENAI_MODEL", DEFAULT_MODEL))
        self._client = None

    @property
    def client(self) -> AsyncOpenAI:
        if AsyncOpenAI is None:
            raise RuntimeError("openai package is not installed")
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return self._client

    def get_model_id(self, model_key: Optional[str] = None) -> str:
        """Resolve model key to model ID."""
        if model_key and model_key in SUPPORTED_MODELS:
            return model_key
        return self.default_model

    async def analyze(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Send analysis request and return complete response.

        If credentials are missing or the endpoint rejects authentication, raise
        the original error so callers can decide whether to fall back to demo
        mode.
        """
        model_id = self.get_model_id(model)
        resp = await self.client.responses.create(
            model=model_id,
            input=prompt,
            max_output_tokens=max_tokens,
        )
        return resp.output_text if hasattr(resp, "output_text") else str(resp)


    async def _retry_with_backoff(self, func, max_retries: int = 3, base_delay: float = 60.0):
        """Execute function with exponential backoff retry on rate limit errors.

        Args:
            func: Async function to execute
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds (doubles each retry)

        Returns:
            Result from the function

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                return await func()
            except RateLimitError as e:
                last_exception = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Rate limit hit, retrying in {delay:.0f}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Rate limit exceeded after {max_retries} attempts")
                    raise
            except Exception as e:
                # Check if it's a 429 error wrapped in a generic exception
                error_str = str(e)
                if "429" in error_str or "resource-exhausted" in error_str or "rate" in error_str.lower():
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Rate limit detected, retrying in {delay:.0f}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"Rate limit exceeded after {max_retries} attempts")
                        raise
                else:
                    raise

        raise last_exception

    async def analyze_with_tools(
        self,
        prompt: str,
        model: Optional[str] = None,
        tools: Optional[list[dict]] = None,
        image_inputs: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Send a tool-enabled analysis request with rate limit handling.

        If auth fails, let the caller decide whether to fall back to demo mode.
        """
        model_id = self.get_model_id(model)
        image_inputs = self._normalize_image_inputs(image_inputs, token_budget=200000)
        content = [{"type": "input_text", "text": prompt}]
        for img in (image_inputs or []):
            b64 = img.get("base64") or ""
            if not b64:
                continue
            content.append({
                "type": "input_image",
                "image_url": f"data:{img.get('mime_type', 'image/png')};base64,{b64}",
            })

        async def _call():
            resp = await self.client.responses.create(
                model=model_id,
                input=[{"role": "user", "content": content}],
                tools=tools or [],
                max_output_tokens=max_tokens,
            )
            return resp.output_text if hasattr(resp, "output_text") else str(resp)

        return await self._retry_with_backoff(_call)

    async def analyze_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        image_inputs: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """Send analysis request and yield streaming response chunks with rate limit handling."""
        model_id = self.get_model_id(model)
        image_inputs = self._normalize_image_inputs(image_inputs, token_budget=200000)
        content = [{"type": "input_text", "text": prompt}]
        for img in (image_inputs or []):
            b64 = img.get("base64") or ""
            if not b64:
                continue
            content.append({"type": "input_image", "image_url": f"data:{img.get('mime_type', 'image/png')};base64,{b64}"})

        max_retries = 3
        base_delay = 60.0

        for attempt in range(max_retries):
            try:
                stream = await self.client.responses.create(
                    model=model_id,
                    input=[{"role": "user", "content": content}],
                    max_output_tokens=max_tokens,
                    stream=True,
                )
                async for event in stream:
                    if hasattr(event, "delta") and event.delta:
                        yield event.delta
                    elif hasattr(event, "output_text_delta") and event.output_text_delta:
                        yield event.output_text_delta
                return  # Success, exit the retry loop
            except RateLimitError as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Rate limit hit in stream, retrying in {delay:.0f}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                else:
                    yield f"\n[Error: Rate limit exceeded after {max_retries} attempts: {str(e)}]"
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "resource-exhausted" in error_str:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Rate limit detected in stream, retrying in {delay:.0f}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                    else:
                        yield f"\n[Error: Rate limit exceeded after {max_retries} attempts: {str(e)}]"
                else:
                    yield f"\n[Error: {str(e)}]"
                    return

    def list_models(self) -> list[dict]:
        """List available models."""
        return [
            {"id": k, **v}
            for k, v in SUPPORTED_MODELS.items()
        ]
