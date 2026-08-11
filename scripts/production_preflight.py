#!/usr/bin/env python3
"""Offline, read-only production preflight for LabCim Manager.

The checker reads repository files, process metadata and optionally an environment
file. It never opens a database connection, performs network I/O, imports app.py,
creates files or changes permissions. Secret values are never printed.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tomllib
from urllib.parse import urlsplit


EXPECTED_BASE_PATH = "manager"
EXPECTED_TIMEZONE = "America/Fortaleza"
PLACEHOLDER_RE = re.compile(r"<[A-Z][A-Z0-9_ -]*>|CHANGE[_ -]?ME|COLE_AQUI|EXAMPLE\.INVALID", re.IGNORECASE)
FALSE_VALUES = {"", "0", "false", "no", "nao", "não", "off"}
TRUE_VALUES = {"1", "true", "yes", "sim", "on"}


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

    def warn(self, check: str, message: str) -> None:
        self.add("WARN", check, message)

    def blocker(self, check: str, message: str) -> None:
        self.add("BLOCKER", check, message)

    def render(self) -> tuple[int, int, int]:
        order = {"BLOCKER": 0, "WARN": 1, "PASS": 2}
        for finding in sorted(self.findings, key=lambda item: (order[item.severity], item.check)):
            print(f"[{finding.severity:7}] {finding.check}: {finding.message}")
        blockers = sum(item.severity == "BLOCKER" for item in self.findings)
        warnings = sum(item.severity == "WARN" for item in self.findings)
        passes = sum(item.severity == "PASS" for item in self.findings)
        print(f"\nSummary: {blockers} blocker(s), {warnings} warning(s), {passes} pass(es).")
        return blockers, warnings, passes


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
        help="Return exit code 1 when warnings remain and no blockers exist.",
    )
    return parser.parse_args()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_env_file(path: Path | None, report: Report) -> dict[str, str]:
    values = dict(os.environ)
    if path is None:
        report.warn("environment.file", "No external environment file was supplied for validation.")
        return values
    if not path.is_file():
        report.blocker("environment.file", "The supplied environment file does not exist or is not a regular file.")
        return values

    try:
        for line_number, raw_line in enumerate(read_text(path).splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            if "=" not in line:
                report.warn("environment.file", f"Ignored malformed entry at line {line_number}; no value was printed.")
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                report.warn("environment.file", f"Ignored invalid variable name at line {line_number}.")
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            values[key] = value
    except (OSError, UnicodeError) as exc:
        report.blocker("environment.file", f"Could not read the environment file: {type(exc).__name__}.")
        return values

    report.passed("environment.file", "External environment file parsed; values were not displayed.")
    return values


def is_real_value(value: str | None) -> bool:
    return bool(value and value.strip() and not PLACEHOLDER_RE.search(value))


def require_env(env: dict[str, str], report: Report, key: str, purpose: str) -> None:
    if is_real_value(env.get(key)):
        report.passed(f"environment.{key}", f"Configured for {purpose}; value withheld.")
    else:
        report.blocker(f"environment.{key}", f"Missing or placeholder value for {purpose}.")


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
        report.blocker("streamlit.config", ".streamlit/config.toml is missing.")
        return {}
    try:
        config = tomllib.loads(read_text(path))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        report.blocker("streamlit.config", f"Config cannot be parsed: {type(exc).__name__}.")
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
    base_path = streamlit_value(env, config, "SERVER", "baseUrlPath")
    if str(base_path or "").strip("/ ") == EXPECTED_BASE_PATH:
        report.passed("streamlit.baseUrlPath", "Configured for /manager/.")
    else:
        report.blocker("streamlit.baseUrlPath", "Must resolve to 'manager'.")

    address = str(streamlit_value(env, config, "SERVER", "address") or "").strip().lower()
    if address == "127.0.0.1":
        report.passed("streamlit.address", "Bound explicitly to IPv4 loopback.")
    else:
        report.blocker("streamlit.address", "Must be explicitly set to 127.0.0.1.")

    port = str(streamlit_value(env, config, "SERVER", "port") or "").strip()
    if port == "8501":
        report.passed("streamlit.port", "Expected upstream port is configured.")
    else:
        report.blocker("streamlit.port", "Must resolve to the approved upstream port 8501.")

    expected_booleans = {
        ("SERVER", "headless"): True,
        ("SERVER", "enableCORS"): True,
        ("SERVER", "enableXsrfProtection"): True,
    }
    for (section, key), expected in expected_booleans.items():
        actual = parse_bool(streamlit_value(env, config, section, key))
        check_name = f"streamlit.{key}"
        if actual is expected:
            report.passed(check_name, f"Set to {str(expected).lower()}.")
        else:
            report.blocker(check_name, f"Must resolve to {str(expected).lower()}.")

    error_details = str(streamlit_value(env, config, "CLIENT", "showErrorDetails") or "").strip().lower()
    if error_details == "none":
        report.passed("streamlit.showErrorDetails", "Browser error details are disabled.")
    else:
        report.blocker("streamlit.showErrorDetails", "Must resolve to 'none' in production.")

    for key in ("maxUploadSize", "maxMessageSize"):
        raw_value = streamlit_value(env, config, "SERVER", key)
        try:
            size_mb = int(str(raw_value))
        except (TypeError, ValueError):
            report.blocker(f"streamlit.{key}", "Must be explicitly configured as an integer number of MB.")
            continue
        if not 1 <= size_mb <= 100:
            report.blocker(f"streamlit.{key}", "Must be between 1 and the M0 ceiling of 100 MB, pending policy approval.")
        else:
            report.passed(f"streamlit.{key}", "Explicit bounded value is configured; value withheld.")

    require_env(env, report, "STREAMLIT_SERVER_COOKIE_SECRET", "stable Streamlit cookie signing")


def check_database_environment(env: dict[str, str], report: Report) -> None:
    database_url = env.get("DATABASE_URL")
    if not is_real_value(database_url):
        report.blocker("database.url", "DATABASE_URL is missing or a placeholder; the app would fall back to SQLite.")
        return
    try:
        parsed = urlsplit(database_url)
    except ValueError:
        report.blocker("database.url", "DATABASE_URL is malformed; value withheld.")
        return
    if parsed.scheme not in {"postgres", "postgresql"}:
        report.blocker("database.url", "DATABASE_URL must use PostgreSQL, not SQLite or another scheme.")
    elif not parsed.hostname or not parsed.path.strip("/") or not parsed.username:
        report.blocker("database.url", "PostgreSQL URL lacks host/socket target, database name or user.")
    else:
        report.passed("database.url", "PostgreSQL URL structure is valid; credentials and host were withheld.")


def check_environment(env: dict[str, str], repo_root: Path, report: Report) -> None:
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

    debug_codes = parse_bool(env.get("LABCIM_AUTH_DEBUG_CODES"))
    if "LABCIM_AUTH_DEBUG_CODES" in env and debug_codes is False:
        report.passed("authentication.debug_codes", "Debug-code display is explicitly disabled.")
    else:
        report.blocker("authentication.debug_codes", "LABCIM_AUTH_DEBUG_CODES must be explicitly false.")

    if env.get("TZ") == EXPECTED_TIMEZONE:
        report.passed("process.timezone", f"Timezone is explicitly {EXPECTED_TIMEZONE}.")
    else:
        report.blocker("process.timezone", f"TZ must be {EXPECTED_TIMEZONE} while timestamps remain naive text.")

    storage_source = read_text(repo_root / "labcim_manager" / "storage.py")
    current_code_forces_r2 = "if database_url or database_url_configured()" in storage_source
    if current_code_forces_r2:
        for key in ("R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"):
            require_env(env, report, key, "R2 required by the current PostgreSQL upload path")
    else:
        report.warn("storage.contract", "Current code no longer matches the M0 R2-only production rule; review this checker for the selected backend.")


def check_manifest(repo_root: Path, report: Report) -> None:
    path = repo_root / "static" / "manifest.json"
    try:
        manifest = json.loads(read_text(path))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        report.blocker("subpath.manifest", f"PWA manifest cannot be read: {type(exc).__name__}.")
        return
    for key in ("start_url", "scope"):
        if manifest.get(key) == "/manager/":
            report.passed(f"subpath.manifest.{key}", "PWA value is scoped to /manager/.")
        else:
            report.blocker(f"subpath.manifest.{key}", "Must be exactly /manager/.")


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
    init_source = function_source(app_path, "ensure_database_initialized")
    if "init_db(" in init_source or "import_base_xlsx(" in init_source or "seed_default_pops(" in init_source:
        report.blocker("database.startup_mutation", "Startup still invokes schema/data initialization or seeding.")
    else:
        report.passed("database.startup_mutation", "No known schema/data mutation call remains in startup initialization.")

    if "https://labcim-manager.streamlit.app" in app_source:
        report.blocker("subpath.qr_default", "The legacy Streamlit Cloud URL remains in QR generation.")
    else:
        report.passed("subpath.qr_default", "Legacy Streamlit Cloud QR default is absent.")

    unrestricted_equipment_upload = re.search(
        r"file_uploader\(\s*[\"']Arquivo[\"']\s*,\s*key=",
        app_source,
    )
    if unrestricted_equipment_upload:
        report.blocker("uploads.equipment_allowlist", "Equipment document uploader still has no explicit type allowlist.")
    else:
        report.passed("uploads.equipment_allowlist", "Known unrestricted equipment uploader pattern is absent.")

    unsafe_blocks = app_source.count("unsafe_allow_html=True")
    if unsafe_blocks:
        report.warn("security.unsafe_html", f"{unsafe_blocks} unsafe HTML rendering call(s) require manual escaping review.")
    else:
        report.passed("security.unsafe_html", "No unsafe HTML rendering calls found.")


def check_migrations(repo_root: Path, report: Report) -> None:
    candidates = (repo_root / "migrations", repo_root / "alembic")
    has_migrations = any(path.is_dir() and any(item.is_file() for item in path.rglob("*")) for path in candidates)
    has_config = (repo_root / "alembic.ini").is_file()
    if has_migrations or has_config:
        report.passed("database.migrations", "A migration artifact exists; content still requires release review.")
    else:
        report.blocker("database.migrations", "No versioned database migration artifacts were found.")


def check_runtime(repo_root: Path, report: Report) -> None:
    if sys.version_info >= (3, 10):
        report.passed("runtime.python_current", "Current interpreter can parse the project's Python syntax.")
    else:
        report.blocker("runtime.python_current", "Python 3.10 or newer is required by current syntax.")

    version_files = (repo_root / ".python-version", repo_root / "runtime.txt")
    if any(path.is_file() and read_text(path).strip() for path in version_files):
        report.passed("runtime.python_declared", "Repository declares a Python runtime version.")
    else:
        report.blocker("runtime.python_declared", "Repository does not declare the production Python version.")

    requirements_path = repo_root / "requirements.txt"
    raw_requirement_lines: list[str] = []
    try:
        raw_requirement_lines = read_text(requirements_path).splitlines()
        requirement_lines = [
            line.strip()
            for line in raw_requirement_lines
            if line.strip() and not line.lstrip().startswith("#") and not line.lstrip().startswith("--hash")
        ]
    except (OSError, UnicodeError) as exc:
        report.blocker("runtime.dependencies", f"requirements.txt cannot be read: {type(exc).__name__}.")
        requirement_lines = []

    non_exact = [line for line in requirement_lines if "==" not in line]
    if requirement_lines and not non_exact:
        report.passed("runtime.dependencies", "All top-level requirements are exactly pinned.")
    else:
        report.blocker("runtime.dependencies", "Dependencies are absent or not all exactly pinned; use a reviewed lock with hashes.")
    if requirement_lines and any("--hash=" in line for line in raw_requirement_lines):
        report.passed("runtime.dependency_hashes", "Requirement hashes are present.")
    else:
        report.warn("runtime.dependency_hashes", "No requirement hashes were found.")

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
            report.blocker(f"runtime.import.{module}", "Required module is not importable in the current environment.")
            continue
        try:
            importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            report.warn(f"runtime.import.{module}", "Module imports but package metadata is unavailable.")
        else:
            report.passed(f"runtime.import.{module}", "Required module and package metadata are available.")


def check_required_files(repo_root: Path, report: Report) -> None:
    required = (
        "app.py",
        "requirements.txt",
        ".streamlit/config.toml",
        "labcim_manager/db.py",
        "labcim_manager/storage.py",
        "static/manifest.json",
        "docs/PRODUCTION_READINESS.md",
        "docs/UFRN_DEPLOYMENT_PLAN.md",
        "docs/DATABASE_MIGRATION_PLAN.md",
        "docs/FILE_STORAGE_MIGRATION_PLAN.md",
        "docs/PRODUCTION_ENV_TEMPLATE.md",
    )
    missing = [relative for relative in required if not (repo_root / relative).is_file()]
    if missing:
        report.blocker("repository.required_files", f"Missing {len(missing)} required file(s); names intentionally omitted from compact output.")
    else:
        report.passed("repository.required_files", "All required M0 files are present.")

    for secret_path in (repo_root / ".streamlit" / "secrets.toml", repo_root / ".env"):
        if secret_path.exists():
            report.warn("repository.local_secrets", "A local secret-bearing file exists; verify it is untracked and permission-restricted.")


def main() -> int:
    args = parse_args()
    report = Report()
    repo_root = args.repo_root.resolve()
    if not repo_root.is_dir():
        print("[BLOCKER] repository.root: Repository root is not a directory.")
        return 2

    env = load_env_file(args.env_file, report)
    check_required_files(repo_root, report)
    config = load_streamlit_config(repo_root, report)
    check_streamlit(env, config, report)
    check_environment(env, repo_root, report)
    check_manifest(repo_root, report)
    check_source_gates(repo_root, report)
    check_migrations(repo_root, report)
    check_runtime(repo_root, report)

    blockers, warnings, _ = report.render()
    if blockers:
        return 2
    if warnings and args.strict_warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
