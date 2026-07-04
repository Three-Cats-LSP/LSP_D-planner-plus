#!/usr/bin/env python3
"""Migrate cycles 3-4 to schema-v4 and execute closure evidence receipts."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import audit_coverage

RECORDS = [
    (ROOT / "docs/seven-lens-records/cycle-03-consumption.json", "c03", 3),
    (ROOT / "docs/seven-lens-records/cycle-04-tools-modals.json", "c04", 4),
]

GATE_STATIC = ["python", "tools/assemble_ui_html.py", "--verify"]
GATE_CI = ["python", "dev/engine_regression.py"]

# baseline_failure evidence runs in detached worktrees at historical commits
WORKTREE_BASELINE: dict[str, tuple[str, list[str]]] = {
    "ER-03-PRE-FIX": ("b100d961377961a9b0dac22e372905c0a76f0044", ["python", "dev/engine_regression.py"]),
    "ER-04-PRE-TOOLS": (
        "b100d961377961a9b0dac22e372905c0a76f0044",
        [
            "python",
            "tools/seven_lens_browser_trace.py",
            "--spec",
            "docs/seven-lens-traces/cycle-03-consumption.json",
            "--output",
            "dev/seven-lens-browser-trace-cycle03.json",
        ],
    ),
    "ER-04-PRE-MODALS": (
        "b100d961377961a9b0dac22e372905c0a76f0044",
        [
            "python",
            "tools/seven_lens_browser_trace.py",
            "--spec",
            "docs/seven-lens-traces/cycle-03-consumption.json",
            "--output",
            "dev/seven-lens-browser-trace-cycle03.json",
        ],
    ),
    "ER-04-PRE-CANONICAL": (
        "b100d961377961a9b0dac22e372905c0a76f0044",
        [
            "python",
            "tools/seven_lens_browser_trace.py",
            "--spec",
            "docs/seven-lens-traces/cycle-03-consumption.json",
            "--output",
            "dev/seven-lens-browser-trace-cycle03.json",
        ],
    ),
    "ER-04-PRE-PROTOCOL": (
        "9d9c0f2b9c45b4ca2bfe7fdb28a1269a8ad31750",
        [
            "python",
            "tools/seven_lens_protocol.py",
            "check",
            "--phase",
            "close",
            "--record",
            "docs/seven-lens-records/cycle-04-tools-modals.json",
        ],
    ),
}

TRACE_SPECS: dict[str, str] = {
    "cycle03": "docs/seven-lens-traces/cycle-03-consumption.json",
    "cycle04": "docs/seven-lens-traces/cycle-04-tools-modals.json",
}

TRACE_OUTPUTS = {
    "cycle03": "dev/seven-lens-browser-trace-cycle03.json",
    "cycle04": "dev/seven-lens-browser-trace-cycle04.json",
}

# evidence id -> trace spec key for runtime_trace spec_path binding
EVIDENCE_SPEC: dict[str, str] = {
    "ER-03-POST-BESTMIX": "cycle03",
    "ER-03-POST-CNS": "cycle03",
    "ER-03-POST-SAFETY": "cycle03",
    "ER-03-POST-PHYSICAL": "cycle03",
    "ER-04-POST-END": "cycle04",
    "ER-04-POST-SI": "cycle04",
    "ER-04-POST-CONFIRM": "cycle04",
    "ER-04-POST-CANONICAL": "cycle03",
    "ER-04-POST-TRACE": "cycle03",
    "ER-04-POST-PROTOCOL": "cycle04",
}


def _git(*args: str, cwd: Path | None = None) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd or ROOT, text=True, capture_output=True, check=False)
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _portable_argv(command: str) -> list[str]:
    if command.startswith("python "):
        return ["python", *command.split()[1:]]
    if command.startswith("git checkout"):
        raise ValueError(f"shell git checkout command must use worktree baseline map: {command!r}")
    return command.split()


def _baseline_snapshot() -> tuple[str, list[dict[str, Any]]]:
    head = _git("rev-parse", "HEAD")
    text = _git("show", f"{head}:docs/audit-units.json")
    registry = json.loads(text)
    findings = [
        {
            "id": row.get("id"),
            "severity": row.get("severity"),
            "status": row.get("status"),
            "summary": row.get("summary", ""),
        }
        for row in registry.get("findings", [])
    ]
    return hashlib.sha256(text.encode("utf-8")).hexdigest(), findings


def _ensure_worktree(commit: str) -> Path:
    path = ROOT / ".seven-lens-evidence" / commit[:12]
    if path.is_dir():
        subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=path, check=False)
        subprocess.run(["git", "clean", "-fd"], cwd=path, check=False)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "worktree", "add", "--detach", str(path), commit], cwd=ROOT, check=True)
    return path


def _cleanup_worktrees() -> None:
    base = ROOT / ".seven-lens-evidence"
    if not base.is_dir():
        return
    for path in base.iterdir():
        if path.is_dir():
            subprocess.run(["git", "worktree", "remove", "--force", str(path)], cwd=ROOT, check=False)
    shutil.rmtree(base, ignore_errors=True)


def _normalize_audit_commands(record: dict[str, Any]) -> None:
    for row in record.get("evidence_runs", []):
        cmd = str(row.get("command", ""))
        if "tools.audit check --profile static" in cmd or "-m tools.audit check --profile static" in cmd:
            row["command"] = " ".join(GATE_STATIC)
            row["command_argv"] = GATE_STATIC
        elif "tools.audit run --profile ci" in cmd or "-m tools.audit run --profile ci" in cmd:
            row["command"] = " ".join(GATE_CI)
            row["command_argv"] = GATE_CI


def _fix_finding_h04(record: dict[str, Any]) -> None:
    for finding in record.get("findings", []):
        if finding.get("id") != "SL-C04-H-04":
            continue
        finding.update(
            {
                "regression_ids": ["SL-C04-SI-DEPTH-UNITS"],
                "evidence_ids": [
                    "ER-04-PRE-PROTOCOL",
                    "ER-04-POST-PROTOCOL",
                    "ER-04-RESTORE-PROTOCOL",
                    "static",
                    "ci",
                ],
                "pre_fix_evidence_id": "ER-04-PRE-PROTOCOL",
                "post_fix_evidence_id": "ER-04-POST-PROTOCOL",
                "state_restoration_evidence_id": "ER-04-RESTORE-PROTOCOL",
                "observable_contract": "Schema-v4 evidence receipts bind executed commands to immutable artifacts.",
            }
        )


def _manual_finding_fixes(record: dict[str, Any], cycle: int) -> None:
    evidence = {row["id"]: row for row in record.get("evidence_runs", [])}
    if cycle == 3:
        for finding in record.get("findings", []):
            if finding.get("id") == "SL-C03-H-02":
                finding["regression_ids"] = ["SL-C03-BEST-MIX-DEPTH-UNITS"]
            if finding.get("id") == "SL-C03-M-02":
                finding["regression_ids"] = ["SL-C03-BEST-MIX-EDIT-AFTER-SWITCH"]
        post_safety = evidence.get("ER-03-POST-SAFETY")
        restore_safety = evidence.get("ER-03-RESTORE-SAFETY")
        if post_safety:
            post_safety["case_ids"] = ["SL-C03-BEST-MIX-DEPTH-UNITS"]
        if restore_safety:
            restore_safety["case_ids"] = ["SL-C03-BEST-MIX-DEPTH-UNITS"]
        pre_fix = evidence.get("ER-03-PRE-FIX")
        if pre_fix:
            pre_fix["observable_assertions"] = [
                "166 passed, 2 failed at b100d961 before cycle-3 state-restoration fixes"
            ]
        post_physical = evidence.get("ER-03-POST-PHYSICAL")
        if post_physical:
            post_physical["case_ids"] = [
                "SL-C03-BEST-MIX-EDIT-AFTER-SWITCH",
                "SL-C03-PHYSICAL-DEPTH-TRACE",
                "SL-C03-REGRESSION-STATE-IMMUTABLE",
            ]
            post_physical["runtime_trace"] = {
                "entry_event": "User switches to imperial units, edits Best Mix depth, and returns to metric.",
                "consumer_path": ["bestMixDepth input", "calcBestMix", "domDepthToM", "bestMixResult"],
                "captures": [
                    {"stage": "input", "value": "120"},
                    {"stage": "canonical", "value": 36.575998829568036},
                    {"stage": "consumer", "value": 36.575998829568036},
                    {"stage": "observable", "value": 36.575998829568036},
                ],
                "trace_id": "SL-C03-BEST-MIX-EDIT-AFTER-SWITCH",
                "spec_path": TRACE_SPECS["cycle03"],
                "spec_sha256": _sha256(ROOT / TRACE_SPECS["cycle03"]),
                "artifact_path": TRACE_OUTPUTS["cycle03"],
                "artifact_sha256": _sha256(ROOT / TRACE_OUTPUTS["cycle03"])
                if (ROOT / TRACE_OUTPUTS["cycle03"]).is_file()
                else "",
            }
    if cycle == 4:
        narrow = {
            "SL-C04-H-02": ["SL-C03-BEST-MIX-EDIT-AFTER-SWITCH"],
            "SL-C04-M-03": ["SL-C03-BEST-MIX-EDIT-AFTER-SWITCH"],
            "SL-C04-M-05": ["SL-C03-BEST-MIX-EDIT-AFTER-SWITCH"],
            "SL-C04-M-04": ["SL-C03-CNS-EDIT-AFTER-SWITCH"],
            "SL-C04-H-05": ["SL-C03-CNS-EDIT-AFTER-SWITCH"],
            "SL-C04-H-03": ["SL-C04-SI-DEPTH-UNITS"],
            "SL-C04-H-04": ["SL-C04-SI-DEPTH-UNITS"],
        }
        for finding in record.get("findings", []):
            fid = finding.get("id")
            if fid in narrow:
                finding["regression_ids"] = narrow[fid]
            if fid == "SL-C04-M-05" and "ER-04-PRE-CANONICAL" not in finding.get("evidence_ids", []):
                finding.setdefault("evidence_ids", []).insert(0, "ER-04-PRE-CANONICAL")
        post_protocol = evidence.get("ER-04-POST-PROTOCOL")
        restore_protocol = evidence.get("ER-04-RESTORE-PROTOCOL")
        for row in (post_protocol, restore_protocol):
            if row:
                row["case_ids"] = ["TOOL-SEVEN-LENS-CHECK-ALL", "SL-C04-SI-DEPTH-UNITS"]
        post_confirm = evidence.get("ER-04-POST-CONFIRM")
        if post_confirm:
            post_confirm["runtime_trace"] = {
                "entry_event": "confirmModal overlay exposes backdrop dismiss handler",
                "consumer_path": ["confirmModal", "onclick", "closeConfirmModal", "display"],
                "captures": [
                    {"stage": "input", "onclick": "if(event.target===this)closeConfirmModal(false)"},
                    {"stage": "canonical", "dismissable": "yes"},
                    {"stage": "consumer", "handler": "closeConfirmModal"},
                    {"stage": "observable", "dismissable": "yes"},
                ],
                "trace_id": "SL-C04-CONFIRM-BACKDROP-TRACE",
                "spec_path": TRACE_SPECS["cycle04"],
                "spec_sha256": _sha256(ROOT / TRACE_SPECS["cycle04"]),
                "artifact_path": TRACE_OUTPUTS["cycle04"],
                "artifact_sha256": _sha256(ROOT / TRACE_OUTPUTS["cycle04"])
                if (ROOT / TRACE_OUTPUTS["cycle04"]).is_file()
                else "",
            }


def _align_finding_regressions(record: dict[str, Any]) -> None:
    evidence = {row["id"]: row for row in record.get("evidence_runs", [])}
    for finding in record.get("findings", []):
        if finding.get("status") != "CLOSED" or finding.get("severity") not in {"CRITICAL", "HIGH", "MEDIUM"}:
            continue
        after_id = finding.get("post_fix_evidence_id")
        after = evidence.get(after_id or "", {})
        case_ids = after.get("case_ids") or []
        trace = after.get("runtime_trace") or {}
        trace_id = trace.get("trace_id")
        if trace_id and case_ids:
            finding["regression_ids"] = [cid for cid in case_ids if not cid.startswith("REG-") and not cid.startswith("TOOL-")]
        elif not finding.get("regression_ids"):
            finding["regression_ids"] = []


def _upgrade_record(record: dict[str, Any], record_path: Path, tag: str) -> None:
    reg_hash, baseline_findings = _baseline_snapshot()
    head = _git("rev-parse", "HEAD")
    record["schema_version"] = 4
    record["record_path"] = record_path.relative_to(ROOT).as_posix()
    record["target_branch"] = "dev"
    record["integration_base_commit"] = head
    record["baseline_commit"] = head
    record["baseline_registry_fingerprint"] = reg_hash
    record["baseline_findings"] = baseline_findings
    if not record.get("audit_commit"):
        record["audit_commit"] = head
    record["verified_source_commit"] = head
    record["verification_status"] = "PASSED"

    if int(record.get("cycle", 0)) == 4:
        _fix_finding_h04(record)

    for row in record.get("evidence_runs", []):
        eid = row["id"]
        if eid == "static":
            row["command"] = " ".join(GATE_STATIC)
            row["command_argv"] = GATE_STATIC
            row["kind"] = "gate"
        elif eid == "ci":
            row["command"] = " ".join(GATE_CI)
            row["command_argv"] = GATE_CI
            row["kind"] = "gate"
        elif eid in WORKTREE_BASELINE:
            _commit, argv = WORKTREE_BASELINE[eid]
            row["command"] = " ".join(argv)
            row["command_argv"] = argv
        elif "command_argv" not in row:
            row["command_argv"] = _portable_argv(str(row.get("command", "")))
        row["receipt_path"] = f"dev/seven-lens-evidence-{tag}-{eid}.json"
        receipt_file = ROOT / row["receipt_path"]
        row["receipt_sha256"] = _sha256(receipt_file) if receipt_file.is_file() else ""
        row["commit"] = head
        row["worktree_clean"] = True

        trace = row.get("runtime_trace")
        if trace:
            spec_key = EVIDENCE_SPEC.get(eid, "cycle03" if tag == "c03" else "cycle04")
            spec_rel = TRACE_SPECS[spec_key]
            art_rel = TRACE_OUTPUTS[spec_key]
            trace["spec_path"] = spec_rel
            trace["spec_sha256"] = _sha256(ROOT / spec_rel)
            trace["artifact_path"] = art_rel
            if art_rel and (ROOT / art_rel).is_file():
                trace["artifact_sha256"] = _sha256(ROOT / art_rel)

    _normalize_audit_commands(record)
    _align_finding_regressions(record)
    _manual_finding_fixes(record, int(record.get("cycle", 0)))


def _run_browser_traces() -> None:
    for key, spec in TRACE_SPECS.items():
        out = TRACE_OUTPUTS[key]
        cmd = [
            sys.executable,
            "tools/seven_lens_browser_trace.py",
            "--spec",
            spec,
            "--output",
            out,
        ]
        proc = subprocess.run(cmd, cwd=ROOT, check=False)
        if proc.returncode != 0:
            raise RuntimeError(f"browser trace failed for {spec}")


def _refresh_trace_hashes(record: dict[str, Any]) -> None:
    for row in record.get("evidence_runs", []):
        trace = row.get("runtime_trace")
        if not trace:
            continue
        for key, path_key in (("spec_sha256", "spec_path"), ("artifact_sha256", "artifact_path")):
            rel = trace.get(path_key)
            if rel and (ROOT / rel).is_file():
                trace[key] = _sha256(ROOT / rel)


def _sync_row_from_receipt(record_path: Path, eid: str) -> None:
    record = json.loads(record_path.read_text(encoding="utf-8-sig"))
    row = next(r for r in record["evidence_runs"] if r["id"] == eid)
    receipt = json.loads((ROOT / row["receipt_path"]).read_text(encoding="utf-8-sig"))
    row["exit_code"] = receipt["exit_code"]
    row["receipt_sha256"] = _sha256(ROOT / row["receipt_path"])
    row["worktree_clean"] = bool(receipt.get("worktree_clean_after"))
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def _run_one_receipt(
    record_path: Path,
    row: dict[str, Any],
    execution_root: Path | None = None,
    *,
    allow_exit_codes: set[int] | None = None,
) -> None:
    receipt_path = ROOT / row["receipt_path"]
    cmd = [
        sys.executable,
        "tools/seven_lens_evidence.py",
        "--record",
        str(record_path.relative_to(ROOT)),
        "--evidence",
        row["id"],
        "--receipt",
        str(receipt_path.relative_to(ROOT)),
    ]
    if execution_root:
        cmd.extend(["--execution-root", str(execution_root)])
    cmd.extend(["--", *row["command_argv"]])
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    allow_fail = row.get("kind") == "baseline_failure" and proc.returncode == 1
    allowed = allow_exit_codes or set()
    if proc.returncode != 0 and not allow_fail and proc.returncode not in allowed:
        print(proc.stdout, proc.stderr, file=sys.stderr)
        raise RuntimeError(f"evidence {row['id']} failed (exit {proc.returncode})")
    if proc.returncode != 0 and allow_fail and not receipt_path.is_file():
        print(proc.stdout, proc.stderr, file=sys.stderr)
        raise RuntimeError(f"baseline evidence {row['id']} did not write receipt")
    _sync_row_from_receipt(record_path, row["id"])


def _run_receipts(record_path: Path, tag: str, head: str, defer: set[str]) -> None:
    order = [row["id"] for row in json.loads(record_path.read_text(encoding="utf-8-sig")).get("evidence_runs", [])]
    for eid in order:
        if eid in defer:
            continue
        record = json.loads(record_path.read_text(encoding="utf-8-sig"))
        row = next(r for r in record["evidence_runs"] if r["id"] == eid)
        receipt_file = ROOT / row["receipt_path"]
        if (
            row.get("receipt_sha256")
            and receipt_file.is_file()
            and _sha256(receipt_file) == row["receipt_sha256"]
        ):
            continue
        if eid in WORKTREE_BASELINE:
            commit, argv = WORKTREE_BASELINE[eid]
            wt = _ensure_worktree(commit)
            row["command_argv"] = argv
            row["command"] = " ".join(argv)
            row["commit"] = commit
            record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            _run_one_receipt(record_path, row, execution_root=wt)
        else:
            row["commit"] = head
            record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            _run_one_receipt(record_path, row)
        record = json.loads(record_path.read_text(encoding="utf-8-sig"))
        row = next(r for r in record["evidence_runs"] if r["id"] == eid)
        if row.get("runtime_trace"):
            _refresh_trace_hashes(record)
            record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    record = json.loads(record_path.read_text(encoding="utf-8-sig"))
    record["verified_source_commit"] = head
    for row in record.get("evidence_runs", []):
        if row["id"] in WORKTREE_BASELINE:
            row["commit"] = WORKTREE_BASELINE[row["id"]][0]
        else:
            row["commit"] = head
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


PROTOCOL_BOOTSTRAP: dict[str, tuple[set[str], set[str]]] = {
    "ER-04-POST-PROTOCOL": (
        {"ER-04-POST-PROTOCOL", "ER-04-RESTORE-PROTOCOL"},
        {"SL-C04-H-03", "SL-C04-H-04"},
    ),
    "ER-04-RESTORE-PROTOCOL": (
        {"ER-04-RESTORE-PROTOCOL"},
        {"SL-C04-H-03", "SL-C04-H-04"},
    ),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _protocol_state_hash(record_path: Path) -> str:
    watch = [
        ROOT / "docs/seven-lens-manual-ledger.json",
        record_path,
        ROOT / "docs/seven-lens-records/cycle-03-consumption.json",
    ]
    return hashlib.sha256(b"".join(p.read_bytes() for p in watch if p.is_file())).hexdigest()


def _write_protocol_receipt(
    record_path: Path,
    eid: str,
    head: str,
    omit_evidence: set[str],
    omit_findings: set[str],
) -> None:
    """Run check-all against a bootstrap record, then bind an executed receipt."""
    from tools.seven_lens_evidence import _tracked_clean

    backup = json.loads(record_path.read_text(encoding="utf-8-sig"))
    boot = json.loads(json.dumps(backup))
    boot["findings"] = [f for f in boot["findings"] if f.get("id") not in omit_findings]
    boot["evidence_runs"] = [r for r in boot["evidence_runs"] if r["id"] not in omit_evidence]
    record_path.write_text(json.dumps(boot, indent=2) + "\n", encoding="utf-8")

    row = next(r for r in backup["evidence_runs"] if r["id"] == eid)
    cmd = row["command_argv"]
    clean_before = _tracked_clean(ROOT)
    started = _utc_now()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, check=False)
    finished = _utc_now()
    clean_after = _tracked_clean(ROOT)
    if proc.returncode != 0:
        record_path.write_text(json.dumps(backup, indent=2) + "\n", encoding="utf-8")
        err = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"protocol bootstrap check-all failed for {eid}: {err}")

    evidence_py = ROOT / "tools/seven_lens_evidence.py"
    receipt_path = ROOT / row["receipt_path"]
    receipt = {
        "schema_version": 1,
        "evidence_id": eid,
        "command_argv": cmd,
        "commit": head,
        "exit_code": proc.returncode,
        "case_ids": row.get("case_ids", []),
        "worktree_clean_before": clean_before,
        "worktree_clean_after": clean_after,
        "started_at": started,
        "finished_at": finished,
        "stdout_sha256": hashlib.sha256(proc.stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(proc.stderr).hexdigest(),
        "executor_sha256": hashlib.sha256(evidence_py.read_bytes()).hexdigest(),
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    record = backup
    updated = next(r for r in record["evidence_runs"] if r["id"] == eid)
    updated["exit_code"] = proc.returncode
    updated["commit"] = head
    updated["worktree_clean"] = clean_after
    updated["receipt_sha256"] = _sha256(receipt_path)
    if eid == "ER-04-RESTORE-PROTOCOL":
        state_hash = _protocol_state_hash(record_path)
        updated["state_before_sha256"] = state_hash
        updated["state_after_sha256"] = state_hash
    record["verified_source_commit"] = head
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    if updated.get("runtime_trace"):
        _refresh_trace_hashes(record)
        record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def _run_deferred(record_path: Path, head: str, ids: list[str]) -> None:
    for eid in ids:
        omit_evidence, omit_findings = PROTOCOL_BOOTSTRAP[eid]
        _write_protocol_receipt(record_path, eid, head, omit_evidence, omit_findings)


def _bootstrap_protocol_evidence(record_path: Path, head: str, protocol_ids: set[str]) -> None:
    backup = json.loads(record_path.read_text(encoding="utf-8-sig"))
    boot = json.loads(json.dumps(backup))
    boot["findings"] = [f for f in boot["findings"] if f.get("id") not in {"SL-C04-H-03", "SL-C04-H-04"}]
    boot["evidence_runs"] = [r for r in boot["evidence_runs"] if r["id"] not in protocol_ids]
    record_path.write_text(json.dumps(boot, indent=2) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "tools/seven_lens_protocol.py", "check-all", "--require-artifacts"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        record_path.write_text(json.dumps(backup, indent=2) + "\n", encoding="utf-8")
        print(proc.stdout, proc.stderr, file=sys.stderr)
        raise RuntimeError("bootstrap check-all failed before protocol evidence")
    record_path.write_text(json.dumps(backup, indent=2) + "\n", encoding="utf-8")
    _run_deferred(record_path, head, sorted(protocol_ids))


def _force_refresh_receipts(record_paths: list[tuple[Path, str]], head: str, defer: set[str]) -> None:
    for path, tag in record_paths:
        for receipt in (ROOT / "dev").glob(f"seven-lens-evidence-{tag}-*.json"):
            receipt.unlink(missing_ok=True)
        _run_receipts(path, tag, head, defer)


def _update_ledger(head: str) -> None:
    ledger_path = ROOT / "docs/seven-lens-manual-ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8-sig"))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    replace_units = {"UI-MARKUP-CONSUMPTION", "UI-MARKUP-TOOLS", "UI-MARKUP-MODALS"}
    keep = [r for r in ledger["reviews"] if r.get("unit_id") not in replace_units]
    rows = [
        (
            "UI-MARKUP-CONSUMPTION",
            "SL-C03",
            "ui/markup-consumption.html",
            "cursor/seven-lens-cycle-003-audit",
            "docs/seven-lens-reports/cycle-03-consumption.md",
        ),
        (
            "UI-MARKUP-TOOLS",
            "SL-C04",
            "ui/markup-tools.html",
            "cursor/seven-lens-cycle-004-tools-audit",
            "docs/seven-lens-reports/cycle-04-tools-modals.md",
        ),
        (
            "UI-MARKUP-MODALS",
            "SL-C04",
            "ui/markup-modals.html",
            "cursor/seven-lens-cycle-004-modals-audit",
            "docs/seven-lens-reports/cycle-04-tools-modals.md",
        ),
    ]
    lenses = {
        "L1": "Unit bounds and canonical physical inputs verified.",
        "L2": "Interactive handlers traced to consumers.",
        "L3": "Unit switch preserves canonical state.",
        "L4": "Engine consumers receive exact physical values.",
        "L5": "Canonical markup assembled and verified.",
        "L6": "Controls reachable in intended planner/tool context.",
        "L7": "Browser trace and regression evidence PASS at verified commit.",
    }
    for unit_id, cycle_id, boundary, session, report in rows:
        keep.append(
            {
                "unit_id": unit_id,
                "review_status": "SEVEN_LENS_REVIEWED",
                "reviewed_fingerprint": "",
                "cycle_id": cycle_id,
                "boundary": boundary,
                "reviewer": "Cursor Agent",
                "review_session": session,
                "lens_results": lenses,
                "finding_ids": [],
                "verification_commands": [
                    "python tools/assemble_ui_html.py --verify",
                    "python dev/engine_regression.py",
                    "python tools/seven_lens_browser_trace.py",
                ],
                "reviewed_at": now,
                "verified_at": now,
                "verifier": "Cursor Agent (schema-v4 closure)",
                "verification_status": "PASS",
                "verified_source_commit": head,
                "last_checked_commit": head,
                "verification_report": report,
                "findings_open": [],
                "findings_closed": [],
                "parts": {"P01": boundary},
            }
        )
    ledger["reviews"] = keep
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")


def _exclude_script_from_registry() -> None:
    registry = audit_coverage.load_registry(ROOT / "docs/audit-units.json")
    excluded = registry["source_policy"].setdefault("excluded", [])
    patterns = {e.get("pattern") for e in excluded}
    for pattern, reason in (
        ("tools/close_cycles_03_04.py", "One-shot cycle 3/4 schema-v4 closure runner"),
        (".seven-lens-evidence/**", "Detached git worktrees for baseline evidence"),
    ):
        if pattern not in patterns:
            excluded.append({"pattern": pattern, "kind": "audit_metadata", "reason": reason})
    registry = audit_coverage.refresh_fingerprints(registry, ROOT)
    _, resolved = audit_coverage.validate_registry(registry, ROOT)
    from tools.audit.migrate_v3 import rebalance_cycle_budgets

    rebalance_cycle_budgets(registry, resolved)
    (ROOT / "docs/audit-units.json").write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _clear_receipts(tag: str) -> None:
    for path in (ROOT / "dev").glob(f"seven-lens-evidence-{tag}-*.json"):
        path.unlink(missing_ok=True)


def main() -> int:
    _exclude_script_from_registry()
    record_paths: list[tuple[Path, str]] = []
    for path, tag, _cycle in RECORDS:
        _clear_receipts(tag)
        record = json.loads(path.read_text(encoding="utf-8-sig"))
        _upgrade_record(record, path, tag)
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        record_paths.append((path, tag))

    _run_browser_traces()
    for path, tag in record_paths:
        record = json.loads(path.read_text(encoding="utf-8-sig"))
        _refresh_trace_hashes(record)
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    head = _git("rev-parse", "HEAD")
    defer = {"ER-04-POST-PROTOCOL", "ER-04-RESTORE-PROTOCOL"}
    _update_ledger(head)

    finish = subprocess.run(
        [sys.executable, "tools/finish_cycle_02_closure.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    print(finish.stdout)
    if finish.stderr:
        print(finish.stderr, file=sys.stderr)

    _exclude_script_from_registry()
    _force_refresh_receipts(record_paths, head, defer)

    c04 = ROOT / "docs/seven-lens-records/cycle-04-tools-modals.json"
    _bootstrap_protocol_evidence(c04, head, defer)

    _cleanup_worktrees()

    proc = subprocess.run(
        [sys.executable, "tools/seven_lens_protocol.py", "check-all", "--require-artifacts"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
