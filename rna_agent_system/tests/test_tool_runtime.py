from __future__ import annotations

import sys
import time

from pydantic import BaseModel, Field

from agent_core.tool_runtime import CommandLineTool, PythonFunctionTool


class _EchoInput(BaseModel):
    text: str = Field(..., min_length=1)


def _echo_func(payload: _EchoInput):
    return {
        "stdout": f"echo:{payload.text}",
        "artifacts": {"echo_text": payload.text},
        "metrics": {"chars": len(payload.text)},
    }


def test_python_function_tool_success():
    tool = PythonFunctionTool(
        name="mock_python_echo",
        description="Mock python echo tool",
        func=_echo_func,
        input_model=_EchoInput,
    )
    out = tool.run({"text": "AUGC"})
    assert out.success is True
    assert out.tool_name == "mock_python_echo"
    assert out.stdout == "echo:AUGC"
    assert out.artifacts["echo_text"] == "AUGC"
    assert out.metrics["chars"] == 4
    assert out.error is None


def test_cli_tool_non_zero_exit_returns_standard_error():
    tool = CommandLineTool(
        name="mock_cli_fail",
        description="Mock failing CLI tool",
        base_command=[sys.executable, "-c", "import sys; sys.stderr.write('boom\\n'); sys.exit(2)"],
    )
    out = tool.run({})
    assert out.success is False
    assert out.tool_name == "mock_cli_fail"
    assert out.error is not None
    assert out.error["type"] == "ToolExecutionError"
    assert out.error["return_code"] == 2
    assert "boom" in out.stderr


def test_cli_tool_timeout_returns_standard_error():
    tool = CommandLineTool(
        name="mock_cli_timeout",
        description="Mock timeout CLI tool",
        base_command=[sys.executable, "-c", "import time; time.sleep(0.2); print('done')"],
        timeout_seconds=0.05,
    )
    out = tool.run({})
    assert out.success is False
    assert out.error is not None
    assert out.error["type"] == "timeout"
    assert out.elapsed_time > 0


def test_python_function_tool_timeout_returns_standard_error():
    def _slow_tool(_payload):
        time.sleep(0.2)
        return {"stdout": "late"}

    tool = PythonFunctionTool(
        name="mock_python_timeout",
        description="Mock timeout python tool",
        func=_slow_tool,
        timeout_seconds=0.05,
    )
    out = tool.run({})
    assert out.success is False
    assert out.error is not None
    assert out.error["type"] == "timeout"
