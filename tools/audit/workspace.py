from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


def tracked_status(root: Path) -> set[str]:
    proc = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=root, text=True, capture_output=True, check=False,
    )
    return {line for line in proc.stdout.splitlines() if line.strip()}


def _dirty_paths(status_lines: set[str]) -> set[Path]:
    paths: set[Path] = set()
    for line in status_lines:
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.add(Path(path))
    return paths


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_dirty_hashes(root: Path, status_lines: set[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for rel in sorted(_dirty_paths(status_lines)):
        path = root / rel
        if path.is_file():
            hashes[str(rel).replace("\\", "/")] = _file_hash(path)
    return hashes


def workspace_changed(root: Path, baseline_status: set[str]) -> tuple[bool, list[str]]:
    before_hashes = snapshot_dirty_hashes(root, baseline_status)
    after_status = tracked_status(root)
    if after_status != baseline_status:
        return False, ["tracked status lines changed"]
    drift: list[str] = []
    for rel, digest in before_hashes.items():
        path = root / rel
        if not path.is_file():
            drift.append(f"{rel}: file removed")
            continue
        if _file_hash(path) != digest:
            drift.append(f"{rel}: content changed during audit")
    return (not drift, drift)


def commit(root: Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=root,
        text=True, capture_output=True, check=False,
    )
    return proc.stdout.strip() or "unknown"


def snapshot_generated(root: Path, registry: dict) -> tuple[dict[Path, bytes], set[Path]]:
    patterns = ["site-assets-manifest.txt", "tests/ccr-differential/*.json"]
    for entry in registry.get("source_policy", {}).get("generated", []):
        reason = entry.get("reason", "")
        if "Regression output" in reason or "golden" in reason.lower():
            patterns.append(entry["pattern"])
    matched: set[Path] = set()
    for pattern in patterns:
        matched.update(path for path in root.glob(pattern) if path.is_file())
    return ({path: path.read_bytes() for path in matched}, matched)


def restore_generated(root: Path, registry: dict, snapshot: dict[Path, bytes], original: set[Path]) -> None:
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
