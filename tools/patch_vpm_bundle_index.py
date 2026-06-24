"""Remove inline VPMEngine from index.html; load vpm-engine-bundle.js from head."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
index_path = ROOT / "index.html"
html = index_path.read_text(encoding="utf-8")

start = html.find("\nconst VPMEngine = (() => {")
end = html.find("// ── END VPM ENGINE ──", start)
if start < 0 or end < 0:
    raise SystemExit("VPMEngine block markers not found in index.html")
end = html.find("\n", end) + 1

replacement = "\n// VPMEngine — Tier 3 bundle (vpm-engine-bundle.js)\n"
html = html[:start] + replacement + html[end:]

head_needle = '<script src="zhl-engine-bundle.js"></script>\n'
head_insert = '<script src="vpm-engine-bundle.js"></script>\n'
if head_needle not in html:
    raise SystemExit("zhl-engine-bundle script tag not found")
if "vpm-engine-bundle.js" not in html:
    html = html.replace(head_needle, head_needle + head_insert, 1)

index_path.write_text(html, encoding="utf-8")
print("Patched index.html — inline VPMEngine removed, script tag added")
