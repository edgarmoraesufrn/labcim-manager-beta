from __future__ import annotations

import ipaddress
import os
from pathlib import Path
from typing import Mapping
from urllib.parse import urlencode, urlsplit, urlunsplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCAL_STORAGE_ROOT = PROJECT_ROOT / "data" / "uploads"
DEFAULT_LOCAL_WORK_ROOT = PROJECT_ROOT / "data"
VALID_APP_ENVIRONMENTS = frozenset({"development", "test", "staging", "production"})
VALID_STORAGE_BACKENDS = frozenset({"local", "r2"})


class ConfigurationError(ValueError):
    """Raised when an explicit application setting is invalid or unsafe."""


def _environment(environ: Mapping[str, str] | None = None) -> Mapping[str, str]:
    return os.environ if environ is None else environ


def project_path(*parts: str) -> Path:
    """Return an application-owned path independent of the process CWD."""

    return PROJECT_ROOT.joinpath(*parts)


def get_app_environment(environ: Mapping[str, str] | None = None) -> str:
    value = _environment(environ).get("APP_ENV", "development").strip().lower()
    if value not in VALID_APP_ENVIRONMENTS:
        allowed = ", ".join(sorted(VALID_APP_ENVIRONMENTS))
        raise ConfigurationError(f"APP_ENV inválido. Use um destes valores: {allowed}.")
    return value


def normalize_storage_backend(value: str | None, *, environment: str) -> str:
    selected = str(value or "").strip().lower()
    if not selected:
        if environment in {"development", "test"}:
            return "local"
        raise ConfigurationError("STORAGE_BACKEND deve ser definido explicitamente em staging/produção.")
    if selected not in VALID_STORAGE_BACKENDS:
        allowed = ", ".join(sorted(VALID_STORAGE_BACKENDS))
        raise ConfigurationError(f"STORAGE_BACKEND inválido. Use: {allowed}.")
    return selected


def resolve_local_storage_root(
    value: str | Path | None,
    *,
    environment: str,
) -> Path:
    raw_value = str(value or "").strip()
    if not raw_value:
        if environment in {"staging", "production"}:
            raise ConfigurationError(
                "LOCAL_STORAGE_ROOT deve ser um caminho absoluto quando STORAGE_BACKEND=local em staging/produção."
            )
        return DEFAULT_LOCAL_STORAGE_ROOT.resolve()

    root = Path(raw_value).expanduser()
    if not root.is_absolute():
        if environment in {"staging", "production"}:
            raise ConfigurationError("LOCAL_STORAGE_ROOT deve ser absoluto em staging/produção.")
        root = PROJECT_ROOT / root
    return root.resolve()


def resolve_local_work_root(
    value: str | Path | None,
    *,
    environment: str,
) -> Path:
    raw_value = str(value or "").strip()
    if not raw_value:
        if environment in {"staging", "production"}:
            raise ConfigurationError("LOCAL_WORK_ROOT deve ser um caminho absoluto em staging/produção.")
        return DEFAULT_LOCAL_WORK_ROOT.resolve()

    root = Path(raw_value).expanduser()
    if not root.is_absolute():
        if environment in {"staging", "production"}:
            raise ConfigurationError("LOCAL_WORK_ROOT deve ser absoluto em staging/produção.")
        root = PROJECT_ROOT / root
    return root.resolve()


def get_local_work_root(environ: Mapping[str, str] | None = None) -> Path:
    values = _environment(environ)
    return resolve_local_work_root(
        values.get("LOCAL_WORK_ROOT"),
        environment=get_app_environment(values),
    )


def normalize_public_app_url(value: str | None, *, environment: str = "development") -> str | None:
    raw_value = str(value or "").strip()
    if not raw_value:
        return None

    parsed = urlsplit(raw_value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigurationError("APP_BASE_URL deve ser uma URL HTTP(S) absoluta.")
    if parsed.username or parsed.password:
        raise ConfigurationError("APP_BASE_URL não pode conter credenciais.")
    if parsed.query or parsed.fragment:
        raise ConfigurationError("APP_BASE_URL não pode conter query string ou fragmento.")

    hostname = (parsed.hostname or "").lower()
    if environment == "production":
        if parsed.scheme != "https":
            raise ConfigurationError("APP_BASE_URL deve usar HTTPS em produção.")
        if hostname == "localhost" or hostname.endswith(".localhost"):
            raise ConfigurationError("APP_BASE_URL de produção não pode apontar para localhost.")
        try:
            if ipaddress.ip_address(hostname).is_private:
                raise ConfigurationError("APP_BASE_URL de produção não pode apontar para IP privado.")
        except ValueError:
            pass

    path = "/" + parsed.path.strip("/") if parsed.path.strip("/") else ""
    path = f"{path}/" if path else "/"
    if environment == "production" and path != "/manager/":
        raise ConfigurationError("APP_BASE_URL de produção deve apontar exatamente para /manager/.")
    return urlunsplit((parsed.scheme.lower(), parsed.netloc, path, "", ""))


def get_public_app_url(
    environ: Mapping[str, str] | None = None,
    *,
    required: bool = False,
) -> str | None:
    values = _environment(environ)
    environment = get_app_environment(values)
    url = normalize_public_app_url(values.get("APP_BASE_URL"), environment=environment)
    if required and url is None:
        raise ConfigurationError("APP_BASE_URL deve ser configurada para gerar URLs públicas e QR Codes.")
    return url


def build_public_url(base_url: str, query: Mapping[str, object] | None = None) -> str:
    normalized = normalize_public_app_url(base_url)
    if normalized is None:
        raise ConfigurationError("Uma URL pública válida é obrigatória.")
    parsed = urlsplit(normalized)
    query_string = urlencode({key: str(value) for key, value in (query or {}).items()})
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query_string, ""))


def build_public_static_url(base_url: str, filename: str) -> str:
    safe_filename = Path(filename).name
    if not safe_filename or safe_filename != filename:
        raise ConfigurationError("Nome de asset estático inválido.")
    normalized = normalize_public_app_url(base_url)
    if normalized is None:
        raise ConfigurationError("Uma URL pública válida é obrigatória.")
    return f"{normalized}app/static/{safe_filename}"
