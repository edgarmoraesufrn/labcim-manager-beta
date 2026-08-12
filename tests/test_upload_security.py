from __future__ import annotations

from io import BytesIO
from pathlib import Path
import tempfile
import unittest
import zipfile

from openpyxl import Workbook

from labcim_manager.storage import LocalStorageBackend, R2Config, R2StorageBackend
from labcim_manager.upload_security import (
    UploadValidationError,
    safe_display_filename,
    unique_temporary_upload_path,
    upload_max_bytes,
    validate_attachment_storage_key,
    validate_upload,
)
from labcim_manager.config import ConfigurationError


def xlsx_bytes() -> bytes:
    workbook = Workbook()
    workbook.active["A1"] = "LabCim"
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


VALID_CASES = (
    ("manual.pdf", b"%PDF-1.7\nLabCim\n%%EOF", "application/pdf", "equipment_document"),
    ("foto.png", b"\x89PNG\r\n\x1a\nLabCim", "image/png", "maintenance_evidence"),
    ("foto.jpeg", b"\xff\xd8\xff\xe0LabCim\xff\xd9", "image/jpeg", "certificate"),
    ("evidencia.mp4", b"\x00\x00\x00\x18ftypisomLabCim", "video/mp4", "maintenance_evidence"),
)


class UploadSecurityTests(unittest.TestCase):
    def test_permitted_valid_files_are_accepted(self) -> None:
        for filename, content, mime, policy in VALID_CASES:
            with self.subTest(filename=filename):
                validated = validate_upload(
                    filename=filename,
                    content=content,
                    declared_mime=mime,
                    policy_name=policy,
                )
                self.assertEqual(validated.safe_display_filename, filename)
                self.assertEqual(validated.mime_type, mime)

        workbook = validate_upload(
            filename="LabCim_Base.xlsx",
            content=xlsx_bytes(),
            declared_mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            policy_name="base_workbook",
        )
        self.assertEqual(workbook.mime_type, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    def test_forbidden_mismatch_empty_and_oversize_are_rejected(self) -> None:
        invalid_cases = (
            dict(filename="payload.exe", content=b"MZ", declared_mime="application/octet-stream"),
            dict(filename="payload.exe.pdf", content=b"%PDF-1.7\n", declared_mime="application/pdf"),
            dict(filename="fake.pdf", content=b"MZ executable", declared_mime="application/pdf"),
            dict(filename="fake.pdf", content=b"%PDF-1.7\n", declared_mime="image/png"),
            dict(filename="empty.pdf", content=b"", declared_mime="application/pdf"),
        )
        for case in invalid_cases:
            with self.subTest(filename=case["filename"]), self.assertRaises(UploadValidationError):
                validate_upload(policy_name="equipment_document", **case)
        with self.assertRaises(UploadValidationError):
            validate_upload(
                filename="large.pdf",
                content=b"%PDF-" + b"x" * 20,
                declared_mime="application/pdf",
                policy_name="equipment_document",
                max_bytes=10,
            )
        macro_buffer = BytesIO()
        with zipfile.ZipFile(macro_buffer, "w") as archive:
            archive.writestr("[Content_Types].xml", "types")
            archive.writestr("xl/workbook.xml", "workbook")
            archive.writestr("xl/vbaProject.bin", b"macro")
        with self.assertRaises(UploadValidationError):
            validate_upload(
                filename="macro-disfarçada.xlsx",
                content=macro_buffer.getvalue(),
                declared_mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                policy_name="base_workbook",
            )

    def test_path_like_control_and_unicode_edge_names(self) -> None:
        malicious = (
            "../../secret.pdf",
            "..\\..\\secret.pdf",
            "/path/file.pdf",
            "C:\\file.pdf",
            "CON.pdf",
            "line\nbreak.pdf",
        )
        for filename in malicious:
            with self.subTest(filename=filename), self.assertRaises(UploadValidationError):
                safe_display_filename(filename)
        self.assertEqual(safe_display_filename("Ｍａｎｕａｌ．pdf"), "Manual.pdf")

    def test_duplicate_filenames_never_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            backend = LocalStorageBackend(Path(directory))
            first = backend.save_file(
                entity_type="equipment",
                entity_id=1,
                original_filename="manual.pdf",
                content=b"first",
                mime_type="application/pdf",
            )
            second = backend.save_file(
                entity_type="equipment",
                entity_id=1,
                original_filename="manual.pdf",
                content=b"second",
                mime_type="application/pdf",
            )
            self.assertNotEqual(first.storage_key, second.storage_key)
            self.assertEqual(backend.get_file_bytes(first.storage_key), b"first")
            self.assertEqual(backend.get_file_bytes(second.storage_key), b"second")

    def test_local_download_and_storage_key_cannot_escape_attachment_namespace(self) -> None:
        invalid_keys = (
            "../secret",
            "attachments/../../secret",
            "/attachments/equipment/1/file.pdf",
            "other/equipment/1/file.pdf",
            "attachments\\equipment\\1\\file.pdf",
        )
        with tempfile.TemporaryDirectory() as directory:
            backend = LocalStorageBackend(Path(directory))
            for key in invalid_keys:
                with self.subTest(key=key), self.assertRaises(FileNotFoundError):
                    backend.get_file_bytes(key)
        for key in invalid_keys:
            with self.subTest(key=key), self.assertRaises(UploadValidationError):
                validate_attachment_storage_key(key)

    def test_r2_download_refuses_out_of_namespace_key_before_client_call(self) -> None:
        class RecordingClient:
            def __init__(self) -> None:
                self.calls = 0

            def get_object(self, **_kwargs):
                self.calls += 1
                return {"Body": BytesIO(b"unexpected")}

            def generate_presigned_url(self, *_args, **_kwargs):
                self.calls += 1
                return "https://example.invalid/unexpected"

        backend = object.__new__(R2StorageBackend)
        backend.config = R2Config("https://r2.invalid", "key", "secret", "bucket")
        backend.client = RecordingClient()
        with self.assertRaises(UploadValidationError):
            backend.get_file_bytes("other/private-object")
        with self.assertRaises(UploadValidationError):
            backend.generate_download_url("attachments/../private-object")
        self.assertEqual(backend.client.calls, 0)

    def test_admin_import_paths_are_unique_and_beneath_work_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            first = unique_temporary_upload_path(root, "base.xlsx")
            second = unique_temporary_upload_path(root, "base.xlsx")
            self.assertNotEqual(first, second)
            self.assertIn(root, first.parents)
            self.assertIn(root, second.parents)
            self.assertEqual(first.name, "base.xlsx")

    def test_upload_limit_configuration_is_bounded(self) -> None:
        self.assertEqual(upload_max_bytes({}), 25 * 1024 * 1024)
        for value in ("not-a-number", "100", str(60 * 1024 * 1024)):
            with self.subTest(value=value), self.assertRaises(ConfigurationError):
                upload_max_bytes({"LABCIM_UPLOAD_MAX_BYTES": value})


if __name__ == "__main__":
    unittest.main()
