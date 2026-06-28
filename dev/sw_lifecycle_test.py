#!/usr/bin/env python3
"""Behavioral check: SW precache lifecycle guards (no blind SKIP_WAITING bypass)."""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_DEV = Path(__file__).resolve().parent
if str(_DEV) not in sys.path:
    sys.path.insert(0, str(_DEV))

from test_http import serve_root  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    from playwright.sync_api import sync_playwright

    with serve_root(ROOT) as base_url:
        base = base_url.rstrip("/") + "/"
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{base}index.html?regression=1", wait_until="domcontentloaded", timeout=60000)
            result = page.evaluate(
                """
                async (base) => {
                  const swText = await (await fetch(base + 'sw.js')).text();
                  const idxText = await (await fetch(base + 'index.html')).text();
                  const guards = swText.includes('verifyShellPrecache')
                    && swText.includes('Required shell precache incomplete')
                    && swText.includes('SKIP_WAITING ignored')
                    && swText.includes('activate blocked')
                    && swText.includes('caches.delete(CACHE_VERSION)');
                  const swBlock = idxText.split('PWA: service worker registration')[1] || '';
                  const noBlindSkip = !swBlock.includes('SKIP_WAITING');
                  const noEagerMigration = !swBlock.includes('getRegistrations()')
                    && !swBlock.includes('caches.delete(k)');
                  const versionOnActivate = swBlock.includes('localStorage.setItem(SW_VERSION_KEY, APP_VERSION)');
                  return { ok: guards && noBlindSkip && noEagerMigration && versionOnActivate, guards, noBlindSkip, noEagerMigration, versionOnActivate };
                }
                """,
                base,
            )
            browser.close()

    print(result)
    if result.get("ok"):
        print("SW lifecycle test PASS")
        return 0
    print("SW lifecycle test FAIL:", result)
    return 1


if __name__ == "__main__":
    sys.exit(main())
