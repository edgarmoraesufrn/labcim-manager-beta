from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from labcim_manager.config import (
    ConfigurationError,
    PROJECT_ROOT,
    build_public_static_url,
    build_public_url,
    get_app_environment,
    get_local_work_root,
    get_public_app_url,
    normalize_public_app_url,
    normalize_storage_backend,
    project_path,
    resolve_local_storage_root,
)


class ConfigurationTests(unittest.TestCase):
    def test_environment_validation_rejects_unknown_value(self) -> None:
        with self.assertRaises(ConfigurationError):
            get_app_environment({"APP_ENV": "live"})

    def test_storage_defaults_to_local_only_for_development_and_test(self) -> None:
        self.assertEqual(normalize_storage_backend(None, environment="development"), "local")
        self.assertEqual(normalize_storage_backend(None, environment="test"), "local")
        with self.assertRaises(ConfigurationError):
            normalize_storage_backend(None, environment="production")

    def test_production_local_root_must_be_absolute(self) -> None:
        with self.assertRaises(ConfigurationError):
            resolve_local_storage_root("data/uploads", environment="production")

    def test_production_work_root_must_be_explicit_and_absolute(self) -> None:
        with self.assertRaises(ConfigurationError):
            get_local_work_root({"APP_ENV": "production"})
        with self.assertRaises(ConfigurationError):
            get_local_work_root({"APP_ENV": "production", "LOCAL_WORK_ROOT": "data/work"})
        root = get_local_work_root(
            {"APP_ENV": "production", "LOCAL_WORK_ROOT": str(PROJECT_ROOT / "work")}
        )
        self.assertTrue(root.is_absolute())

    def test_development_relative_storage_root_is_project_rooted(self) -> None:
        root = resolve_local_storage_root("var/uploads", environment="development")
        self.assertEqual(root, (PROJECT_ROOT / "var" / "uploads").resolve())

    def test_project_paths_do_not_depend_on_cwd(self) -> None:
        expected = project_path("assets", "logo_labcim.png")
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                self.assertEqual(project_path("assets", "logo_labcim.png"), expected)
            finally:
                os.chdir(previous)

    def test_public_url_normalization_and_manager_query(self) -> None:
        base_url = normalize_public_app_url(
            "https://labcim.quimica.ufrn.br/manager",
            environment="production",
        )
        self.assertEqual(base_url, "https://labcim.quimica.ufrn.br/manager/")
        self.assertEqual(
            build_public_url(base_url, {"eq": "AUT 01", "view": "reserva"}),
            "https://labcim.quimica.ufrn.br/manager/?eq=AUT+01&view=reserva",
        )
        self.assertEqual(
            build_public_static_url(base_url, "manifest.json"),
            "https://labcim.quimica.ufrn.br/manager/app/static/manifest.json",
        )

    def test_production_url_rejects_local_or_insecure_destinations(self) -> None:
        for value in (
            "http://labcim.example/manager/",
            "https://localhost:8501/manager/",
            "https://labcim.example/",
        ):
            with self.subTest(value=value), self.assertRaises(ConfigurationError):
                normalize_public_app_url(value, environment="production")

    def test_required_public_url_does_not_invent_localhost(self) -> None:
        with self.assertRaises(ConfigurationError):
            get_public_app_url({"APP_ENV": "production"}, required=True)

    def test_environment_public_url_is_normalized(self) -> None:
        with patch.dict(
            os.environ,
            {"APP_ENV": "staging", "APP_BASE_URL": "https://staging.example/manager"},
            clear=True,
        ):
            self.assertEqual(get_public_app_url(required=True), "https://staging.example/manager/")


if __name__ == "__main__":
    unittest.main()
