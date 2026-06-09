"""Minimal runtime abstraction for executable tools.

This module complements ``tool_interface.py`` (spec/contracts) by providing a
small execution layer with:
- standardized return payloads
- timeout/error handling
- Python-function tool wrapper
- CLI/subprocess tool wrapper
"""

from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Type

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ToolExecutionError(RuntimeError):
    """Raised when a command exits with non-zero status."""

    def __init__(
        self,
        message: str,
        return_code: Optional[int] = None,
        command: Optional[Sequence[str]] = None,
        stdout: str = "",
        stderr: str = "",
    ):
        super().__init__(message)
        self.return_code = return_code
        self.command = list(command) if command is not None else None
        self.stdout = stdout
        self.stderr = stderr


class ToolTimeoutError(TimeoutError):
    """Raised when tool execution exceeds timeout."""

    def __init__(self, message: str, stdout: str = "", stderr: str = ""):
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr


class ToolResult(BaseModel):
    """Standardized runtime result returned by tool wrappers."""

    model_config = ConfigDict(extra="allow")

    success: bool
    tool_name: str
    stdout: str = ""
    stderr: str = ""
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[Dict[str, Any]] = None
    elapsed_time: float = 0.0


class CommandExecutionOutput(BaseModel):
    """Raw subprocess execution output."""

    command: list[str]
    stdout: str = ""
    stderr: str = ""
    return_code: int
    elapsed_time: float


def assemble_command(base_command: Sequence[str], extra_args: Optional[Sequence[str]] = None) -> list[str]:
    """Compose a subprocess argv list from base command and extra args."""

    if not base_command:
        raise ValueError("base_command must not be empty.")
    command = [str(part) for part in base_command]
    if extra_args:
        command.extend(str(part) for part in extra_args)
    return command


def command_to_shell_string(command: Sequence[str]) -> str:
    """Render argv as a shell-safe string for logs/errors."""

    return " ".join(shlex.quote(str(part)) for part in command)


