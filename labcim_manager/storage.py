from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import mimetypes
import os
from pathlib import Path
import re
from uuid import uuid4
from urllib.parse import quote

from labcim_manager.config import (
    ConfigurationError,
    DEFAULT_LOCAL_STORAGE_ROOT,
    get_app_environment,
    normalize_storage_backend,
    resolve_local_storage_root,
)
from labcim_manager.upload_security import (
    UploadValidationError,
    safe_display_filename,
    validate_attachment_storage_key,
)

LOCAL_UPLOAD_ROOT = DEFAULT_LOCAL_STORAGE_ROOT
R2_REQUIRED_KEYS = ("R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET")
DEFAULT_DOWNLOAD_TTL_SECONDS = 300


class StorageConfigurationError(ConfigurationError, RuntimeError):
    """Raised when production storage cannot safely persist uploaded files."""


@dataclass(frozen=True)
class R2Config:
    endpoint_url: str
    access_key_id: str
    secret_access_key: str
    bucket: str
    account_id: str | None = None


@dataclass(frozen=True)
class StoredFile:
    original_filename: str
    storage_key: str
    storage_backend: str
    mime_type: str | None
    file_size: int
    sha256: str


def _safe_filename(filename: str) -> str:
    return safe_display_filename(filename)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _guess_mime_type(filename: str, fallback: str | None = None) -> str | None:
    return fallback or mimetypes.guess_type(filename)[0] or "application/octet-stream"


def make_storage_key(entity_type: str, entity_id: int, filename: str, digest: str) -> str:
    now = datetime.now(UTC)
    safe_name = _safe_filename(filename)
    safe_entity = re.sub(r"[^A-Za-z0-9_-]+", "_", str(entity_type)).strip("_") or "entity"
    nonce = uuid4().hex
    return f"attachments/{safe_entity}/{int(entity_id)}/{now:%Y}/{now:%m}/{digest}_{nonce}_{safe_name}"


def _read_streamlit_secret(key: str, section: str | None = None) -> str | None:
    try:
        import streamlit as st

        if section and hasattr(st, "secrets") and section in st.secrets and key in st.secrets[section]:
            value = st.secrets[section][key]
        elif hasattr(st, "secrets") and key in st.secrets:
            value = st.secrets[key]
        else:
            return None
    except Exception:
        return None
    value = str(value).strip()
    return value or None


def resolve_config_value(key: str, *, section: str | None = "r2") -> str | None:
    env_value = os.environ.get(key)
    if env_value and env_value.strip():
        return env_value.strip()

    value = _read_streamlit_secret(key, section=section)
    if value:
        return value

    if section:
        short_key = key.removeprefix("R2_").lower()
        value = _read_streamlit_secret(short_key, section=section)
        if value:
            return value
    return None


def get_r2_config() -> R2Config | None:
    values = {key: resolve_config_value(key) for key in R2_REQUIRED_KEYS}
    if all(values.values()):
        return R2Config(
            endpoint_url=str(values["R2_ENDPOINT_URL"]),
            access_key_id=str(values["R2_ACCESS_KEY_ID"]),
            secret_access_key=str(values["R2_SECRET_ACCESS_KEY"]),
            bucket=str(values["R2_BUCKET"]),
            account_id=resolve_config_value("R2_ACCOUNT_ID"),
        )
    return None


def missing_r2_config_keys() -> list[str]:
    return [key for key in R2_REQUIRED_KEYS if not resolve_config_value(key)]


def is_r2_configured() -> bool:
    return get_r2_config() is not None


def selected_storage_backend() -> str:
    environment = get_app_environment()
    value = resolve_config_value("STORAGE_BACKEND", section="storage")
    return normalize_storage_backend(value, environment=environment)


def local_storage_root() -> Path:
    environment = get_app_environment()
    value = resolve_config_value("LOCAL_STORAGE_ROOT", section="storage")
    return resolve_local_storage_root(value, environment=environment)


