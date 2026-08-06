"""Assemble production and development builds into one Pages artifact."""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit


ASSET_RE = re.compile(r'''(?:src|href)=["']([^"']+)["']''', re.IGNORECASE)
CACHE_DECLARATION = "const CACHE_VERSION = 'lsp-dplanner-plus-v' + APP_VERSION + '-' + APP_BUILD_ID;"
APP_BASE_DECLARATION = "const APP_BASE = getAppBasePath();"


def _local_asset_refs(index_path: Path) -> list[str]:
    refs: set[str] = set()
    for value in ASSET_RE.findall(index_path.read_text(encoding="utf-8")):
        parsed = urlsplit(value)
        if parsed.scheme or parsed.netloc or value.startswith(("#", "data:")):
            continue
        path = parsed.path.lstrip("./")
        if path:
            refs.add(path)
    return sorted(refs)


def _sync_referenced_assets(source: Path, built: Path) -> None:
    index_path = built / "index.html"
    if not index_path.is_file():
        raise SystemExit(f"Pages build has no index.html: {built}")

    for rel in _local_asset_refs(index_path):
        target = built / rel
        if target.exists():
            continue
        origin = source / rel
        if not origin.is_file():
            raise SystemExit(f"Referenced site asset is missing: {rel}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, target)


def _patch_preview(preview: Path, commit: str) -> None:
    sw_path = preview / "sw.js"
    sw = sw_path.read_text(encoding="utf-8")
    if CACHE_DECLARATION not in sw or APP_BASE_DECLARATION not in sw:
        raise SystemExit("Service-worker preview patch anchors are missing")
    sw = sw.replace(
        CACHE_DECLARATION,
        "const CACHE_VERSION = 'lsp-dplanner-plus-dev-v' + APP_VERSION + '-' + APP_BUILD_ID;",
        1,
    ).replace(
        APP_BASE_DECLARATION,
        "const APP_BASE = new URL('./', self.location.href).pathname;",
        1,
    )
    sw_path.write_text(sw, encoding="utf-8", newline="\n")

    index_path = preview / "index.html"
    index = index_path.read_text(encoding="utf-8")
    if "<head>" not in index or "</body>" not in index:
        raise SystemExit("Preview index patch anchors are missing")
    index = index.replace(
        "<head>",
        '<head>\n<meta content="noindex,nofollow,noarchive" name="robots"/>',
        1,
    ).replace(
        "</body>",
        '<div aria-label="Development preview" style="position:fixed;right:10px;bottom:10px;z-index:99999;'
        'padding:5px 8px;border:1px solid #f59e0b;background:#111827;color:#fbbf24;'
        'font:600 11px/1.2 system-ui,sans-serif;border-radius:4px;pointer-events:none">DEV PREVIEW</div>\n'
        "</body>",
        1,
    )
    index_path.write_text(index, encoding="utf-8", newline="\n")

    (preview / "preview-version.json").write_text(
        json.dumps({"branch": "dev", "commit": commit}, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _validate_site(site: Path) -> None:
    missing = [rel for rel in _local_asset_refs(site / "index.html") if not (site / rel).exists()]
    if missing:
        raise SystemExit("Missing deployed assets: " + ", ".join(missing))


def assemble(production: Path, development: Path, output: Path, commit: str) -> Path:
    production_build = production / "_pages"
    development_build = development / "_pages"
    _sync_referenced_assets(production, production_build)
    _sync_referenced_assets(development, development_build)

    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(production_build, output)
    preview = output / "dev"
    shutil.copytree(development_build, preview)
    _patch_preview(preview, commit)
    _validate_site(output)
    _validate_site(preview)
    print(f"Assembled Pages site: production=/, preview=/dev/ -> {output}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--production", required=True, type=Path)
    parser.add_argument("--development", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    assemble(
        args.production.resolve(),
        args.development.resolve(),
        args.output.resolve(),
        args.commit,
    )


if __name__ == "__main__":
    main()
