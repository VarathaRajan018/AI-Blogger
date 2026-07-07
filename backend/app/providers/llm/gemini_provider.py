"""Google Gemini LLM provider implementation.

Uses langchain-google-genai for Gemini API access with
structured JSON output support via Pydantic schemas.
"""

from __future__ import annotations

import json
from typing import Any, Optional, Type

from pydantic import BaseModel

from app.core.interfaces.llm_provider import (
    BaseLLMProvider,
    LLMConfig,
    LLMResponse,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


# Provider-specific cost per 1K tokens (approximate, as of 2026)
GEMINI_PRICING = {
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    "gemini-2.0-flash": {"input": 0.0001, "output": 0.0004},
}


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider.

    Implements BaseLLMProvider using the langchain-google-genai package.
    Supports both free-form text and structured JSON generation.

    Args:
        api_key: Google AI Studio API key.
        model: Model identifier (default: gemini-1.5-pro).
        temperature: Default temperature for generation.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-1.5-pro",
        temperature: float = 0.7,
    ) -> None:
        if not api_key:
            raise ValueError("Gemini API key is required")

        self._api_key = api_key
        self._model = model
        self._temperature = temperature
        self._chat_model = None

        logger.info(
            "gemini provider initialized",
            model=model,
            temperature=temperature,
        )

    def _get_chat_model(self, config: Optional[LLMConfig] = None) -> Any:
        """Lazily create the LangChain ChatGoogleGenerativeAI instance.

        Args:
            config: Optional generation config overrides.

        Returns:
            ChatGoogleGenerativeAI instance.
        """
        from langchain_google_genai import ChatGoogleGenerativeAI

        temp = config.temperature if config else self._temperature
        max_tokens = config.max_tokens if config else 4096

        return ChatGoogleGenerativeAI(
            model=self._model,
            google_api_key=self._api_key,
            temperature=temp,
            max_output_tokens=max_tokens,
            convert_system_message_to_human=True,
        )

    def _build_messages(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> list[tuple[str, str]]:
        """Build message list for the chat model.

        Args:
            prompt: User prompt.
            system_prompt: Optional system instruction.

        Returns:
            List of (role, content) tuples.
        """
        messages: list[tuple[str, str]] = []
        if system_prompt:
            messages.append(("system", system_prompt))
        messages.append(("human", prompt))
        return messages

    def _extract_token_usage(self, response: Any) -> dict[str, int]:
        """Extract token usage from LangChain response metadata.

        Args:
            response: LangChain AIMessage response.

        Returns:
            Dict with prompt_tokens, completion_tokens, total_tokens.
        """
        usage = getattr(response, "usage_metadata", None)
        if usage:
            return {
                "prompt_tokens": getattr(usage, "input_tokens", 0),
                "completion_tokens": getattr(usage, "output_tokens", 0),
                "total_tokens": getattr(usage, "total_tokens", 0),
            }

        # Fallback: try response_metadata
        meta = getattr(response, "response_metadata", {})
        usage_meta = meta.get("usage_metadata", {})
        return {
            "prompt_tokens": usage_meta.get("prompt_token_count", 0),
            "completion_tokens": usage_meta.get("candidates_token_count", 0),
            "total_tokens": usage_meta.get("total_token_count", 0),
        }

    def _estimate_cost(self, tokens: dict[str, int]) -> float:
        """Estimate cost in USD based on token usage and model pricing.

        Args:
            tokens: Dict with prompt_tokens and completion_tokens.

        Returns:
            Estimated cost in USD.
        """
        pricing = GEMINI_PRICING.get(
            self._model, {"input": 0.00125, "output": 0.005}
        )
        input_cost = (tokens["prompt_tokens"] / 1000) * pricing["input"]
        output_cost = (tokens["completion_tokens"] / 1000) * pricing["output"]
        return round(input_cost + output_cost, 6)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        """Generate text using Gemini.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system instruction.
            config: Generation config overrides.

        Returns:
            LLMResponse with generated text and usage data.
        """
        model = self._get_chat_model(config)
        messages = self._build_messages(prompt, system_prompt)

        logger.debug(
            "generating text",
            provider="gemini",
            model=self._model,
            prompt_length=len(prompt),
        )

        response = await model.ainvoke(messages)
        tokens = self._extract_token_usage(response)

        logger.info(
            "text generation complete",
            provider="gemini",
            model=self._model,
            tokens=tokens,
        )

        return LLMResponse(
            content=response.content,
            provider="gemini",
            model=self._model,
            prompt_tokens=tokens["prompt_tokens"],
            completion_tokens=tokens["completion_tokens"],
            total_tokens=tokens["total_tokens"],
            raw_response=response,
        )

    async def generate_json(
        self,
        prompt: str,
        schema: Type[BaseModel],
        system_prompt: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> BaseModel:
        """Generate structured JSON output matching a Pydantic schema.

        Uses LangChain's with_structured_output for reliable
        JSON generation that conforms to the provided schema.

        Args:
            prompt: The user prompt.
            schema: Pydantic model defining expected output structure.
            system_prompt: Optional system instruction.
            config: Generation config overrides.

        Returns:
            Instance of the provided Pydantic schema.

        Raises:
            ValueError: If the response cannot be parsed into the schema.
        """
        model = self._get_chat_model(config)
        messages = self._build_messages(prompt, system_prompt)

        logger.debug(
            "generating structured json",
            provider="gemini",
            model=self._model,
            schema=schema.__name__,
        )

        # Try structured output first (native Gemini JSON mode)
        try:
            structured_model = model.with_structured_output(schema)
            result = await structured_model.ainvoke(messages)

            if isinstance(result, schema):
                logger.info(
                    "structured json generation complete",
                    provider="gemini",
                    model=self._model,
                    schema=schema.__name__,
                )
                return result
        except Exception as e:
            logger.warning(
                "structured output failed, falling back to manual parsing",
                error=str(e),
            )

        # Fallback: generate text with JSON instruction and parse manually
        json_instruction = (
            f"\n\nRespond ONLY with valid JSON matching this schema:\n"
            f"{json.dumps(schema.model_json_schema(), indent=2)}\n"
            f"Do not include any text outside the JSON object."
        )
        full_prompt = prompt + json_instruction
        messages = self._build_messages(full_prompt, system_prompt)

        response = await model.ainvoke(messages)
        content = response.content.strip()

        # Strip markdown code fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

        try:
            parsed = schema.model_validate_json(content)
            logger.info(
                "json parsed from text fallback",
                provider="gemini",
                schema=schema.__name__,
            )
            return parsed
        except Exception as parse_err:
            logger.error(
                "failed to parse json response",
                error=str(parse_err),
                raw_content=content[:500],
            )
            raise ValueError(
                f"Failed to parse Gemini response as {schema.__name__}: {parse_err}"
            ) from parse_err

    def get_provider_name(self) -> str:
        """Return 'gemini'."""
        return "gemini"

    def get_model_name(self) -> str:
        """Return the configured model identifier."""
        return self._model
