#!/usr/bin/env python3
"""Offline, read-only production preflight for LabCim Manager.

The checker reads repository files, process metadata and optionally an environment
file. It never opens a database connection, performs network I/O, imports app.py,
creates files or changes permissions. Secret values are never printed.
"""

from __future__ import annotations

import argparse
import ast
from collections import Counter
from dataclasses import dataclass
import importlib.metadata
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
import tomllib
from urllib.parse import urlsplit


EXPECTED_BASE_PATH = "manager"
EXPECTED_PYTHON = "3.12.13"
EXPECTED_TIMEZONE = "America/Fortaleza"
PLACEHOLDER_RE = re.compile(
    r"<[A-Z][A-Z0-9_ -]*>|CHANGE[_ -]?ME|COLE_AQUI|EXAMPLE\.INVALID",
    re.IGNORECASE,
)
FALSE_VALUES = {"", "0", "false", "no", "nao", "não", "off"}
TRUE_VALUES = {"1", "true", "yes", "sim", "on"}
SEVERITY_ORDER = {
    "CODE BLOCKER": 0,
    "ENVIRONMENT REQUIRED": 1,
    "DEPLOYMENT PENDING": 2,
    "WARNING": 3,
    "PASS": 4,
}


@dataclass(frozen=True)
class Finding:
    severity: str
    check: str
    message: str


class Report:
    def __init__(self) -> None:
        self.findings: list[Finding] = []

    def add(self, severity: str, check: str, message: str) -> None:
        self.findings.append(Finding(severity, check, message))

    def passed(self, check: str, message: str) -> None:
        self.add("PASS", check, message)

    def warning(self, check: str, message: str) -> None:
        self.add("WARNING", check, message)

    def code_blocker(self, check: str, message: str) -> None:
        self.add("CODE BLOCKER", check, message)

    def environment_required(self, check: str, message: str) -> None:
        self.add("ENVIRONMENT REQUIRED", check, message)

    def deployment_pending(self, check: str, message: str) -> None:
        self.add("DEPLOYMENT PENDING", check, message)

    def render(self) -> Counter[str]:
        for finding in sorted(
            self.findings,
            key=lambda item: (SEVERITY_ORDER[item.severity], item.check),
        ):
            print(f"[{finding.severity:<20}] {finding.check}: {finding.message}")
        counts: Counter[str] = Counter(item.severity for item in self.findings)
        print(
            "\nSummary: "
            f"{counts['CODE BLOCKER']} code blocker(s), "
            f"{counts['DEPLOYMENT PENDING']} deployment pending, "
            f"{counts['ENVIRONMENT REQUIRED']} environment required, "
            f"{counts['WARNING']} warning(s), "
            f"{counts['PASS']} pass(es)."
        )
        return counts


