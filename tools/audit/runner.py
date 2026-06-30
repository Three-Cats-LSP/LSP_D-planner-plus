from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .model import SuiteResult


def _command(tokens: list[str]) -> list[str]:
    return [sys.executable if token == "{python}" else token for token in tokens]


def run_suites(root: Path, registry: dict[str, Any], profile: str) -> list[SuiteResult]:
    selected = [suite for suite in registry.get("suite_catalog", []) if profile in suite.get("profiles", [])]
    cache: dict[tuple[tuple[str, ...], tuple[tuple[str, str], ...]], SuiteResult] = {}
    results: list[SuiteResult] = []
    for suite in selected:
        command = _command(suite["command"])
        env_overrides = {str(key): str(value) for key, value in suite.get("env", {}).items()}
        key = (tuple(command), tuple(sorted(env_overrides.items())))
        if key in cache:
            prior = cache[key]
            results.append(
                SuiteResult(
                    id=suite["id"], status=prior.status, command=command,
                    exit_code=prior.exit_code, duration_ms=0,
                    stdout=f"Deduplicated with {prior.id}",
                )
            )
            continue
        started = time.perf_counter()
        try:
            proc = subprocess.run(
                command,
                cwd=root,
                env={**os.environ, **env_overrides},
                text=True,
                capture_output=True,
                timeout=suite["timeout_seconds"],
            )
            result = SuiteResult(
                id=suite["id"],
                status="PASS" if proc.returncode == 0 else "FAIL",
                command=command,
                exit_code=proc.returncode,
                duration_ms=int((time.perf_counter() - started) * 1000),
                stdout=(proc.stdout or "")[-12000:],
                stderr=(proc.stderr or "")[-12000:],
            )
        except subprocess.TimeoutExpired as exc:
            result = SuiteResult(
                id=suite["id"], status="ERROR", command=command, exit_code=None,
                duration_ms=int((time.perf_counter() - started) * 1000),
                stdout=(exc.stdout or "")[-12000:] if isinstance(exc.stdout, str) else "",
                stderr=(exc.stderr or "")[-12000:] if isinstance(exc.stderr, str) else "",
                error=f"timed out after {suite['timeout_seconds']} seconds",
            )
        except OSError as exc:
            result = SuiteResult(
                id=suite["id"], status="ERROR", command=command, exit_code=None,
                duration_ms=int((time.perf_counter() - started) * 1000), error=str(exc),
            )
        cache[key] = result
        results.append(result)
    return results