def run_subprocess_command(
    command: Sequence[str],
    timeout_seconds: float,
    cwd: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    check: bool = True,
) -> CommandExecutionOutput:
    """Execute subprocess command with timeout and normalized errors."""

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be > 0.")

    start_ts = time.perf_counter()
    merged_env: Optional[Dict[str, str]] = None
    if env is not None:
        merged_env = dict(os.environ)
        merged_env.update(env)

    try:
        completed = subprocess.run(
            [str(part) for part in command],
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
            env=merged_env,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - start_ts
        message = f"Command timed out after {timeout_seconds:.3f}s: {command_to_shell_string(command)}"
        raise ToolTimeoutError(
            message,
            stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
            stderr=(exc.stderr or "") if isinstance(exc.stderr, str) else "",
        ) from exc

    elapsed = time.perf_counter() - start_ts
    output = CommandExecutionOutput(
        command=[str(part) for part in command],
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        return_code=int(completed.returncode),
        elapsed_time=elapsed,
    )

    if check and output.return_code != 0:
        raise ToolExecutionError(
            message=(
                f"Command failed with exit code {output.return_code}: "
                f"{command_to_shell_string(output.command)}"
            ),
            return_code=output.return_code,
            command=output.command,
            stdout=output.stdout,
            stderr=output.stderr,
        )
    return output


@contextmanager
def managed_temp_dir(prefix: str = "tool_runtime_"):
    """Create and cleanup a temporary directory for one tool run."""

    with tempfile.TemporaryDirectory(prefix=prefix) as tmp_dir:
        yield Path(tmp_dir)


class BaseExecutableTool(ABC):
    """Common executable tool contract for function/CLI wrappers."""

    def __init__(
        self,
        name: str,
        description: str,
        input_model: Optional[Type[BaseModel]] = None,
        timeout_seconds: float = 30.0,
    ):
        self.name = name
        self.description = description
        self.input_model = input_model
        self.timeout_seconds = timeout_seconds

    def _normalize_input(self, raw_input: Optional[Mapping[str, Any]]) -> Any:
        payload = dict(raw_input or {})
        if self.input_model is None:
            return payload
        try:
            return self.input_model.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(f"Input validation failed for `{self.name}`: {exc}") from exc

    @abstractmethod
    def _execute(self, parsed_input: Any, timeout_seconds: float) -> ToolResult:
        """Execute tool-specific logic and return ``ToolResult``."""

    def run(self, raw_input: Optional[Mapping[str, Any]] = None, timeout_seconds: Optional[float] = None) -> ToolResult:
        """Run tool with standardized timeout/error handling."""

        timeout = timeout_seconds if timeout_seconds is not None else self.timeout_seconds
        started = time.perf_counter()
        try:
            parsed_input = self._normalize_input(raw_input)
            result = self._execute(parsed_input, timeout)
            if result.tool_name != self.name:
                result.tool_name = self.name
            if result.elapsed_time <= 0:
                result.elapsed_time = time.perf_counter() - started
            return result
        except ToolTimeoutError as exc:
            elapsed = time.perf_counter() - started
            return ToolResult(
                success=False,
                tool_name=self.name,
                stdout=getattr(exc, "stdout", ""),
                stderr=getattr(exc, "stderr", ""),
                error={"type": "timeout", "message": str(exc)},
                elapsed_time=elapsed,
            )
        except Exception as exc:  # Keep broad catch for unified error payload.
            elapsed = time.perf_counter() - started
            error_payload: Dict[str, Any] = {
                "type": type(exc).__name__,
                "message": str(exc),
            }
            if isinstance(exc, ToolExecutionError):
                error_payload["return_code"] = exc.return_code
                error_payload["command"] = exc.command
            return ToolResult(
                success=False,
                tool_name=self.name,
                stdout=getattr(exc, "stdout", ""),
                stderr=getattr(exc, "stderr", ""),
                error=error_payload,
                elapsed_time=elapsed,
            )


class PythonFunctionTool(BaseExecutableTool):
    """Wrapper for pure-Python callable tools."""

    def __init__(
        self,
        name: str,
        description: str,
        func: Callable[[Any], Any],
        input_model: Optional[Type[BaseModel]] = None,
        timeout_seconds: float = 30.0,
    ):
        super().__init__(name=name, description=description, input_model=input_model, timeout_seconds=timeout_seconds)
        self.func = func

    def _execute(self, parsed_input: Any, timeout_seconds: float) -> ToolResult:
        start_ts = time.perf_counter()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.func, parsed_input)
            try:
                payload = future.result(timeout=timeout_seconds)
            except FutureTimeoutError as exc:
                raise ToolTimeoutError(
                    f"Python function tool timed out after {timeout_seconds:.3f}s: {self.name}"
                ) from exc
        elapsed = time.perf_counter() - start_ts

        if isinstance(payload, ToolResult):
            payload.tool_name = self.name
            if payload.elapsed_time <= 0:
                payload.elapsed_time = elapsed
            return payload

        if isinstance(payload, Mapping):
            return ToolResult(
                success=bool(payload.get("success", True)),
                tool_name=self.name,
                stdout=str(payload.get("stdout", "")),
                stderr=str(payload.get("stderr", "")),
                artifacts=dict(payload.get("artifacts", {})),
                metrics=dict(payload.get("metrics", {})),
                error=payload.get("error"),
                elapsed_time=float(payload.get("elapsed_time", elapsed)),
            )

        return ToolResult(
            success=True,
            tool_name=self.name,
            artifacts={"result": payload},
            elapsed_time=elapsed,
        )

    def invoke(self, input_dict: Mapping[str, Any]) -> ToolResult:
        """LangChain-compatible entry point for ``ToolExecutor`` and registry dispatch."""

        return self.run(dict(input_dict))


class CommandLineTool(BaseExecutableTool):
    """Wrapper for external CLI tools executed via subprocess."""

    def __init__(
        self,
        name: str,
        description: str,
        base_command: Sequence[str],
        arg_builder: Optional[Callable[[Any], Sequence[str]]] = None,
        input_model: Optional[Type[BaseModel]] = None,
        timeout_seconds: float = 30.0,
        cwd: Optional[Path] = None,
        env: Optional[Mapping[str, str]] = None,
    ):
        super().__init__(name=name, description=description, input_model=input_model, timeout_seconds=timeout_seconds)
        self.base_command = [str(part) for part in base_command]
        self.arg_builder = arg_builder
        self.cwd = cwd
        self.env = dict(env) if env is not None else None

    def _build_args(self, parsed_input: Any) -> Sequence[str]:
        if self.arg_builder is None:
            return []
        return self.arg_builder(parsed_input)

    def _execute(self, parsed_input: Any, timeout_seconds: float) -> ToolResult:
        args = self._build_args(parsed_input)
        command = assemble_command(self.base_command, args)
        output = run_subprocess_command(
            command=command,
            timeout_seconds=timeout_seconds,
            cwd=self.cwd,
            env=self.env,
            check=True,
        )
        return ToolResult(
            success=True,
            tool_name=self.name,
            stdout=output.stdout,
            stderr=output.stderr,
            artifacts={"command": output.command},
            metrics={"return_code": output.return_code},
            elapsed_time=output.elapsed_time,
        )
