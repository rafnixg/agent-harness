

import os

from app.providers.antropic_provider import AnthropicProvider
from app.providers.base import LLMProvider, GenerationSettings, LLMResponse, ToolCallRequest
from app.providers.openai_compat_provider import OpenAICompatProvider
from app.providers.registry import ProviderSpec, find_by_name


def _build_provider_config(
    provider_name: str,
) -> tuple[ProviderSpec, str | None, str | None]:
    """Resolve provider spec, API key and base URL using ProviderSpec metadata."""
    spec = find_by_name(provider_name)
    if spec is None:
        raise RuntimeError(f"Unknown provider: {provider_name}")

    api_key = os.getenv(str(spec.env_key)) if spec.env_key else None
    base_env = f"{spec.name.upper()}_BASE_URL"
    base_url = os.getenv(base_env) or spec.default_base_url or None

    if spec.env_key and not api_key and not spec.is_oauth and not spec.is_direct:
        raise RuntimeError(f"{spec.env_key} is not set")

    return spec, api_key, base_url



def build_llm_provider(provider_name: str, model: str) -> LLMProvider:
    """Create a concrete LLMProvider based on ProviderSpec backend."""
    spec, api_key, base_url = _build_provider_config(provider_name)

    if spec.backend == "openai_compat":
        return OpenAICompatProvider(
            api_key=api_key,
            base_url=base_url,
            default_model=model,
            spec=spec,
        )

    if spec.backend == "anthropic":
        return AnthropicProvider(
            api_key=api_key,
            api_base=base_url,
            default_model=model,
        )

    raise RuntimeError(f"Unsupported provider backend: {spec.backend}")
