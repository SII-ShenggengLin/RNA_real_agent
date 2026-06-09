"""Factory for creating LLM planner instances with multi-provider support.

Set ``PLANNER_BACKEND`` environment variable to choose the backend:
- ``llm`` → ``LLMPlanner`` (default)

Use ``PLANNER_PROVIDER`` to select the LLM provider:
- ``deepseek`` → DeepSeek V4 (default)
- ``openai`` → OpenAI GPT-4 / GPT-3.5
- ``anthropic`` → Anthropic Claude
- ``alibaba`` → Alibaba Qwen
- ``google`` → Google Gemma

Example::

    import os
    os.environ["PLANNER_PROVIDER"] = "openai"
    os.environ["OPENAI_API_KEY"] = "sk-..."
    planner = build_planner()
"""

from __future__ import annotations

import os
from typing import Optional

from agent_core.llm_config import get_llm_for_provider, list_supported_providers
from agent_core.planning.llm_planner import LLMPlanner


_DEFAULT_PROVIDER = os.getenv("PLANNER_PROVIDER", "deepseek")


def build_planner(
    backend: str = "llm",
    *,
    provider: Optional[str] = None,
    **llm_kwargs,
) -> LLMPlanner:
    """Return a concrete ``LLMPlanner`` instance.

    Args:
        backend: Planner backend type. Currently only ``"llm"`` is supported.
        provider: LLM provider name (e.g. ``"deepseek"``, ``"openai"``,
            ``"anthropic"``, ``"alibaba"``, ``"google"``).  Falls back to the
            ``PLANNER_PROVIDER`` environment variable, then ``"deepseek"``.
        **llm_kwargs: Forwarded to ``get_llm_for_provider`` (e.g.
            ``temperature``, ``model``, ``api_key``).

    Returns:
        An initialized ``LLMPlanner`` powered by the requested provider.

    Raises:
        ValueError: If *backend* is not ``"llm"``.
        RuntimeError: If the provider API key is missing.
    """
    if backend not in ("llm",):
        raise ValueError(
            f"Unsupported planner backend: {backend!r}. Use 'llm'. "
            f"Supported providers: {list_supported_providers()}"
        )

    resolved_provider = provider or _DEFAULT_PROVIDER
    llm = get_llm_for_provider(resolved_provider, **llm_kwargs)
    return LLMPlanner(llm=llm)
