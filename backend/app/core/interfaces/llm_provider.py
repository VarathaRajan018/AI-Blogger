"""Abstract base class for LLM providers.

All LLM providers (Gemini, OpenAI, Claude, Groq) implement this
interface, enabling provider-agnostic usage throughout the pipeline.

Usage:
    # Pipeline stages only depend on this interface:
    provider: BaseLLMProvider = llm_router.get_provider("content_generator")
    result = await provider.generate_text("Write a blog post about...")
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Type

from pydantic import BaseModel


@dataclass
class LLMResponse:
    """Standardized response from an LLM provider.

    Attributes:
        content: The generated text content.
        provider: Name of the provider that generated this response.
        model: Model identifier used.
        prompt_tokens: Number of tokens in the prompt.
        completion_tokens: Number of tokens in the completion.
        total_tokens: Total tokens used.
        raw_response: Provider-specific raw response object.
    """

    content: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    raw_response: Any = None

    @property
    def estimated_cost_usd(self) -> float:
        """Estimate cost based on provider pricing.

        Override in subclasses for more accurate per-provider pricing.
        Uses a rough average of $0.005 per 1K tokens as default.
        """
        return (self.total_tokens / 1000) * 0.005


@dataclass
class LLMConfig:
    """Configuration for an LLM generation call.

    Attributes:
        temperature: Controls randomness (0.0 = deterministic, 1.0 = creative).
        max_tokens: Maximum tokens in the response.
        top_p: Nucleus sampling parameter.
        stop_sequences: Sequences that stop generation.
    """

    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 0.95
    stop_sequences: list[str] = field(default_factory=list)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM provider implementations.

    All concrete providers (GeminiProvider, OpenAIProvider, etc.)
    must implement these methods. Pipeline stages interact with
    LLMs exclusively through this interface.
    """

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        """Generate text from a prompt.

        Args:
            prompt: The user prompt/instruction.
            system_prompt: Optional system-level instruction.
            config: Generation configuration overrides.

        Returns:
            LLMResponse with generated text and token usage.
        """
        ...

    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        schema: Type[BaseModel],
        system_prompt: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> BaseModel:
        """Generate structured JSON output matching a Pydantic schema.

        Args:
            prompt: The user prompt/instruction.
            schema: Pydantic model class defining the expected output structure.
            system_prompt: Optional system-level instruction.
            config: Generation configuration overrides.

        Returns:
            An instance of the provided Pydantic schema.

        Raises:
            ValueError: If LLM output cannot be parsed into the schema.
        """
        ...

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the canonical name of this provider.

        Returns:
            Provider name string (e.g., "gemini", "openai", "claude").
        """
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model identifier being used.

        Returns:
            Model name string (e.g., "gemini-1.5-pro", "gpt-4o").
        """
        ...
