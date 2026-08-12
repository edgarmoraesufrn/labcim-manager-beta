from __future__ import annotations

import os
import gc
from pathlib import Path
import tempfile
import unittest

from streamlit.testing.v1 import AppTest

from labcim_manager.db import connect
from labcim_manager.schema import initialize_schema


REPO_ROOT = Path(__file__).resolve().parents[1]


class StreamlitSmokeTests(unittest.TestCase):
    def test_login_page_starts_against_current_ephemeral_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            database = root / "smoke.db"
            conn = connect(database)
            try:
                initialize_schema(conn)
            finally:
                conn.close()

            source = f"""
import os
from pathlib import Path
import runpy
from labcim_manager import config

os.environ.update({{
    "APP_ENV": "test",
    "STORAGE_BACKEND": "local",
    "LOCAL_STORAGE_ROOT": {str(root / 'uploads')!r},
    "LOCAL_WORK_ROOT": {str(root / 'work')!r},
    "LABCIM_OTP_HASH_SECRET": "test-only-app-smoke-secret-32chars",
}})
original_project_path = config.project_path
def ephemeral_project_path(*parts):
    if parts == ("data", "labcim_manager.db"):
        return Path({str(database)!r})
    return original_project_path(*parts)
config.project_path = ephemeral_project_path
runpy.run_path({str(REPO_ROOT / 'app.py')!r}, run_name="__main__")
"""
            app_test = AppTest.from_string(source, default_timeout=20)
            app_test.run()

            self.assertFalse(app_test.exception)
            self.assertTrue(
                any("Acesso ao sistema" in element.value for element in app_test.subheader)
            )
            app_test = None
            gc.collect()


if __name__ == "__main__":
    unittest.main()
