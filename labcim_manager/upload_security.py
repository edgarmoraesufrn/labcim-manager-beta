from __future__ import annotations

from dataclasses import dataclass
import mimetypes
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import unicodedata
from typing import Mapping
from uuid import uuid4
import zipfile
from io import BytesIO

from labcim_manager.config import ConfigurationError


class UploadValidationError(ValueError):
    """Raised when an uploaded file violates the repository security policy."""


@dataclass(frozen=True)
class UploadPolicy:
    name: str
    extensions: frozenset[str]
    mime_types: frozenset[str]
    allow_video: bool = False


@dataclass(frozen=True)
class ValidatedUpload:
    original_filename: str
    safe_display_filename: str
    content: bytes
    mime_type: str
    policy_name: str


DOCUMENT_EXTENSIONS = frozenset({"pdf", "png", "jpg", "jpeg", "docx", "xlsx"})
IMAGE_PDF_EXTENSIONS = frozenset({"pdf", "png", "jpg", "jpeg"})
EVIDENCE_EXTENSIONS = IMAGE_PDF_EXTENSIONS | {"mp4", "mov"}

MIME_BY_EXTENSION = {
    "pdf": frozenset({"application/pdf"}),
    "png": frozenset({"image/png"}),
    "jpg": frozenset({"image/jpeg", "image/jpg"}),
    "jpeg": frozenset({"image/jpeg", "image/jpg"}),
    "docx": frozenset({
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
    }),
    "xlsx": frozenset({
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
    }),
    "mp4": frozenset({"video/mp4"}),
    "mov": frozenset({"video/quicktime"}),
}

DETECTED_MIME_BY_EXTENSION = {
    extension: frozenset(
        mime for mime in mime_types if mime != "application/zip" and mime != "image/jpg"
    )
    for extension, mime_types in MIME_BY_EXTENSION.items()
}


def _mimes(extensions: frozenset[str]) -> frozenset[str]:
    return frozenset(mime for ext in extensions for mime in MIME_BY_EXTENSION[ext])


UPLOAD_POLICIES: dict[str, UploadPolicy] = {
    "equipment_document": UploadPolicy(
        "equipment_document", DOCUMENT_EXTENSIONS, _mimes(DOCUMENT_EXTENSIONS)
    ),
    "certificate": UploadPolicy(
        "certificate", IMAGE_PDF_EXTENSIONS | {"xlsx"}, _mimes(IMAGE_PDF_EXTENSIONS | {"xlsx"})
    ),
    "safety_document": UploadPolicy(
        "safety_document", IMAGE_PDF_EXTENSIONS, _mimes(IMAGE_PDF_EXTENSIONS)
    ),
    "technical_document": UploadPolicy(
        "technical_document", IMAGE_PDF_EXTENSIONS | {"xlsx", "docx"}, _mimes(IMAGE_PDF_EXTENSIONS | {"xlsx", "docx"})
    ),
    "movement_document": UploadPolicy(
        "movement_document", IMAGE_PDF_EXTENSIONS | {"xlsx"}, _mimes(IMAGE_PDF_EXTENSIONS | {"xlsx"})
    ),
    "maintenance_evidence": UploadPolicy(
        "maintenance_evidence", EVIDENCE_EXTENSIONS, _mimes(EVIDENCE_EXTENSIONS), allow_video=True
    ),
    "maintenance_document": UploadPolicy(
        "maintenance_document", IMAGE_PDF_EXTENSIONS, _mimes(IMAGE_PDF_EXTENSIONS)
    ),
    "base_workbook": UploadPolicy(
        "base_workbook", frozenset({"xlsx"}), _mimes(frozenset({"xlsx"}))
    ),
}

DANGEROUS_EXTENSION_SEGMENTS = frozenset(
    {
        "bat", "cmd", "com", "dll", "exe", "hta", "html", "htm", "jar",
        "js", "jse", "lnk", "msi", "php", "ps1", "py", "scr", "sh", "svg",
        "vbs", "wsf", "zip", "rar", "7z",
    }
)
WINDOWS_RESERVED_NAMES = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{number}" for number in range(1, 10)}
    | {f"lpt{number}" for number in range(1, 10)}
)


def upload_max_bytes(environ: Mapping[str, str] | None = None) -> int:
    values = os.environ if environ is None else environ
    raw = str(values.get("LABCIM_UPLOAD_MAX_BYTES") or 25 * 1024 * 1024).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError("LABCIM_UPLOAD_MAX_BYTES deve ser um número inteiro.") from exc
    if not 1_048_576 <= value <= 52_428_800:
        raise ConfigurationError(
            "LABCIM_UPLOAD_MAX_BYTES deve estar entre 1048576 e 52428800 bytes."
        )
    return value


