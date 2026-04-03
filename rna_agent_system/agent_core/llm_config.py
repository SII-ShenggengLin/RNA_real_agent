"""Centralized LLM configuration for internal OpenAI-compatible gateway."""

from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def get_llm() -> ChatOpenAI:
    """Create a ChatOpenAI client for the internal gateway."""
    return ChatOpenAI(
        model=os.getenv("LLM_MODEL_NAME"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE"),
        temperature=0.1,
        http_client=httpx.Client(verify=False),
        max_retries=1,
    )
