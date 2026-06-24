"""Verify deployed site trees include every runtime asset the app needs.

Compares a built _pages/ tree (or explicit manifest) against a target directory
and optionally probes live URLs.

Usage:
  python tools/build_pages_site.py
  python tools/verify_site_assets.py _pages
  python tools/verify_site_assets.py --live https://threecats-lsp.com/d-planner-plus/
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel_files(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        out[rel] = sha256_file(p)
    return out


def check_tree(reference: Path, target: Path) -> list[str]:
    ref = rel_files(reference)
    tgt = rel_files(target)
    errors: list[str] = []
    skip = {"about.html", "LSP_D-planner-plus.apk", ".nojekyll"}
    for rel, ref_hash in sorted(ref.items()):
        if rel in skip:
            continue
        if rel not in tgt:
            errors.append(f"missing: {rel}")
        elif tgt[rel] != ref_hash:
            errors.append(f"hash mismatch: {rel}")
    return errors


def check_live(base_url: str, reference: Path) -> list[str]:
    base = base_url.rstrip("/") + "/"
    errors: list[str] = []
    skip = {"about.html", "LSP_D-planner-plus.apk", ".nojekyll"}
    for rel in sorted(rel_files(reference)):
        if rel in skip:
            continue
        url = base + rel
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "LSP-site-verify/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status != 200:
                    errors.append(f"HTTP {resp.status}: {rel}")
        except urllib.error.HTTPError as exc:
            errors.append(f"HTTP {exc.code}: {rel}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"fetch failed {rel}: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify site asset parity")
    parser.add_argument("target", nargs="?", help="Local directory to compare against _pages/")
    parser.add_argument("--reference", default=str(ROOT / "_pages"), help="Reference tree (default: _pages/)")
    parser.add_argument("--live", help="Also HEAD-check each asset under this base URL")
    args = parser.parse_args()

    reference = Path(args.reference)
    if not reference.is_dir():
        print(f"Reference tree missing: {reference} — run tools/build_pages_site.py first", file=sys.stderr)
        return 1

    errors: list[str] = []
    if args.target:
        target = Path(args.target)
        if not target.is_dir():
            print(f"Target missing: {target}", file=sys.stderr)
            return 1
        errors.extend(check_tree(reference, target))

    if args.live:
        errors.extend(check_live(args.live, reference))

    if errors:
        print(f"FAILED — {len(errors)} issue(s):")
        for err in errors:
            print(f"  {err}")
        return 1

    parts = []
    if args.target:
        parts.append(f"local tree {args.target}")
    if args.live:
        parts.append(f"live {args.live}")
    print(f"OK — all runtime assets present ({', '.join(parts)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
