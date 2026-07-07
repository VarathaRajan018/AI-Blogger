"""LLM Router — selects and manages LLM provider instances.

Routes LLM requests to the configured provider per module,
with fallback support and usage tracking.

Usage:
    router = LLMRouter(settings)
    provider = router.get_provider("content_generator")
    response = await provider.generate_text("Write a blog post...")
"""

from __future__ import annotations

from typing import Optional

from app.config import Settings
from app.core.interfaces.llm_provider import BaseLLMProvider
from app.utils.logging import get_logger

logger = get_logger(__name__)


class LLMRouter:
    """Routes LLM requests to the appropriate provider.

    Each pipeline module can have its own preferred provider configured
    via settings. If a module-specific provider is not configured,
    the default provider is used.

    Supported providers: gemini, openai, claude, groq
    """

    # Map of module names to settings field names
    MODULE_PROVIDER_MAP: dict[str, str] = {
        "content_generator": "llm_content_provider",
        "market_analyzer": "llm_market_analysis_provider",
        "keyword_researcher": "llm_keyword_provider",
        "social_media_generator": "llm_social_provider",
    }

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._providers: dict[str, BaseLLMProvider] = {}

        logger.info(
            "llm router initialized",
            default_provider=settings.llm_default_provider,
        )

    def _create_provider(self, provider_name: str) -> BaseLLMProvider:
        """Create a new provider instance by name.

        Args:
            provider_name: One of 'gemini', 'openai', 'claude', 'groq'.

        Returns:
            Configured BaseLLMProvider instance.

        Raises:
            ValueError: If provider name is not recognized or API key is missing.
        """
        if provider_name == "gemini":
            from app.providers.llm.gemini_provider import GeminiProvider

            if not self._settings.gemini_api_key:
                raise ValueError("GEMINI_API_KEY is not configured")

            return GeminiProvider(
                api_key=self._settings.gemini_api_key,
                model=self._settings.gemini_model,
                temperature=self._settings.gemini_temperature,
            )

        elif provider_name == "openai":
            # Phase 3: OpenAI provider implementation
            raise NotImplementedError(
                "OpenAI provider not yet implemented. Coming in Phase 3."
            )

        elif provider_name == "claude":
            # Phase 5: Claude provider implementation
            raise NotImplementedError(
                "Claude provider not yet implemented. Coming in Phase 5."
            )

        elif provider_name == "groq":
            # Phase 5: Groq provider implementation
            raise NotImplementedError(
                "Groq provider not yet implemented. Coming in Phase 5."
            )

        else:
            raise ValueError(
                f"Unknown LLM provider: {provider_name}. "
                f"Supported: gemini, openai, claude, groq"
            )

    def get_provider(self, module_name: Optional[str] = None) -> BaseLLMProvider:
        """Get the LLM provider for a specific pipeline module.

        Resolution order:
        1. Module-specific provider (e.g., llm_content_provider=openai)
        2. Default provider (llm_default_provider=gemini)

        Args:
            module_name: Pipeline module requesting the provider.
                If None, returns the default provider.

        Returns:
            BaseLLMProvider instance (cached after first creation).

        Raises:
            ValueError: If no valid provider can be resolved.
        """
        # Determine which provider to use
        provider_name = self._settings.llm_default_provider

        if module_name and module_name in self.MODULE_PROVIDER_MAP:
            setting_field = self.MODULE_PROVIDER_MAP[module_name]
            module_provider = getattr(self._settings, setting_field, "")
            if module_provider:
                provider_name = module_provider

        # Return cached provider if available
        if provider_name in self._providers:
            return self._providers[provider_name]

        # Create and cache new provider
        logger.info(
            "creating llm provider",
            provider=provider_name,
            module=module_name or "default",
        )
        provider = self._create_provider(provider_name)
        self._providers[provider_name] = provider
        return provider

    def get_default_provider(self) -> BaseLLMProvider:
        """Get the default LLM provider.

        Returns:
            The default BaseLLMProvider instance.
        """
        return self.get_provider(module_name=None)
