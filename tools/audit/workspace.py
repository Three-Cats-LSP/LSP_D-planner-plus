from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def tracked_status(root: Path) -> set[str]:
    proc = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=root, text=True, capture_output=True, check=False,
    )
    return {line for line in proc.stdout.splitlines() if line.strip()}


def commit(root: Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=root,
        text=True, capture_output=True, check=False,
    )
    return proc.stdout.strip() or "unknown"


def snapshot_generated(root: Path, registry: dict[str, Any]) -> tuple[dict[Path, bytes], set[Path]]:
    patterns = ["site-assets-manifest.txt", "tests/ccr-differential/*.json"]
    for entry in registry.get("source_policy", {}).get("generated", []):
        reason = entry.get("reason", "")
        if "Regression output" in reason or "golden" in reason.lower():
            patterns.append(entry["pattern"])
    matched: set[Path] = set()
    for pattern in patterns:
        matched.update(path for path in root.glob(pattern) if path.is_file())
    return ({path: path.read_bytes() for path in matched}, matched)


def restore_generated(root: Path, registry: dict[str, Any], snapshot: dict[Path, bytes], original: set[Path]) -> None:
    patterns = ["site-assets-manifest.txt", "tests/ccr-differential/*.json"]
    for entry in registry.get("source_policy", {}).get("generated", []):
        reason = entry.get("reason", "")
        if "Regression output" in reason or "golden" in reason.lower():
            patterns.append(entry["pattern"])
    current: set[Path] = set()
    for pattern in patterns:
        current.update(path for path in root.glob(pattern) if path.is_file())
    for path in current - original:
        path.unlink()
    for path, content in snapshot.items():
        path.write_bytes(content)
