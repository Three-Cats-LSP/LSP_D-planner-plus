from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.assemble_pages_preview import assemble


class AssemblePagesPreviewTests(unittest.TestCase):
    def _source(self, root: Path, name: str) -> Path:
        source = root / name
        built = source / "_pages"
        built.mkdir(parents=True)
        (source / "app.js").write_text("source", encoding="utf-8")
        (built / "index.html").write_text(
            '<html><head></head><body><script src="app.js"></script></body></html>',
            encoding="utf-8",
        )
        (built / "sw.js").write_text(
            "const CACHE_VERSION = 'lsp-dplanner-plus-v' + APP_VERSION + '-' + APP_BUILD_ID;\n"
            "const APP_BASE = getAppBasePath();\n",
            encoding="utf-8",
        )
        return source

    def test_assemble_keeps_production_and_isolates_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            production = self._source(root, "production")
            development = self._source(root, "development")
            output = assemble(production, development, root / "site", "abc123")

            self.assertEqual((output / "app.js").read_text(encoding="utf-8"), "source")
            self.assertTrue((output / "dev" / "app.js").is_file())
            preview_sw = (output / "dev" / "sw.js").read_text(encoding="utf-8")
            self.assertIn("lsp-dplanner-plus-dev-v", preview_sw)
            self.assertIn("new URL('./', self.location.href).pathname", preview_sw)
            preview_index = (output / "dev" / "index.html").read_text(encoding="utf-8")
            self.assertIn("noindex,nofollow,noarchive", preview_index)
            self.assertIn("DEV PREVIEW", preview_index)
            metadata = json.loads((output / "dev" / "preview-version.json").read_text())
            self.assertEqual(metadata, {"branch": "dev", "commit": "abc123"})


if __name__ == "__main__":
    unittest.main()
