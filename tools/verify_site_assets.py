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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE_TIMEOUT_S = 10
LIVE_WORKERS = 8


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel_paths(root: Path) -> list[str]:
    return sorted(
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file()
    )


def rel_files(root: Path) -> dict[str, str]:
    return {rel: sha256_file(root / rel) for rel in rel_paths(root)}


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


def probe_url(url: str, rel: str, timeout: float) -> str | None:
    """Return an error message, or None if the asset is reachable."""
    headers = {"User-Agent": "LSP-site-verify/1.0"}
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status != 200:
                    return f"HTTP {resp.status}: {rel}"
                return None
        except urllib.error.HTTPError as exc:
            if exc.code == 405 and method == "HEAD":
                continue
            return f"HTTP {exc.code}: {rel}"
        except Exception as exc:  # noqa: BLE001
            return f"fetch failed {rel}: {exc}"
    return f"fetch failed {rel}: HEAD and GET both failed"


def check_live(base_url: str, reference: Path) -> list[str]:
    base = base_url.rstrip("/") + "/"
    skip = {"about.html", "LSP_D-planner-plus.apk", ".nojekyll"}
    rels = [rel for rel in rel_paths(reference) if rel not in skip]
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=LIVE_WORKERS) as pool:
        futures = {
            pool.submit(probe_url, base + rel, rel, LIVE_TIMEOUT_S): rel
            for rel in rels
        }
        for fut in as_completed(futures):
            err = fut.result()
            if err:
                errors.append(err)
    return sorted(errors)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify site asset parity")
    parser.add_argument("target", nargs="?", help="Local directory to compare against _pages/")
    parser.add_argument("--reference", default=str(ROOT / "_pages"), help="Reference tree (default: _pages/)")
    parser.add_argument("--live", help="Also check each asset under this base URL (HEAD, GET on 405)")
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