def parse_args() -> argparse.Namespace:
    default_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Run an offline, non-mutating production-readiness preflight.",
    )
    parser.add_argument("--repo-root", type=Path, default=default_root)
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Read a systemd-style environment file without displaying its values.",
    )
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="Return exit code 1 when only warnings remain.",
    )
    return parser.parse_args()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_env_file(path: Path | None, report: Report) -> dict[str, str]:
    values = dict(os.environ)
    if path is None:
        report.environment_required(
            "environment.file",
            "No external production environment file was supplied for validation.",
        )
        return values
    if not path.is_file():
        report.environment_required(
            "environment.file",
            "The supplied environment file does not exist or is not a regular file.",
        )
        return values

    try:
        for line_number, raw_line in enumerate(read_text(path).splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            if "=" not in line:
                report.warning(
                    "environment.file",
                    f"Ignored malformed entry at line {line_number}; no value was printed.",
                )
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                report.warning(
                    "environment.file",
                    f"Ignored invalid variable name at line {line_number}.",
                )
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            values[key] = value
    except (OSError, UnicodeError) as exc:
        report.environment_required(
            "environment.file",
            f"Could not read the environment file: {type(exc).__name__}.",
        )
        return values

    report.passed("environment.file", "External environment file parsed; values were not displayed.")
    return values


def is_real_value(value: str | None) -> bool:
    return bool(value and value.strip() and not PLACEHOLDER_RE.search(value))


def require_env(env: dict[str, str], report: Report, key: str, purpose: str) -> None:
    if is_real_value(env.get(key)):
        report.passed(f"environment.{key}", f"Configured for {purpose}; value withheld.")
    else:
        report.environment_required(
            f"environment.{key}",
            f"Missing or placeholder value for {purpose}.",
        )


def parse_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    return None


def load_streamlit_config(repo_root: Path, report: Report) -> dict[str, object]:
    path = repo_root / ".streamlit" / "config.toml"
    if not path.is_file():
        report.code_blocker("streamlit.config", ".streamlit/config.toml is missing.")
        return {}
    try:
        config = tomllib.loads(read_text(path))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        report.code_blocker(
            "streamlit.config",
            f"Config cannot be parsed: {type(exc).__name__}.",
        )
        return {}
    report.passed("streamlit.config", "Project Streamlit configuration parses successfully.")
    return config


def streamlit_value(
    env: dict[str, str],
    config: dict[str, object],
    section: str,
    key: str,
) -> object | None:
    snake_key = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", key)
    snake_key = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", snake_key).upper()
    env_key = f"STREAMLIT_{section}_{snake_key}".upper()
    if env_key in env:
        return env[env_key]
    section_values = config.get(section.lower(), {})
    if isinstance(section_values, dict):
        return section_values.get(key)
    return None


def check_streamlit(env: dict[str, str], config: dict[str, object], report: Report) -> None:
    exact_values = {
        "baseUrlPath": EXPECTED_BASE_PATH,
        "address": "127.0.0.1",
        "port": "8501",
    }
    for key, expected in exact_values.items():
        actual = str(streamlit_value(env, config, "SERVER", key) or "").strip("/ ")
        if actual.lower() == expected.lower():
            report.passed(f"streamlit.{key}", f"Expected value {expected!r} is configured.")
        else:
            report.code_blocker(
                f"streamlit.{key}",
                f"Must resolve to {expected!r} for the production profile.",
            )

    for key in ("headless", "enableCORS", "enableXsrfProtection"):
        if parse_bool(streamlit_value(env, config, "SERVER", key)) is True:
            report.passed(f"streamlit.{key}", "Set to true.")
        else:
            report.code_blocker(f"streamlit.{key}", "Must resolve to true.")

    error_details = str(
        streamlit_value(env, config, "CLIENT", "showErrorDetails") or ""
    ).strip().lower()
    if error_details == "none":
        report.passed("streamlit.showErrorDetails", "Browser error details are disabled.")
    else:
        report.code_blocker(
            "streamlit.showErrorDetails",
            "Must resolve to 'none' in the production profile.",
        )

    for key in ("maxUploadSize", "maxMessageSize"):
        raw_value = streamlit_value(env, config, "SERVER", key)
        try:
            size_mb = int(str(raw_value))
        except (TypeError, ValueError):
            report.code_blocker(
                f"streamlit.{key}",
                "Must be explicitly configured as an integer number of MB.",
            )
            continue
        if 1 <= size_mb <= 100:
            report.passed(
                f"streamlit.{key}",
                "Explicit bounded value is configured; value withheld.",
            )
        else:
            report.code_blocker(
                f"streamlit.{key}",
                "Must be between 1 and the M0 ceiling of 100 MB, pending policy approval.",
            )

    require_env(env, report, "STREAMLIT_SERVER_COOKIE_SECRET", "stable Streamlit cookie signing")


def check_database_environment(env: dict[str, str], report: Report) -> None:
    database_url = env.get("DATABASE_URL")
    if not is_real_value(database_url):
        report.environment_required(
            "database.url",
            "DATABASE_URL is missing or a placeholder; production would fall back to SQLite.",
        )
        return
    try:
        parsed = urlsplit(database_url)
    except ValueError:
        report.environment_required("database.url", "DATABASE_URL is malformed; value withheld.")
        return
    if parsed.scheme not in {"postgres", "postgresql"}:
        report.environment_required(
            "database.url",
            "DATABASE_URL must use PostgreSQL in production.",
        )
    elif not parsed.hostname or not parsed.path.strip("/") or not parsed.username:
        report.environment_required(
            "database.url",
            "PostgreSQL URL lacks host, database name or user; value withheld.",
        )
    else:
        report.passed(
            "database.url",
            "PostgreSQL URL structure is valid; credentials and host were withheld.",
        )


def check_application_environment(env: dict[str, str], repo_root: Path, report: Report) -> None:
    app_env = str(env.get("APP_ENV") or "").strip().lower()
    if app_env == "production":
        report.passed("environment.APP_ENV", "Production mode is explicitly selected.")
    else:
        report.environment_required(
            "environment.APP_ENV",
            "APP_ENV must be explicitly set to production for production validation.",
        )

    app_base_url = env.get("APP_BASE_URL")
    try:
        parsed_base_url = urlsplit(app_base_url or "")
    except ValueError:
        parsed_base_url = urlsplit("")
    hostname = (parsed_base_url.hostname or "").lower()
    private_target = hostname == "localhost" or hostname.endswith(".localhost")
    try:
        private_target = private_target or ipaddress.ip_address(hostname).is_private
    except ValueError:
        pass
    if (
        is_real_value(app_base_url)
        and parsed_base_url.scheme == "https"
        and hostname
        and not private_target
        and parsed_base_url.path.rstrip("/") == "/manager"
        and not parsed_base_url.query
        and not parsed_base_url.fragment
        and not parsed_base_url.username
    ):
        report.passed(
            "environment.APP_BASE_URL",
            "HTTPS public application URL targets /manager/; host withheld.",
        )
    else:
        report.environment_required(
            "environment.APP_BASE_URL",
            "APP_BASE_URL must be a credential-free HTTPS URL ending in /manager/.",
        )

    check_database_environment(env, report)
    for key, purpose in (
        ("LABCIM_SMTP_HOST", "SMTP host"),
        ("LABCIM_SMTP_PORT", "SMTP port"),
        ("LABCIM_SMTP_USER", "SMTP account"),
        ("LABCIM_SMTP_PASSWORD", "SMTP credential"),
        ("LABCIM_SMTP_FROM", "SMTP sender"),
        ("LABCIM_SMTP_TLS", "SMTP STARTTLS policy"),
    ):
        require_env(env, report, key, purpose)

    if parse_bool(env.get("LABCIM_AUTH_DEBUG_CODES")) is False and "LABCIM_AUTH_DEBUG_CODES" in env:
        report.passed("authentication.debug_codes", "Debug-code display is explicitly disabled.")
    else:
        report.environment_required(
            "authentication.debug_codes",
            "LABCIM_AUTH_DEBUG_CODES must be explicitly false.",
        )

    if env.get("TZ") == EXPECTED_TIMEZONE:
        report.passed("process.timezone", f"Timezone is explicitly {EXPECTED_TIMEZONE}.")
    else:
        report.environment_required(
            "process.timezone",
            f"TZ must be {EXPECTED_TIMEZONE} while timestamps remain naive text.",
        )

    log_level = str(env.get("APP_LOG_LEVEL") or "INFO").strip().upper()
    if log_level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        report.passed("environment.APP_LOG_LEVEL", f"Application log level resolves to {log_level}.")
    else:
        report.environment_required(
            "environment.APP_LOG_LEVEL",
            "APP_LOG_LEVEL must be a standard Python logging level.",
        )

    work_root = str(env.get("LOCAL_WORK_ROOT") or "").strip()
    if work_root and Path(work_root).is_absolute():
        report.passed(
            "filesystem.work_root",
            "An absolute writable work root is configured; value withheld.",
        )
    else:
        report.environment_required(
            "filesystem.work_root",
            "LOCAL_WORK_ROOT must be an absolute path in production.",
        )

    backend = str(env.get("STORAGE_BACKEND") or "").strip().lower()
    if backend not in {"local", "r2"}:
        report.environment_required(
            "storage.backend",
            "STORAGE_BACKEND must explicitly select local or r2.",
        )
    elif backend == "local":
        report.passed("storage.backend", "Local file storage is explicitly selected.")
        root = str(env.get("LOCAL_STORAGE_ROOT") or "").strip()
        if root and Path(root).is_absolute():
            report.passed(
                "storage.local_root",
                "An absolute institutional storage root is configured; value withheld.",
            )
        else:
            report.environment_required(
                "storage.local_root",
                "LOCAL_STORAGE_ROOT must be an absolute path for production local storage.",
            )
    else:
        report.passed("storage.backend", "R2 object storage is explicitly selected.")
        for key in ("R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"):
            require_env(env, report, key, "the explicitly selected R2 backend")

    storage_source = read_text(repo_root / "labcim_manager" / "storage.py")
    if "del database_url" in storage_source and "selected_storage_backend()" in storage_source:
        report.passed(
            "storage.database_independence",
            "File backend selection is explicit and independent from DATABASE_URL.",
        )
    else:
        report.code_blocker(
            "storage.database_independence",
            "Storage selection still appears coupled to database configuration.",
        )


def check_manifest(repo_root: Path, report: Report) -> None:
    path = repo_root / "static" / "manifest.json"
    try:
        manifest = json.loads(read_text(path))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        report.code_blocker(
            "subpath.manifest",
            f"PWA manifest cannot be read: {type(exc).__name__}.",
        )
        return
    for key in ("start_url", "scope"):
        if manifest.get(key) == "/manager/":
            report.passed(f"subpath.manifest.{key}", "PWA value is scoped to /manager/.")
        else:
            report.code_blocker(f"subpath.manifest.{key}", "Must be exactly /manager/.")
    icons = manifest.get("icons")
    if isinstance(icons, list) and icons and all(
        isinstance(icon, dict)
        and str(icon.get("src") or "").startswith("/manager/app/static/")
        for icon in icons
    ):
        report.passed("subpath.manifest.icons", "PWA icons are scoped beneath /manager/.")
    else:
        report.code_blocker("subpath.manifest.icons", "PWA icon paths must remain under /manager/.")


def function_source(path: Path, function_name: str) -> str:
    source = read_text(path)
    tree = ast.parse(source)
    lines = source.splitlines()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return "\n".join(lines[node.lineno - 1 : node.end_lineno])
    return ""


def check_source_gates(repo_root: Path, report: Report) -> None:
    app_path = repo_root / "app.py"
    app_source = read_text(app_path)
    database_source = read_text(repo_root / "labcim_manager" / "db.py")
    startup_source = function_source(app_path, "ensure_database_compatible")
    mutating_tokens = (
        "init_db(",
        "import_base_xlsx(",
        "seed_default_pops(",
        "ALTER TABLE",
        "CREATE INDEX",
        "UPDATE ",
    )
    if (
        not startup_source
        or "verify_database_target(" not in startup_source
        or any(token in startup_source for token in mutating_tokens)
    ):
        report.code_blocker(
            "database.startup_mutation",
            "Startup is not demonstrably limited to opening and verifying an existing schema.",
        )
    else:
        report.passed(
            "database.startup_mutation",
            "Web startup opens an existing database and performs a read-only compatibility check.",
        )

    if "https://labcim-manager.streamlit.app" in app_source:
        report.code_blocker(
            "subpath.qr_default",
            "The legacy Streamlit Cloud URL remains in QR generation.",
        )
    elif "get_public_app_url(required=True)" in app_source:
        report.passed(
            "subpath.qr_default",
            "QR generation requires the centrally validated public application URL.",
        )
    else:
        report.code_blocker(
            "subpath.qr_default",
            "QR generation does not visibly enforce central public URL configuration.",
        )

    if re.search(r"file_uploader\(\s*[\"']Arquivo[\"']\s*,\s*key=", app_source):
        report.code_blocker(
            "uploads.equipment_allowlist",
            "Equipment document uploader still has no explicit type allowlist.",
        )
    else:
        report.passed(
            "uploads.equipment_allowlist",
            "Known unrestricted equipment uploader pattern is absent.",
        )

    legacy_error_patterns = (
        'st.error(f"Erro na importação: {exc}")',
        'st.warning(f"Não foi possível abrir o anexo persistido: {exc}")',
        "return False, str(exc)",
        'f"Erro ao atualizar status da reserva: {exc}"',
        'f"Erro ao registrar reserva: {exc}"',
        'f"Erro ao atualizar equipamento: {exc}"',
    )
    error_source = app_source + "\n" + database_source
    if any(pattern in error_source for pattern in legacy_error_patterns):
        report.code_blocker(
            "errors.touched_paths",
            "A raw exception remains exposed in an M1A-touched browser path.",
        )
    elif error_source.count("safe_exception_message(") >= 6:
        report.passed(
            "errors.touched_paths",
            "M1A-touched failure paths log diagnostics and show opaque references.",
        )
    else:
        report.code_blocker(
            "errors.touched_paths",
            "The production-safe error helper is not applied to all M1A-touched paths.",
        )

    path_patterns = (
        "Path.cwd()",
        "os.getcwd()",
        'Path("data/',
        "Path('data/",
        'Path("assets/',
        "Path('assets/",
    )
    if any(pattern in app_source for pattern in path_patterns):
        report.code_blocker(
            "filesystem.cwd_independence",
            "Application entrypoint still contains a known CWD-dependent owned path.",
        )
    else:
        report.passed(
            "filesystem.cwd_independence",
            "Known application-owned paths resolve independently from process CWD.",
        )

    unsafe_blocks = app_source.count("unsafe_allow_html=True")
    if unsafe_blocks:
        report.warning(
            "security.unsafe_html",
            f"{unsafe_blocks} unsafe HTML rendering call(s) require manual escaping review.",
        )
    else:
        report.passed("security.unsafe_html", "No unsafe HTML rendering calls found.")


def check_migrations(repo_root: Path, report: Report) -> None:
    migration_dir = repo_root / "labcim_manager" / "migrations"
    schema_path = repo_root / "labcim_manager" / "schema.py"
    cli_path = repo_root / "labcim_manager" / "db_migrate.py"
    migration_files = sorted(migration_dir.glob("v[0-9][0-9][0-9]_*.py"))
    versions = [
        int(match.group(1))
        for path in migration_files
        if (match := re.fullmatch(r"v([0-9]{3})_.+\.py", path.name))
    ]
    ordered = bool(versions) and versions == list(range(1, max(versions) + 1))
    schema_source = read_text(schema_path) if schema_path.is_file() else ""
    cli_source = read_text(cli_path) if cli_path.is_file() else ""
    required_schema_markers = (
        "labcim_schema_migrations",
        "LATEST_SCHEMA_VERSION",
        "checksum",
        "baseline_existing_schema",
        "pg_try_advisory_xact_lock",
        "BEGIN IMMEDIATE",
    )
    required_commands = (
        '"status"',
        '"verify"',
        '"upgrade"',
        '"initialize"',
        '"baseline-existing"',
    )
    if (
        ordered
        and all(marker in schema_source for marker in required_schema_markers)
        and all(command in cli_source for command in required_commands)
    ):
        report.passed(
            "database.migrations",
            f"Ordered migrations 1..{versions[-1]}, version ledger, locking and administrative CLI are present.",
        )
    else:
        report.code_blocker(
            "database.migrations",
            "The ordered migration, version-ledger, locking or administrative CLI contract is incomplete.",
        )


def check_runtime(repo_root: Path, report: Report) -> None:
    version_path = repo_root / ".python-version"
    try:
        declared_version = read_text(version_path).strip()
    except (OSError, UnicodeError):
        declared_version = ""
    if declared_version == EXPECTED_PYTHON:
        report.passed(
            "runtime.python_declared",
            f"Repository declares the reviewed Python {EXPECTED_PYTHON} runtime.",
        )
    else:
        report.code_blocker(
            "runtime.python_declared",
            f".python-version must declare the reviewed runtime {EXPECTED_PYTHON}.",
        )

    current_version = ".".join(str(part) for part in sys.version_info[:3])
    if current_version == EXPECTED_PYTHON:
        report.passed("runtime.python_current", "Preflight runs under the declared Python runtime.")
    else:
        report.environment_required(
            "runtime.python_current",
            f"Run preflight with Python {EXPECTED_PYTHON}; current interpreter is {current_version}.",
        )

    requirements_path = repo_root / "requirements.txt"
    input_path = repo_root / "requirements.in"
    lock_path = repo_root / "requirements.lock"
    try:
        install_lines = [
            line.strip()
            for line in read_text(requirements_path).splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    except (OSError, UnicodeError):
        install_lines = []
    if "--require-hashes" in install_lines and "-r requirements.lock" in install_lines:
        report.passed(
            "runtime.install_contract",
            "Production install delegates to the fully resolved hash-locked graph.",
        )
    else:
        report.code_blocker(
            "runtime.install_contract",
            "requirements.txt must enforce hashes and include requirements.lock.",
        )

    try:
        source_lines = [
            line.strip()
            for line in read_text(input_path).splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    except (OSError, UnicodeError):
        source_lines = []
    required_names = {"streamlit", "pandas", "plotly", "qrcode", "openpyxl", "psycopg", "boto3"}
    source_names = {
        re.split(r"\[|==", line, maxsplit=1)[0].lower().replace("_", "-")
        for line in source_lines
        if "==" in line
    }
    if source_lines and all("==" in line for line in source_lines) and required_names <= source_names:
        report.passed(
            "runtime.direct_dependencies",
            "All reviewed direct runtime dependencies are explicitly and exactly pinned.",
        )
    else:
        report.code_blocker(
            "runtime.direct_dependencies",
            "requirements.in must exactly pin every reviewed direct runtime dependency.",
        )

    try:
        lock_source = read_text(lock_path)
    except (OSError, UnicodeError):
        lock_source = ""
    package_count = len(re.findall(r"(?m)^[A-Za-z0-9_.-]+(?:\[[^]]+\])?==[^\s\\]+", lock_source))
    hash_count = lock_source.count("--hash=sha256:")
    if package_count and hash_count >= package_count and "# This file is autogenerated by pip-compile" in lock_source:
        report.passed(
            "runtime.dependency_lock",
            f"Resolved lock contains {package_count} package record(s) protected by hashes.",
        )
    else:
        report.code_blocker(
            "runtime.dependency_lock",
            "requirements.lock is absent, incomplete, or lacks hashes.",
        )

    modules = {
        "streamlit": "streamlit",
        "pandas": "pandas",
        "plotly": "plotly",
        "qrcode": "qrcode",
        "openpyxl": "openpyxl",
        "psycopg": "psycopg",
        "boto3": "boto3",
    }
    for distribution, module in modules.items():
        if importlib.util.find_spec(module) is None:
            report.environment_required(
                f"runtime.import.{module}",
                "Required module is not importable in the current environment; install the lock.",
            )
            continue
        try:
            importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            report.warning(
                f"runtime.import.{module}",
                "Module imports but package metadata is unavailable.",
            )
        else:
            report.passed(
                f"runtime.import.{module}",
                "Required module and package metadata are available.",
            )


def check_required_files(repo_root: Path, report: Report) -> None:
    required = (
        "app.py",
        ".python-version",
        "requirements.in",
        "requirements.txt",
        "requirements.lock",
        ".streamlit/config.toml",
        "labcim_manager/config.py",
        "labcim_manager/db.py",
        "labcim_manager/db_migrate.py",
        "labcim_manager/errors.py",
        "labcim_manager/schema.py",
        "labcim_manager/storage.py",
        "static/manifest.json",
        "docs/PRODUCTION_READINESS.md",
        "docs/UFRN_DEPLOYMENT_PLAN.md",
        "docs/DATABASE_MIGRATION_PLAN.md",
        "docs/FILE_STORAGE_MIGRATION_PLAN.md",
        "docs/PRODUCTION_ENV_TEMPLATE.md",
        "docs/LOCAL_STAGING_GUIDE.md",
        "docs/DATABASE_SCHEMA_LIFECYCLE.md",
    )
    missing = [relative for relative in required if not (repo_root / relative).is_file()]
    if missing:
        report.code_blocker(
            "repository.required_files",
            f"Missing {len(missing)} required foundation file(s): {', '.join(missing)}.",
        )
    else:
        report.passed("repository.required_files", "All required M1A/M1B foundation files are present.")

    for secret_path in (repo_root / ".streamlit" / "secrets.toml", repo_root / ".env"):
        if secret_path.exists():
            report.warning(
                "repository.local_secrets",
                "A local secret-bearing file exists; verify it is untracked and permission-restricted.",
            )


def check_deployment_boundaries(report: Report) -> None:
    for check, message in (
        ("deployment.nginx", "Real Nginx routing, TLS and WebSocket forwarding require UFRN deployment validation."),
        ("deployment.systemd", "The real systemd unit, service user and filesystem permissions require UFRN validation."),
        ("deployment.postgresql", "UFRN PostgreSQL connectivity and target schema compatibility have not been tested."),
        ("deployment.backup_restore", "A backup and restore drill remains required before production."),
        ("deployment.manager_browser", "Browser/PWA behavior behind the real /manager/ reverse proxy remains to be validated."),
    ):
        report.deployment_pending(check, message)


def main() -> int:
    args = parse_args()
    report = Report()
    repo_root = args.repo_root.resolve()
    if not repo_root.is_dir():
        print("[CODE BLOCKER        ] repository.root: Repository root is not a directory.")
        return 2

    env = load_env_file(args.env_file, report)
    check_required_files(repo_root, report)
    config = load_streamlit_config(repo_root, report)
    check_streamlit(env, config, report)
    check_application_environment(env, repo_root, report)
    check_manifest(repo_root, report)
    check_source_gates(repo_root, report)
    check_migrations(repo_root, report)
    check_runtime(repo_root, report)
    check_deployment_boundaries(report)

    counts = report.render()
    if counts["CODE BLOCKER"]:
        return 2
    if counts["ENVIRONMENT REQUIRED"] or counts["DEPLOYMENT PENDING"]:
        return 1
    if counts["WARNING"] and args.strict_warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
