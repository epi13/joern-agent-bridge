"""Hardened subprocess execution with bounded output and process-tree cleanup."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from collections.abc import Mapping, Sequence
from contextlib import suppress
from pathlib import Path

from .errors import JoernExecutionError
from .models import ProcessResult

_ENV_ALLOWLIST = (
    "HOME",
    "LANG",
    "LC_ALL",
    "PATH",
    "JAVA_HOME",
    "TMPDIR",
    "XDG_CACHE_HOME",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
)


def sanitized_environment(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    env = {key: os.environ[key] for key in _ENV_ALLOWLIST if key in os.environ}
    env.setdefault("LANG", "C.UTF-8")
    env.setdefault("PATH", "/usr/local/bin:/usr/bin:/bin")
    if extra:
        for key, value in extra.items():
            if key not in _ENV_ALLOWLIST:
                raise ValueError(f"Environment variable is not allowed: {key}")
            env[key] = value
    return env


def _bounded_decode(value: bytes, limit: int) -> tuple[str, bool]:
    truncated = len(value) > limit
    if truncated:
        value = value[:limit]
    return value.decode("utf-8", errors="replace"), truncated


def run_process(
    argv: Sequence[str | Path],
    *,
    cwd: Path,
    timeout: float,
    output_limit: int = 2_000_000,
    env: Mapping[str, str] | None = None,
) -> ProcessResult:
    args = [str(item) for item in argv]
    if not args or not Path(args[0]).is_absolute():
        raise ValueError("Executable must be an absolute path")
    started = time.monotonic()
    process = subprocess.Popen(  # noqa: S603
        args,
        cwd=cwd,
        env=sanitized_environment(env),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout_raw, stderr_raw = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=2)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
        stdout_raw, stderr_raw = process.communicate()
        stdout, stdout_truncated = _bounded_decode(stdout_raw, output_limit)
        stderr, stderr_truncated = _bounded_decode(stderr_raw, output_limit)
        raise JoernExecutionError(
            "process_timeout",
            f"Process exceeded {timeout:.1f}s timeout",
            details={
                "argv": args,
                "stdout": stdout,
                "stderr": stderr,
                "stdout_truncated": stdout_truncated,
                "stderr_truncated": stderr_truncated,
            },
            retryable=True,
        ) from exc

    stdout, stdout_truncated = _bounded_decode(stdout_raw, output_limit)
    stderr, stderr_truncated = _bounded_decode(stderr_raw, output_limit)
    return ProcessResult(
        argv=args,
        returncode=process.returncode,
        stdout=stdout,
        stderr=stderr,
        duration_ms=round((time.monotonic() - started) * 1000),
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
    )