def safe_display_filename(filename: object) -> str:
    raw = unicodedata.normalize("NFKC", str(filename or "")).strip()
    if not raw or any(ord(char) < 32 or ord(char) == 127 for char in raw):
        raise UploadValidationError("Nome de arquivo inválido.")
    if (
        PurePosixPath(raw).is_absolute()
        or PureWindowsPath(raw).is_absolute()
        or "/" in raw
        or "\\" in raw
        or ".." in PurePosixPath(raw).parts
        or ".." in PureWindowsPath(raw).parts
        or re.match(r"^[A-Za-z]:", raw)
    ):
        raise UploadValidationError("O nome do arquivo não pode conter caminho.")
    cleaned = re.sub(r"[^A-Za-z0-9À-ÖØ-öø-ÿ_. -]+", "_", raw).strip(" .")
    if not cleaned or len(cleaned) > 180:
        raise UploadValidationError("Nome de arquivo inválido ou muito longo.")
    if cleaned.split(".", 1)[0].strip().lower() in WINDOWS_RESERVED_NAMES:
        raise UploadValidationError("Nome de arquivo reservado pelo sistema operacional.")
    return cleaned


def _extension(filename: str) -> str:
    segments = [segment.lower() for segment in filename.split(".")[1:]]
    if any(segment in DANGEROUS_EXTENSION_SEGMENTS for segment in segments):
        raise UploadValidationError("O nome contém uma extensão perigosa ou não permitida.")
    suffix = Path(filename).suffix.lower().removeprefix(".")
    if not suffix:
        raise UploadValidationError("O arquivo precisa ter uma extensão permitida.")
    return suffix


def _detected_type(content: bytes, extension: str) -> str | None:
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(content) >= 12 and content[4:8] == b"ftyp":
        brand = content[8:12]
        return "video/quicktime" if brand == b"qt  " else "video/mp4"
    if content.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(BytesIO(content)) as archive:
                names = set(archive.namelist())
            if "[Content_Types].xml" not in names:
                return "application/zip"
            if any(PurePosixPath(name).name.lower() == "vbaproject.bin" for name in names):
                return "application/zip"
            if any(name.startswith("xl/") for name in names):
                return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if any(name.startswith("word/") for name in names):
                return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        except (OSError, zipfile.BadZipFile):
            return "application/zip"
    return None


def validate_upload(
    *,
    filename: object,
    content: bytes,
    declared_mime: object,
    policy_name: str,
    max_bytes: int | None = None,
) -> ValidatedUpload:
    try:
        policy = UPLOAD_POLICIES[policy_name]
    except KeyError as exc:
        raise UploadValidationError("Política de upload desconhecida.") from exc
    safe_name = safe_display_filename(filename)
    extension = _extension(safe_name)
    if extension not in policy.extensions:
        raise UploadValidationError("Tipo de arquivo não permitido para este campo.")
    limit = max_bytes if max_bytes is not None else upload_max_bytes()
    if not content:
        raise UploadValidationError("O arquivo está vazio.")
    if len(content) > limit:
        raise UploadValidationError("O arquivo excede o limite de tamanho permitido.")

    declared = str(declared_mime or "").strip().lower()
    plausible_declared = MIME_BY_EXTENSION[extension]
    if declared and declared not in plausible_declared and declared != "application/octet-stream":
        raise UploadValidationError("O tipo declarado não corresponde à extensão do arquivo.")
    detected = _detected_type(content, extension)
    if detected not in DETECTED_MIME_BY_EXTENSION[extension]:
        raise UploadValidationError("O conteúdo do arquivo não corresponde ao tipo permitido.")
    return ValidatedUpload(
        original_filename=str(filename),
        safe_display_filename=safe_name,
        content=content,
        mime_type=detected,
        policy_name=policy_name,
    )


def policy_extensions(policy_name: str) -> list[str]:
    return sorted(UPLOAD_POLICIES[policy_name].extensions)


def unique_temporary_upload_path(work_root: Path, filename: object) -> Path:
    safe_name = safe_display_filename(filename)
    upload_dir = (work_root / "imports" / uuid4().hex).resolve()
    root = work_root.resolve()
    if root not in upload_dir.parents:
        raise UploadValidationError("Diretório temporário fora da raiz de trabalho.")
    return upload_dir / safe_name


def validate_attachment_storage_key(storage_key: object) -> str:
    key = str(storage_key or "").strip()
    if not key or "\\" in key or key.startswith("/"):
        raise UploadValidationError("Chave de anexo inválida.")
    path = PurePosixPath(key)
    if path.parts[0] != "attachments" or any(part in {"", ".", ".."} for part in path.parts):
        raise UploadValidationError("Chave de anexo fora do namespace permitido.")
    return key
