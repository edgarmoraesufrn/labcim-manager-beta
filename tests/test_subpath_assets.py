from __future__ import annotations

import json
from pathlib import Path
import unittest

from labcim_manager.config import build_public_static_url, build_public_url


REPO_ROOT = Path(__file__).resolve().parents[1]


class SubpathAssetTests(unittest.TestCase):
    def test_manifest_is_scoped_to_manager(self) -> None:
        manifest = json.loads((REPO_ROOT / "static" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["start_url"], "/manager/")
        self.assertEqual(manifest["scope"], "/manager/")
        for icon in manifest["icons"]:
            self.assertTrue(icon["src"].startswith("/manager/app/static/"))

    def test_qr_urls_keep_manager_path_and_encode_values(self) -> None:
        url = build_public_url(
            "https://labcim.quimica.ufrn.br/manager/",
            {"eq": "EQ 01/A", "view": "reserva"},
        )
        self.assertEqual(
            url,
            "https://labcim.quimica.ufrn.br/manager/?eq=EQ+01%2FA&view=reserva",
        )

    def test_static_url_keeps_manager_path(self) -> None:
        self.assertEqual(
            build_public_static_url(
                "https://labcim.quimica.ufrn.br/manager/",
                "manifest.json",
            ),
            "https://labcim.quimica.ufrn.br/manager/app/static/manifest.json",
        )


if __name__ == "__main__":
    unittest.main()
