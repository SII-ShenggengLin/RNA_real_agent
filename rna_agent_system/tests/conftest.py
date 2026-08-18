from __future__ import annotations

import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load .env early so that skipif conditions can see DEEPSEEK_API_KEY
load_dotenv()


def pytest_configure():
    # Ensure `agent_core` is importable.
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def pytest_addoption(parser):
    parser.addoption(
        "--live-llm",
        action="store_true",
        default=False,
        help="Run live LLM tests that require a valid DEEPSEEK_API_KEY",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--live-llm"):
        skip_live = pytest.mark.skip(
            reason="Requires --live-llm flag and valid DEEPSEEK_API_KEY"
        )
        for item in items:
            if "live_llm" in item.keywords:
                item.add_marker(skip_live)


# ═══════════════════════════════════════════════════════════════════════════════
# Shared fixtures (previously duplicated across comprehensive test files)
# ═════════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def _hermetic_calibrated_runtime(monkeypatch):
    """Keep the suite hermetic: no platform CapGate unless a test opts in.

    ``AgentRunner`` reads ``RNADA_CAPGATE`` at construction; tests default to
    ``off`` and configure ``CalibratedRuntime`` explicitly when testing gates.
    """
    from agent_core.calibrated.runtime import CalibratedRuntime

    CalibratedRuntime.clear()
    monkeypatch.setenv("RNADA_CAPGATE", "off")
    yield
    CalibratedRuntime.clear()


@pytest.fixture(scope="module")
def executor():
    """Build a ToolExecutor with the default tool registry."""
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
    return ToolExecutor(build_default_tool_registry())


@pytest.fixture(scope="module")
def registry(executor):
    """Build a CapabilityRegistry backed by *executor*."""
    from agent_core.capabilities.base import build_default_capability_registry
    return build_default_capability_registry(executor)


@pytest.fixture(autouse=True)
def _workspace_dir():
    """Ensure the workspace directory exists before each test.

    Previously duplicated in 7 layer-3 test files.
    """
    from agent_core.file_manager import PROJECT_ROOT
    ws = PROJECT_ROOT / "workspace"
    ws.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Shared live-LLM connectivity test (previously duplicated in 7 comprehensive files)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.live_llm
def test_deepseek_api_connectivity():
    """Verify DeepSeek API is reachable and returns sensible output."""
    from langchain_core.messages import HumanMessage, SystemMessage

    from agent_core.llm_config import get_deepseek_llm

    llm = get_deepseek_llm(temperature=0.1)
    messages = [
        SystemMessage(
            content="You are a helpful assistant. Reply with a single JSON object containing keys 'status' and 'message'."
        ),
        HumanMessage(content="Say hello and confirm the API works. Return JSON only."),
    ]
    response = llm.invoke(messages)
    content = response.content if hasattr(response, "content") else str(response)

    assert content and len(content) >= 5, f"Empty or too-short response: {content!r}"
    assert "hello" in content.lower() or "status" in content.lower(), (
        f"Unexpected response: {content[:100]!r}"
    )
