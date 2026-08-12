from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from labcim_manager.storage import (
    LocalStorageBackend,
    StorageConfigurationError,
    get_active_storage_backend,
)


class StorageSelectionTests(unittest.TestCase):
    def local_environment(self, root: Path) -> dict[str, str]:
        return {
            "APP_ENV": "test",
            "STORAGE_BACKEND": "local",
            "LOCAL_STORAGE_ROOT": str(root),
        }

    def test_sqlite_and_local_storage_are_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            self.local_environment(Path(directory)),
            clear=True,
        ):
            backend = get_active_storage_backend(database_url=None)
            self.assertIsInstance(backend, LocalStorageBackend)

    def test_postgresql_and_local_storage_are_independent(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            self.local_environment(Path(directory)),
            clear=True,
        ):
            backend = get_active_storage_backend(database_url="postgresql://unused.example/labcim")
            self.assertIsInstance(backend, LocalStorageBackend)

    def test_r2_selection_requires_its_own_credentials(self) -> None:
        with patch.dict(
            os.environ,
            {"APP_ENV": "test", "STORAGE_BACKEND": "r2"},
            clear=True,
        ):
            with self.assertRaises(StorageConfigurationError) as context:
                get_active_storage_backend(database_url="postgresql://unused.example/labcim")
        self.assertIn("R2_ENDPOINT_URL", str(context.exception))
        self.assertNotIn("DATABASE_URL", str(context.exception))

    def test_local_storage_rejects_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            backend = LocalStorageBackend(Path(directory))
            with self.assertRaises(FileNotFoundError):
                backend.resolve_target_path("../outside.txt")

    def test_local_storage_round_trip_uses_portable_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            backend = LocalStorageBackend(Path(directory))
            stored = backend.save_file(
                entity_type="equipment",
                entity_id=42,
                original_filename="manual técnico.pdf",
                content=b"test-content",
                mime_type="application/pdf",
            )
            self.assertEqual(stored.storage_backend, "local")
            self.assertTrue(stored.storage_key.startswith("attachments/equipment/42/"))
            self.assertNotIn(str(directory), stored.storage_key)
            self.assertEqual(backend.get_file_bytes(stored.storage_key), b"test-content")


if __name__ == "__main__":
    unittest.main()
