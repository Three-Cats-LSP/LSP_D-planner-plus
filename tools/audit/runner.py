from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .case_report import load_suite_cases, results_path, validate_suite_cases
from .model import SuiteResult


def _command(tokens: list[str]) -> list[str]:
    return [sys.executable if token == "{python}" else token for token in tokens]


def _finalize_suite(
    root: Path,
    suite: dict[str, Any],
    proc: subprocess.CompletedProcess[str] | None,
    *,
    started: float,
    error: str | None = None,
) -> SuiteResult:
    suite_id = suite["id"]
    command = _command(suite["command"])
    declared = list(suite.get("case_ids", []))
    payload = load_suite_cases(root, suite_id)
    case_errors = validate_suite_cases(suite_id, declared, payload)
    case_results = list(payload.get("cases", [])) if payload else []
    exit_code = None if proc is None else proc.returncode
    proc_failed = exit_code not in (0, None)
    status = "ERROR" if error else ("FAIL" if proc_failed or case_errors else "PASS")
    return SuiteResult(
        id=suite_id,
        status=status,
        command=command,
        exit_code=exit_code,
        duration_ms=int((time.perf_counter() - started) * 1000),
        stdout=(proc.stdout or "")[-12000:] if proc else "",
        stderr=(proc.stderr or "")[-12000:] if proc else "",
        error=error,
        case_results=case_results,
        case_errors=case_errors,
    )


def run_suites(root: Path, registry: dict[str, Any], profile: str) -> list[SuiteResult]:
    selected = [suite for suite in registry.get("suite_catalog", []) if profile in suite.get("profiles", [])]
    cache: dict[tuple[tuple[str, ...], tuple[tuple[str, str], ...]], SuiteResult] = {}
    results: list[SuiteResult] = []
    for suite in selected:
        command = _command(suite["command"])
        env_overrides = {str(key): str(value) for key, value in suite.get("env", {}).items()}
        env = {**os.environ, **env_overrides, "LSP_AUDIT_SUITE_ID": suite["id"]}
        key = (tuple(command), tuple(sorted(env_overrides.items())))
        if key in cache:
            prior = cache[key]
            results.append(
                SuiteResult(
                    id=suite["id"], status=prior.status, command=command,
                    exit_code=prior.exit_code, duration_ms=0,
                    stdout=f"Deduplicated with {prior.id}",
                    case_results=list(prior.case_results),
                    case_errors=list(prior.case_errors),
                )
            )
            continue
        started = time.perf_counter()
        results_path(root, suite["id"]).unlink(missing_ok=True)
        try:
            proc = subprocess.run(
                command,
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
                timeout=suite["timeout_seconds"],
            )
            result = _finalize_suite(root, suite, proc, started=started)
        except subprocess.TimeoutExpired as exc:
            result = SuiteResult(
                id=suite["id"], status="ERROR", command=command, exit_code=None,
                duration_ms=int((time.perf_counter() - started) * 1000),
                stdout=(exc.stdout or "")[-12000:] if isinstance(exc.stdout, str) else "",
                stderr=(exc.stderr or "")[-12000:] if isinstance(exc.stderr, str) else "",
                error=f"timed out after {suite['timeout_seconds']} seconds",
                case_errors=[f"{suite['id']}: suite timed out before emitting case results"],
            )
        except OSError as exc:
            result = SuiteResult(
                id=suite["id"], status="ERROR", command=command, exit_code=None,
                duration_ms=int((time.perf_counter() - started) * 1000), error=str(exc),
                case_errors=[f"{suite['id']}: {exc}"],
            )
        cache[key] = result
        results.append(result)
    return results