class LocalStorageBackend:
    name = "local"

    def __init__(self, root: Path | str | None = None):
        self.root = (
            resolve_local_storage_root(root, environment="development")
            if root is not None
            else local_storage_root()
        )

    def save_file(
        self,
        *,
        entity_type: str,
        entity_id: int,
        original_filename: str,
        content: bytes,
        mime_type: str | None = None,
    ) -> StoredFile:
        digest = _sha256(content)
        storage_key = make_storage_key(entity_type, entity_id, original_filename, digest)
        target = self.resolve_target_path(storage_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return StoredFile(
            original_filename=Path(original_filename or "arquivo").name,
            storage_key=storage_key,
            storage_backend=self.name,
            mime_type=_guess_mime_type(original_filename, mime_type),
            file_size=len(content),
            sha256=digest,
        )

    def get_file_bytes(self, storage_key: str) -> bytes:
        return self.resolve_path(storage_key).read_bytes()

    def resolve_path(self, storage_key: str) -> Path:
        candidate = self.resolve_target_path(storage_key)
        if not candidate.exists() or not candidate.is_file():
            raise FileNotFoundError("Arquivo local não encontrado.")
        return candidate

    def resolve_target_path(self, storage_key: str) -> Path:
        try:
            storage_key = validate_attachment_storage_key(storage_key)
        except UploadValidationError as exc:
            raise FileNotFoundError("Arquivo fora da raiz de armazenamento configurada.") from exc
        candidate = (self.root / storage_key).resolve()
        root = self.root.resolve()
        if root not in candidate.parents and candidate != root:
            raise FileNotFoundError("Chave de arquivo local fora da raiz configurada.")
        return candidate

    def generate_download_url(self, storage_key: str, original_filename: str | None = None) -> None:
        return None


class R2StorageBackend:
    name = "r2"

    def __init__(self, config: R2Config):
        self.config = config
        try:
            import boto3
        except ImportError as exc:
            raise StorageConfigurationError("R2 foi configurado, mas a dependência boto3 não está instalada.") from exc

        self.client = boto3.client(
            "s3",
            endpoint_url=config.endpoint_url,
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.secret_access_key,
            region_name="auto",
        )

    def save_file(
        self,
        *,
        entity_type: str,
        entity_id: int,
        original_filename: str,
        content: bytes,
        mime_type: str | None = None,
    ) -> StoredFile:
        digest = _sha256(content)
        content_type = _guess_mime_type(original_filename, mime_type)
        storage_key = make_storage_key(entity_type, entity_id, original_filename, digest)
        self.client.put_object(
            Bucket=self.config.bucket,
            Key=storage_key,
            Body=content,
            ContentType=content_type or "application/octet-stream",
            Metadata={"sha256": digest},
        )
        return StoredFile(
            original_filename=Path(original_filename or "arquivo").name,
            storage_key=storage_key,
            storage_backend=self.name,
            mime_type=content_type,
            file_size=len(content),
            sha256=digest,
        )

    def get_file_bytes(self, storage_key: str) -> bytes:
        storage_key = validate_attachment_storage_key(storage_key)
        response = self.client.get_object(Bucket=self.config.bucket, Key=storage_key)
        return response["Body"].read()

    def generate_download_url(
        self,
        storage_key: str,
        original_filename: str | None = None,
        expires_in: int = DEFAULT_DOWNLOAD_TTL_SECONDS,
    ) -> str:
        storage_key = validate_attachment_storage_key(storage_key)
        safe_name = _safe_filename(original_filename or Path(storage_key).name)
        return self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.config.bucket,
                "Key": storage_key,
                "ResponseContentDisposition": f"attachment; filename*=UTF-8''{quote(safe_name)}",
            },
            ExpiresIn=expires_in,
        )


def get_active_storage_backend(database_url: str | None = None) -> LocalStorageBackend | R2StorageBackend:
    del database_url  # Database and file-storage selection are intentionally independent.
    selected = selected_storage_backend()
    if selected == "local":
        return LocalStorageBackend()

    config = get_r2_config()
    if config is None:
        missing = ", ".join(missing_r2_config_keys())
        raise StorageConfigurationError(
            "STORAGE_BACKEND=r2 exige configuração R2 completa. "
            f"Defina: {missing}."
        )
    return R2StorageBackend(config)


def get_storage_backend_for_name(storage_backend: str) -> LocalStorageBackend | R2StorageBackend:
    backend = str(storage_backend or "").strip().lower()
    if backend == "local":
        return LocalStorageBackend()
    if backend == "r2":
        config = get_r2_config()
        if config is None:
            missing = ", ".join(missing_r2_config_keys())
            raise StorageConfigurationError(
                "Este anexo está no R2, mas a configuração R2 está ausente ou incompleta. "
                f"Defina: {missing}."
            )
        return R2StorageBackend(config)
    raise StorageConfigurationError(f"Backend de armazenamento desconhecido: {storage_backend}.")
