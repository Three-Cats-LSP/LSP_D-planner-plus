from __future__ import annotations

import json
import subprocess
import time
from collections import Counter
from pathlib import Path
from typing import Any

from .model import CheckResult


def parser_files(registry: dict[str, Any], root: Path | None = None) -> list[str]:
    root = root or Path(".")
    generated_patterns = {
        entry.get("pattern")
        for entry in registry.get("source_policy", {}).get("generated", [])
    }
    files: set[str] = set()
    for unit in registry.get("units", []):
        path = unit.get("path", "")
        suffix = Path(path).suffix.lower()
        if suffix not in {".js", ".mjs", ".html", ".css"}:
            continue
        if any(Path(path).match(pattern.replace("**", "*")) for pattern in generated_patterns if pattern):
            continue
        files.add(path)
    markup_paths = [
        "ui/markup-header.html",
        "ui/markup-planner.html",
        "ui/markup-consumption.html",
        "ui/markup-tools.html",
        "ui/markup-modals.html",
    ]
    for markup_path in markup_paths:
        if (root / markup_path).is_file():
            files.add(markup_path)
    return sorted(files)


def run_parser(root: Path, registry: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    request = {
        "root": root.as_posix(),
        "files": parser_files(registry, root),
        "wrappers": registry.get("parser_config", {}).get("wrappers", {}),
    }
    command = ["node", str(Path(__file__).with_name("parser_bridge.mjs"))]
    try:
        proc = subprocess.run(
            command,
            input=json.dumps(request),
            text=True,
            capture_output=True,
            cwd=root,
            timeout=90,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {}, [f"parser bridge failed: {exc}"]
    if proc.returncode != 0:
        return {}, [f"parser bridge exited {proc.returncode}: {proc.stderr.strip()}"]
    try:
        return json.loads(proc.stdout), []
    except json.JSONDecodeError as exc:
        return {}, [f"parser bridge returned invalid JSON: {exc}"]


def _base(rule: dict[str, Any], status: str, message: str, **location: Any) -> CheckResult:
    return CheckResult(
        id=rule["id"],
        status=status,
        severity=rule["severity"],
        unit_ids=list(rule["unit_ids"]),
        message=message,
        rationale=rule["rationale"],
        remediation=rule["remediation"],
        path=location.get("path"),
        line=location.get("line"),
    )


def evaluate_rules(root: Path, registry: dict[str, Any]) -> tuple[list[CheckResult], list[str]]:
    started = time.perf_counter()
    parsed, errors = run_parser(root, registry)
    if errors:
        return [], errors
    files = parsed.get("files", {})
    diagnostics = parsed.get("diagnostics", [])
    results: list[CheckResult] = []
    for rule in registry.get("rule_catalog", []):
        kind = rule["kind"]
        targets = rule.get("paths") or list(files)
        if kind == "parser.syntax":
            related = [item for item in diagnostics if item.get("path") in targets]
            if related:
                first = related[0]
                results.append(_base(rule, "FAIL", first["message"], path=first.get("path"), line=first.get("line")))
            else:
                results.append(_base(rule, "PASS", f"Parsed {len(targets)} registered source files"))
        elif kind == "js.no_duplicate_top_level_functions":
            duplicates = []
            for path in targets:
                counts = Counter(item["name"] for item in files.get(path, {}).get("functions", []))
                for name, count in counts.items():
                    if count > 1:
                        duplicates.append((path, name, count))
            if duplicates:
                path, name, count = duplicates[0]
                results.append(_base(rule, "FAIL", f"Duplicate top-level function {name} ({count}x)", path=path))
            else:
                results.append(_base(rule, "PASS", "No duplicate top-level function declarations"))
        elif kind == "html.unique_ids":
            duplicates = []
            for path in targets:
                counts = Counter(item["id"] for item in files.get(path, {}).get("ids", []))
                for name, count in counts.items():
                    if count > 1:
                        duplicates.append((path, name, count))
            if duplicates:
                path, name, count = duplicates[0]
                results.append(_base(rule, "FAIL", f"Duplicate HTML id {name} ({count}x)", path=path))
            else:
                results.append(_base(rule, "PASS", "HTML ids are unique"))
        elif kind == "html.script_order":
            path = targets[0]
            actual = [item["src"] for item in files.get(path, {}).get("scripts", []) if item.get("src")]
            required = rule.get("config", {}).get("required", [])
            cursor = -1
            missing = None
            for src in required:
                try:
                    cursor = actual.index(src, cursor + 1)
                except ValueError:
                    missing = src
                    break
            if missing:
                results.append(_base(rule, "FAIL", f"Required script order missing {missing}", path=path))
            else:
                results.append(_base(rule, "PASS", "Required runtime scripts load in canonical order"))
        elif kind == "html.css_link_order":
            path = targets[0]
            actual = [item["href"] for item in files.get(path, {}).get("stylesheets", []) if item.get("href")]
            required = rule.get("config", {}).get("required", [])
            cursor = -1
            missing = None
            for href in required:
                try:
                    cursor = actual.index(href, cursor + 1)
                except ValueError:
                    missing = href
                    break
            if missing:
                results.append(_base(rule, "FAIL", f"Required stylesheet order missing {missing}", path=path))
            else:
                results.append(_base(rule, "PASS", "Required stylesheets load in canonical order"))
        elif kind == "extract.no_reinline":
            from tools.extract_ui_cores import INLINE_FORBIDDEN_DEFS

            index_path = targets[0]
            inline = (root / index_path).read_text(encoding="utf-8")
            script_start = inline.find("<script>\n// AUDIT-UNIT:UI-RUNTIME-BOOTSTRAP")
            if script_start < 0:
                script_start = inline.rfind("<script>")
            inline_body = inline[script_start:] if script_start >= 0 else ""
            hits: list[str] = []
            for block_id, needles in INLINE_FORBIDDEN_DEFS.items():
                for needle in needles:
                    if needle in inline_body:
                        hits.append(f"{block_id}: {needle}")
            if hits:
                results.append(
                    _base(
                        rule,
                        "FAIL",
                        f"Re-inlined extracted definitions: {hits[0]}",
                        path=index_path,
                    )
                )
            else:
                results.append(_base(rule, "PASS", "No re-inlined extracted UI core definitions in index.html"))
        elif kind == "html.dom_references_resolve":
            path = targets[0]
            file_data = files.get(path, {})
            ids = {item["id"] for item in file_data.get("ids", [])}
            allowed = set(rule.get("config", {}).get("allow_missing", []))
            missing = [item for item in file_data.get("domRefs", []) if item["id"] not in ids and item["id"] not in allowed]
            if missing:
                first = missing[0]
                results.append(_base(rule, "FAIL", f"getElementById references missing id {first['id']}", path=path, line=first.get("line")))
            else:
                results.append(_base(rule, "PASS", "Literal DOM ID references resolve"))
    elapsed = int((time.perf_counter() - started) * 1000)
    for result in results:
        result.duration_ms = elapsed
    return results, []
