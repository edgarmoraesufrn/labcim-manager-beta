from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = REPO_ROOT / "scripts" / "production_preflight.py"


class PreflightTests(unittest.TestCase):
    def run_preflight(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        for key in tuple(environment):
            if key.startswith(("APP_", "LABCIM_", "R2_", "STREAMLIT_")) or key in {
                "DATABASE_URL",
                "LOCAL_STORAGE_ROOT",
                "STORAGE_BACKEND",
                "TZ",
            }:
                environment.pop(key, None)
        return subprocess.run(
            [sys.executable, str(PREFLIGHT), *arguments],
            cwd=REPO_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_preflight_distinguishes_code_environment_and_deployment(self) -> None:
        result = self.run_preflight()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("[CODE BLOCKER", result.stdout)
        self.assertIn("[ENVIRONMENT REQUIRED", result.stdout)
        self.assertIn("[DEPLOYMENT PENDING", result.stdout)
        self.assertIn("[PASS", result.stdout)

    def test_complete_dummy_environment_is_not_disclosed(self) -> None:
        sentinel = "offline-secret-sentinel-9f72"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            secret_value = sentinel + "-long-enough-for-hmac"
            env_file = root / "manager.env"
            env_file.write_text(
                "\n".join(
                    (
                        "APP_ENV=production",
                        "APP_BASE_URL=https://labcim.test/manager/",
                        f"DATABASE_URL=postgresql://labcim:{sentinel}@127.0.0.1:5432/labcim",
                        "STORAGE_BACKEND=local",
                        f"LOCAL_STORAGE_ROOT={root / 'uploads'}",
                        f"LOCAL_WORK_ROOT={root / 'work'}",
                        "APP_LOG_LEVEL=INFO",
                        f"STREAMLIT_SERVER_COOKIE_SECRET={secret_value}",
                        "LABCIM_SMTP_HOST=smtp.test",
                        "LABCIM_SMTP_PORT=587",
                        "LABCIM_SMTP_USER=labcim@test.invalid",
                        f"LABCIM_SMTP_PASSWORD={sentinel}",
                        "LABCIM_SMTP_FROM=labcim@test.invalid",
                        "LABCIM_SMTP_TLS=true",
                        "LABCIM_OTP_TTL_SECONDS=600",
                        "LABCIM_OTP_MAX_VERIFY_ATTEMPTS=5",
                        "LABCIM_OTP_REQUEST_WINDOW_SECONDS=900",
                        "LABCIM_OTP_MAX_REQUESTS_PER_WINDOW=3",
                        "LABCIM_OTP_MAX_REQUESTS_PER_ORIGIN=20",
                        "LABCIM_OTP_GLOBAL_MAX_REQUESTS=100",
                        "LABCIM_UPLOAD_MAX_BYTES=26214400",
                        "TZ=America/Fortaleza",
                    )
                ),
                encoding="utf-8",
            )
            result = self.run_preflight("--env-file", str(env_file))

        self.assertEqual(result.returncode, 1)
        self.assertNotIn(sentinel, result.stdout)
        self.assertNotIn("[ENVIRONMENT REQUIRED", result.stdout)
        self.assertIn("0 code blocker(s)", result.stdout)
        self.assertIn("5 deployment pending", result.stdout)


if __name__ == "__main__":
    unittest.main()
