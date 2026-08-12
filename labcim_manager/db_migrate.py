from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from labcim_manager.config import PROJECT_ROOT
from labcim_manager.db import connect, import_base_xlsx, is_operational_database_empty, seed_default_pops
from labcim_manager.schema import (
    ExistingSchemaMismatchError,
    LATEST_SCHEMA_VERSION,
    SchemaLifecycleError,
    SchemaState,
    baseline_existing_schema,
    initialize_schema,
    inspect_schema,
    upgrade_schema,
    verify_schema_compatible,
)


DEFAULT_SQLITE_PATH = PROJECT_ROOT / "data" / "labcim_manager.db"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Administrate the LabCim Manager schema without launching Streamlit.",
    )
    parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=DEFAULT_SQLITE_PATH,
        help="SQLite path used only when DATABASE_URL is absent.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("status", "verify", "upgrade", "initialize"):
        subparsers.add_parser(command)
    baseline = subparsers.add_parser("baseline-existing")
    baseline.add_argument(
        "--confirm-compatible-schema",
        action="store_true",
        help="Write version metadata after structural validation succeeds.",
    )
    seed_base = subparsers.add_parser("seed-base")
    seed_base.add_argument("--workbook", type=Path, default=PROJECT_ROOT / "data" / "LabCim_Base.xlsx")
    seed_base.add_argument(
        "--allow-nonempty",
        action="store_true",
        help="Allow explicit upsert into a non-empty database.",
    )
    subparsers.add_parser("seed-pops")
    return parser.parse_args(argv)


def _database_url() -> str | None:
    value = os.environ.get("DATABASE_URL")
    return value.strip() if value and value.strip() else None


def _target_exists(sqlite_path: Path, database_url: str | None) -> bool:
    return bool(database_url or sqlite_path.is_file())


def _connect(args: argparse.Namespace, *, allow_create: bool) -> object:
    return connect(
        args.sqlite_path,
        database_url=_database_url(),
        allow_create=allow_create,
    )


def _print_status(status) -> None:
    current = "none" if status.current_version is None else str(status.current_version)
    pending = ",".join(str(version) for version in status.pending_versions) or "none"
    print(f"state={status.state.value}")
    print(f"current_version={current}")
    print(f"expected_version={status.expected_version}")
    print(f"pending_versions={pending}")
    if status.issues:
        print(f"issues={len(status.issues)}")
        for position, issue in enumerate(status.issues, start=1):
            print(f"issue_{position}={issue}")


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    database_url = _database_url()
    if args.command in {"status", "verify"} and not _target_exists(args.sqlite_path, database_url):
        print("state=missing")
        print("current_version=none")
        print(f"expected_version={LATEST_SCHEMA_VERSION}")
        print(f"pending_versions={','.join(str(version) for version in range(1, LATEST_SCHEMA_VERSION + 1))}")
        return 1

    allow_create = args.command in {"initialize", "upgrade"}
    conn = _connect(args, allow_create=allow_create)
    try:
        if args.command == "status":
            status = inspect_schema(conn)
            _print_status(status)
            return 0 if status.compatible else 1
        if args.command == "verify":
            status = verify_schema_compatible(conn)
            _print_status(status)
            return 0
        if args.command == "initialize":
            status = initialize_schema(conn)
            _print_status(status)
            return 0
        if args.command == "upgrade":
            status = upgrade_schema(conn)
            _print_status(status)
            return 0
        if args.command == "baseline-existing":
            status = baseline_existing_schema(
                conn,
                confirmed=args.confirm_compatible_schema,
            )
            _print_status(status)
            return 0
        if args.command == "seed-base":
            verify_schema_compatible(conn)
            if not args.workbook.is_file():
                raise SchemaLifecycleError("Workbook de seed não encontrado.")
            if not args.allow_nonempty and not is_operational_database_empty(conn):
                raise SchemaLifecycleError(
                    "Seed recusado: banco operacional não está vazio. Use confirmação explícita para upsert."
                )
            counts = import_base_xlsx(conn, args.workbook)
            print(
                "seeded="
                + ",".join(f"{key}:{int(value)}" for key, value in sorted(counts.items()))
            )
            return 0
        if args.command == "seed-pops":
            verify_schema_compatible(conn)
            print(f"updated={seed_default_pops(conn)}")
            return 0
    finally:
        conn.close()
    return 2


def main() -> int:
    try:
        return run()
    except (SchemaLifecycleError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: database operation failed ({type(exc).__name__}).", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
