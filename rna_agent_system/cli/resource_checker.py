"""CLI resource pre-check utilities.

Checks GPU availability (via nvidia-smi) and system resources (via psutil)
before launching the RNA Design Agent interactive session.
"""

from __future__ import annotations

import shutil
import subprocess

import psutil


def check_gpu(min_vram_gb: int = 24) -> tuple[bool, str]:
    """Check for at least one NVIDIA GPU with sufficient VRAM.

    Parameters
    ----------
    min_vram_gb:
        Minimum required video memory in GB (default 24, i.e. RTX 4090 class).

    Returns
    -------
    (passed, message)
        *passed* is ``True`` when at least one GPU has ``>= min_vram_gb`` GB.
        If ``nvidia-smi`` is missing, returns ``(False, "nvidia-smi 未找到...")``.
    """
    if shutil.which("nvidia-smi") is None:
        return False, "nvidia-smi 未找到，请确保已安装 NVIDIA 驱动"

    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        return False, f"nvidia-smi 执行失败: {exc.stderr.strip()}"

    lines = [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]
    if not lines:
        return False, "未检测到 NVIDIA GPU"

    for line in lines:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2:
            try:
                vram_mb = float(parts[1])
                vram_gb = vram_mb / 1024.0
                if vram_gb >= min_vram_gb:
                    return True, f"检测到 GPU: {parts[0]} ({vram_gb:.1f} GB)"
            except ValueError:
                continue

    return False, f"未检测到显存 >= {min_vram_gb}GB 的 GPU"


def check_system_resources(min_ram_gb: int = 16, max_cpu_percent: int = 90) -> tuple[bool, str]:
    """Check available RAM and current CPU usage.

    Parameters
    ----------
    min_ram_gb:
        Minimum free RAM in GB.
    max_cpu_percent:
        Maximum acceptable overall CPU usage percentage.

    Returns
    -------
    (passed, message)
    """
    mem = psutil.virtual_memory()
    free_ram_gb = mem.available / (1024 ** 3)
    cpu_percent = psutil.cpu_percent(interval=1)

    issues: list[str] = []
    if free_ram_gb < min_ram_gb:
        issues.append(f"空闲内存不足: {free_ram_gb:.1f} GB (要求 >= {min_ram_gb} GB)")
    if cpu_percent > max_cpu_percent:
        issues.append(f"CPU 使用率过高: {cpu_percent:.1f}% (要求 <= {max_cpu_percent}%)")

    if issues:
        return False, "; ".join(issues)
    return True, f"系统资源正常 (空闲内存 {free_ram_gb:.1f} GB, CPU {cpu_percent:.1f}%)"


def check_all() -> tuple[bool, str]:
    """Run GPU and system-resource checks sequentially.

    Returns
    -------
    (passed, message)
        ``passed`` is ``True`` only when **both** checks pass.
    """
    gpu_ok, gpu_msg = check_gpu()
    sys_ok, sys_msg = check_system_resources()

    if gpu_ok and sys_ok:
        return True, f"{gpu_msg}; {sys_msg}"

    messages: list[str] = []
    if not gpu_ok:
        messages.append(gpu_msg)
    if not sys_ok:
        messages.append(sys_msg)
    return False, "; ".join(messages)
