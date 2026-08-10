"""Centralized LLM configuration — multi-provider support.

All providers are accessed through ``langchain_openai.ChatOpenAI`` because
the major model vendors (DeepSeek, OpenAI, Alibaba/Qwen, Google/Gemini,
Anthropic via compatible proxies) all expose an OpenAI-compatible chat
completions endpoint.

Environment variables per provider
----------------------------------
+----------+-------------------+-------------------------------------------+
| Provider | Variable          | Default                                   |
+----------+-------------------+-------------------------------------------+
| deepseek | DEEPSEEK_API_KEY  | —                                         |
|          | DEEPSEEK_BASE_URL | https://api.deepseek.com                  |
|          | DEEPSEEK_MODEL    | deepseek-v4-pro                           |
+----------+-------------------+-------------------------------------------+
| openai   | OPENAI_API_KEY    | —                                         |
|          | OPENAI_BASE_URL   | https://api.openai.com/v1                 |
|          | OPENAI_MODEL      | gpt-4                                     |
+----------+-------------------+-------------------------------------------+
| anthropic| ANTHROPIC_API_KEY | —                                         |
|          | ANTHROPIC_BASE_URL| https://api.anthropic.com/v1              |
|          | ANTHROPIC_MODEL   | claude-3-5-sonnet-20241022                |
+----------+-------------------+-------------------------------------------+
| alibaba  | ALIBABA_API_KEY   | —                                         |
|          | ALIBABA_BASE_URL  | https://dashscope.aliyuncs.com/compatible-mode/v1 |
|          | ALIBABA_MODEL     | qwen2.5-72b-instruct                      |
+----------+-------------------+-------------------------------------------+
| google   | GOOGLE_API_KEY    | —                                         |
|          | GOOGLE_BASE_URL   | https://generativelanguage.googleapis.com/v1beta/openai/ |
|          | GOOGLE_MODEL      | gemma-2-27b-it                            |
+----------+-------------------+-------------------------------------------+

Notes
-----
- Anthropic native API is *not* OpenAI-compatible.  If you do not have a
  compatible proxy, set ``ANTHROPIC_BASE_URL`` to an OpenRouter endpoint
  (e.g. ``https://openrouter.ai/api/v1``) or install ``langchain-anthropic``
  and subclass the loader.
- Google Gemini also exposes an OpenAI-compatible endpoint under
  ``/v1beta/openai/``; the default above uses that path.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Provider registry
# ─────────────────────────────────────────────────────────────────────────────

_PROVIDER_DEFAULTS: Dict[str, Dict[str, str]] = {
    "deepseek": {
        "env_api_key": "DEEPSEEK_API_KEY",
        "env_base_url": "DEEPSEEK_BASE_URL",
        "env_model": "DEEPSEEK_MODEL",
        "default_base_url": "https://api.deepseek.com",
        "default_model": "deepseek-v4-pro",
    },
    "openai": {
        "env_api_key": "OPENAI_API_KEY",
        "env_base_url": "OPENAI_BASE_URL",
        "env_model": "OPENAI_MODEL",
        "default_base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4",
    },
    "anthropic": {
        "env_api_key": "ANTHROPIC_API_KEY",
        "env_base_url": "ANTHROPIC_BASE_URL",
        "env_model": "ANTHROPIC_MODEL",
        "default_base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-3-5-sonnet-20241022",
    },
    "alibaba": {
        "env_api_key": "ALIBABA_API_KEY",
        "env_base_url": "ALIBABA_BASE_URL",
        "env_model": "ALIBABA_MODEL",
        "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen2.5-72b-instruct",
    },
    "google": {
        "env_api_key": "GOOGLE_API_KEY",
        "env_base_url": "GOOGLE_BASE_URL",
        "env_model": "GOOGLE_MODEL",
        "default_base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemma-2-27b-it",
    },
}

# Friendly name → provider key mapping (matches benchmark backend names)
_BACKEND_NAME_TO_PROVIDER: Dict[str, str] = {
    "deepseek-v4-pro": "deepseek",
    "deepseek": "deepseek",
    "gpt-4": "openai",
    "gpt-3.5-turbo": "openai",
    "openai": "openai",
    "claude-3-5-sonnet": "anthropic",
    "claude": "anthropic",
    "anthropic": "anthropic",
    "qwen2.5-72b": "alibaba",
    "qwen": "alibaba",
    "alibaba": "alibaba",
    "gemma-2-27b": "google",
    "gemma": "google",
    "google": "google",
}


def _resolve_provider(provider: str) -> str:
    """Normalize a provider or backend name to the internal provider key."""
    key = provider.lower().replace(" ", "-").replace("_", "-")
    if key in _PROVIDER_DEFAULTS:
        return key
    mapped = _BACKEND_NAME_TO_PROVIDER.get(key)
    if mapped:
        return mapped
    raise ValueError(
        f"Unknown LLM provider '{provider}'. "
        f"Supported: {list(_PROVIDER_DEFAULTS.keys())}"
    )


def get_llm_for_provider(
    provider: str,
    *,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.1,
    timeout: float = 120.0,
    max_retries: int = 2,
    **extra_kwargs: Any,
) -> ChatOpenAI:
    """Create a ``ChatOpenAI`` client for the requested provider.

    Args:
        provider: One of ``deepseek``, ``openai``, ``anthropic``, ``alibaba``,
            ``google``, or a friendly backend name such as ``gpt-4`` or
            ``qwen2.5-72b``.
        model: Overrides the default model for this provider.
        api_key: Overrides the environment-variable API key.
        base_url: Overrides the default endpoint.
        temperature: Sampling temperature.
        timeout: HTTP request timeout in seconds.
        max_retries: Number of retries on transient errors.
        **extra_kwargs: Forwarded to ``ChatOpenAI``.

    Returns:
        A configured ``ChatOpenAI`` instance.
    """
    pkey = _resolve_provider(provider)
    cfg = _PROVIDER_DEFAULTS[pkey]

    resolved_model = model or os.getenv(cfg["env_model"], cfg["default_model"])
    resolved_api_key = api_key or os.getenv(cfg["env_api_key"], "")
    resolved_base_url = base_url or os.getenv(cfg["env_base_url"], cfg["default_base_url"])

    if not resolved_api_key:
        raise RuntimeError(
            f"Provider '{pkey}' requires an API key. "
            f"Set the environment variable {cfg['env_api_key']} or pass api_key=."
        )

    return ChatOpenAI(
        model=resolved_model,
        api_key=resolved_api_key,
        base_url=resolved_base_url,
        temperature=temperature,
        timeout=timeout,
        http_client=httpx.Client(timeout=timeout),
        max_retries=max_retries,
        **extra_kwargs,
    )


def get_deepseek_llm(
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.1,
) -> ChatOpenAI:
    """Backward-compatible helper: create a ChatOpenAI client for DeepSeek."""
    return get_llm_for_provider(
        "deepseek",
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
    )


def list_supported_providers() -> list[str]:
    """Return the list of supported provider keys."""
    return list(_PROVIDER_DEFAULTS.keys())
