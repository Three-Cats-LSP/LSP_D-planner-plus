from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CheckResult:
    id: str
    status: str
    severity: str
    unit_ids: list[str]
    message: str
    path: str | None = None
    line: int | None = None
    rationale: str = ""
    remediation: str = ""
    duration_ms: int = 0


@dataclass
class SuiteResult:
    id: str
    status: str
    command: list[str]
    exit_code: int | None
    duration_ms: int
    stdout: str = ""
    stderr: str = ""
    error: str | None = None
    case_results: list[dict[str, Any]] = field(default_factory=list)
    case_errors: list[str] = field(default_factory=list)


@dataclass
class AuditReport:
    schema_version: int
    profile: str
    command: str
    commit: str
    checks: list[CheckResult] = field(default_factory=list)
    suites: list[SuiteResult] = field(default_factory=list)
    effective_units: dict[str, dict[str, Any]] = field(default_factory=dict)
    invalid_findings: list[dict[str, Any]] = field(default_factory=list)
    migration: dict[str, Any] = field(default_factory=dict)
    configuration_errors: list[str] = field(default_factory=list)
    workspace_clean: bool = True
    workspace_drift: list[str] = field(default_factory=list)

    @property
    def failed(self) -> bool:
        return bool(
            self.configuration_errors
            or self.invalid_findings
            or not self.workspace_clean
            or self.workspace_drift
            or any(item.status in {"FAIL", "ERROR"} for item in self.checks)
            or any(item.status in {"FAIL", "ERROR"} for item in self.suites)
            or any(item.case_errors for item in self.suites)
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["summary"] = {
            "checks_passed": sum(item.status == "PASS" for item in self.checks),
            "checks_failed": sum(item.status in {"FAIL", "ERROR"} for item in self.checks),
            "suites_passed": sum(item.status == "PASS" for item in self.suites),
            "suites_failed": sum(item.status in {"FAIL", "ERROR"} for item in self.suites),
            "suites_skipped": sum(item.status == "SKIP" for item in self.suites),
            "ok": not self.failed,
        }
        return data
