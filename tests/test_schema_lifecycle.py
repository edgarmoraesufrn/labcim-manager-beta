from __future__ import annotations

import ast
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from labcim_manager.db import (
    connect,
    create_booking,
    create_equipment,
    create_project,
    create_supply,
    create_supply_movement,
    create_user,
    query_df,
    table_counts,
)
from labcim_manager.db_migrate import run as run_migration_cli
from labcim_manager.migrations import (
    v001_legacy_core,
    v002_approved_schema,
    v003_auth_abuse_protection,
)
from labcim_manager.schema import (
    LATEST_SCHEMA_VERSION,
    MIGRATION_TABLE,
    ExistingSchemaMismatchError,
    MigrationLockError,
    SchemaCompatibilityError,
    SchemaLifecycleError,
    SchemaState,
    baseline_existing_schema,
    initialize_schema,
    inspect_schema,
    migration_sql_for_dialect,
    structural_issues,
    upgrade_schema,
    verify_database_target,
    verify_schema_compatible,
    _begin_migration,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def create_legacy_snapshot(path: Path) -> None:
    raw = sqlite3.connect(path)
    try:
        raw.executescript(v001_legacy_core.SQL)
        raw.execute(
            "INSERT INTO equipment (equipment_code, equipment_name) VALUES ('EQ-LEGACY', 'Equipamento legado')"
        )
        raw.execute(
            "INSERT INTO users (full_name, email, role) VALUES ('Usuário legado', 'legacy@example.invalid', 'operator')"
        )
        raw.execute(
            "INSERT INTO projects (project_code, project_name) VALUES ('P-LEGACY', 'Projeto legado')"
        )
        raw.execute(
            "INSERT INTO supplies (supply_name, current_quantity) VALUES ('Insumo legado', 7.5)"
        )
        raw.execute(
            """
            INSERT INTO bookings (
                equipment_id, user_id, project_id, start_datetime, end_datetime, status
            ) VALUES (1, 1, 1, '2026-01-01T08:00:00', '2026-01-01T09:00:00', 'scheduled')
            """
        )
        raw.execute(
            """
            INSERT INTO supply_movements (
                supply_id, movement_type, movement_date, quantity, user_id, project_id
            ) VALUES (1, 'entry', '2026-01-01', 7.5, 1, 1)
            """
        )
        raw.commit()
    finally:
        raw.close()


class SchemaLifecycleTests(unittest.TestCase):
    def test_m1b_migration_checksums_are_immutable(self) -> None:
        from labcim_manager.schema import MIGRATIONS

        checksums = {migration.version: migration.checksum for migration in MIGRATIONS}
        self.assertEqual(
            checksums[1],
            "082096411bef0900a165e443b0efe8ffd61c9db4fa1718203d6cce001c447bf2",
        )
        self.assertEqual(
            checksums[2],
            "a07a72c9752d99324b0e8fbb07e510342e253b785da85f0fa74e06ae7981b8a0",
        )
        self.assertEqual(
            checksums[4],
            "71a3a63c959c0a310ac64c6cb403e310a8767db16e69d1531870cb5ff783a502",
        )

    def test_fresh_sqlite_initializes_to_current_schema_without_seed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fresh.db"
            conn = connect(path)
            try:
                status = initialize_schema(conn)
                self.assertTrue(status.compatible)
                self.assertEqual(status.current_version, LATEST_SCHEMA_VERSION)
                self.assertFalse(structural_issues(conn))
                self.assertEqual(sum(table_counts(conn).values()), 0)
            finally:
                conn.close()

    def test_workbook_seed_only_runs_through_explicit_admin_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "seed.db"
            workbook = root / "seed.xlsx"
            with pd.ExcelWriter(workbook) as writer:
                pd.DataFrame(
                    [{"equipment_code": "EQ-SEED", "equipment_name": "Equipamento seed"}]
                ).to_excel(writer, sheet_name="Equipamentos", index=False)
                pd.DataFrame(
                    [{"full_name": "Usuário seed", "email": "seed@example.invalid"}]
                ).to_excel(writer, sheet_name="Usuarios", index=False)
                pd.DataFrame(
                    [{"project_code": "P-SEED", "project_name": "Projeto seed"}]
                ).to_excel(writer, sheet_name="Projetos", index=False)

            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("DATABASE_URL", None)
                self.assertEqual(
                    run_migration_cli(["--sqlite-path", str(path), "initialize"]),
                    0,
                )
                before = connect(path, allow_create=False)
                try:
                    self.assertEqual(sum(table_counts(before).values()), 0)
                finally:
                    before.close()
                self.assertEqual(
                    run_migration_cli(
                        [
                            "--sqlite-path",
                            str(path),
                            "seed-base",
                            "--workbook",
                            str(workbook),
                        ]
                    ),
                    0,
                )

            seeded = connect(path, allow_create=False)
            try:
                counts = table_counts(seeded)
                self.assertEqual(counts["equipment"], 1)
                self.assertEqual(counts["users"], 1)
                self.assertEqual(counts["projects"], 1)
            finally:
                seeded.close()

    def test_fresh_schema_supports_core_user_booking_and_supply_operations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "operations.db"
            conn = connect(path)
            try:
                initialize_schema(conn)
                self.assertTrue(
                    create_equipment(
                        conn,
                        equipment_code="EQ-TEST",
                        equipment_name="Equipamento teste",
                        lab_unit=None,
                        location=None,
                        requires_operator=0,
                        responsible_name=None,
                        responsible_phone=None,
                        active=1,
                        operational_status="available",
                        unavailable_functions=None,
                        max_sample_capacity=None,
                        capacity_unit="amostras",
                        capacity_enforced=0,
                        technical_manager=None,
                        pop_title=None,
                        pop_path=None,
                        pop_version=None,
                        pop_updated_at=None,
                        pop_responsible=None,
                        document_notes=None,
                        notes=None,
                    )[0]
                )
                self.assertTrue(
                    create_user(
                        conn,
                        full_name="Usuário teste",
                        email="user@example.invalid",
                        phone_e164=None,
                        role="member",
                        lab_unit=None,
                        department=None,
                        advisor_name=None,
                        training_completed=1,
                        active=1,
                        notes=None,
                    )[0]
                )
                self.assertTrue(
                    create_project(
                        conn,
                        project_code="P-TEST",
                        project_name="Projeto teste",
                        funding_source=None,
                        start_date=None,
                        end_date=None,
                        active=1,
                        notes=None,
                    )[0]
                )
                ok, _message, booking_id = create_booking(
                    conn,
                    equipment_id=1,
                    user_id=1,
                    project_id=1,
                    operator_id=None,
                    start_iso="2026-08-12T08:00:00",
                    end_iso="2026-08-12T09:00:00",
                    sample_count=1,
                    purpose="Teste",
                )
                self.assertTrue(ok)
                self.assertIsNotNone(booking_id)
                supply_id = create_supply(
                    conn,
                    supply_type="Insumo",
                    supply_name="Insumo teste",
                    supply_code="S-TEST",
                    commercial_name=None,
                    manufacturer=None,
                    manufacturer_code=None,
                    category=None,
                    physical_state=None,
                    application_function=None,
                    addition_mode=None,
                    compatible_model_family=None,
                    unit="kg",
                    current_quantity=0,
                    minimum_quantity=0,
                    lot=None,
                    expiration_date=None,
                    location=None,
                    responsible_name=None,
                    safety_doc_path=None,
                    technical_doc_path=None,
                    density=None,
                    recommended_concentration=None,
                    recommended_temperature=None,
                    characterization_summary=None,
                    notes=None,
                )
                movement_ok, _message, movement_id = create_supply_movement(
                    conn,
                    supply_id=supply_id,
                    movement_type="entrada",
                    movement_date="2026-08-12",
                    quantity=2.5,
                    user_id=1,
                    project_id=1,
                    purpose="Teste",
                    document_path=None,
                )
                self.assertTrue(movement_ok)
                self.assertIsNotNone(movement_id)
                counts = table_counts(conn)
                self.assertEqual(counts["users"], 1)
                self.assertEqual(counts["bookings"], 1)
                self.assertEqual(counts["supplies"], 1)
                self.assertEqual(counts["supply_movements"], 1)
                self.assertEqual(
                    float(query_df(conn, "SELECT current_quantity FROM supplies").iloc[0]["current_quantity"]),
                    2.5,
                )
            finally:
                conn.close()

    def test_historical_snapshot_requires_adoption_then_upgrades_without_data_loss(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.db"
            create_legacy_snapshot(path)
            conn = connect(path)
            try:
                self.assertEqual(inspect_schema(conn).state, SchemaState.UNVERSIONED)
                adopted = baseline_existing_schema(conn, confirmed=True)
                self.assertEqual(adopted.state, SchemaState.BEHIND)
                self.assertEqual(adopted.current_version, 1)
                status = upgrade_schema(conn)
                self.assertTrue(status.compatible)
                self.assertEqual(
                    conn.execute("SELECT equipment_name FROM equipment WHERE id=1").fetchone()["equipment_name"],
                    "Equipamento legado",
                )
                self.assertEqual(
                    conn.execute("SELECT role FROM users WHERE id=1").fetchone()["role"],
                    "operator",
                )
                self.assertEqual(
                    float(conn.execute("SELECT current_quantity FROM supplies WHERE id=1").fetchone()["current_quantity"]),
                    7.5,
                )
                self.assertEqual(conn.execute("SELECT COUNT(*) AS n FROM bookings").fetchone()["n"], 1)
                self.assertEqual(conn.execute("SELECT COUNT(*) AS n FROM supply_movements").fetchone()["n"], 1)
            finally:
                conn.close()

    def test_current_schema_startup_verification_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "current.db"
            conn = connect(path)
            try:
                initialize_schema(conn)
                before = conn.raw_conn.total_changes
                status = verify_schema_compatible(conn)
                after = conn.raw_conn.total_changes
                self.assertTrue(status.compatible)
                self.assertEqual(before, after)
            finally:
                conn.close()

    def test_web_startup_only_opens_and_verifies_the_database(self) -> None:
        source = (REPO_ROOT / "app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        node = next(
            item
            for item in tree.body
            if isinstance(item, ast.FunctionDef) and item.name == "ensure_database_compatible"
        )
        startup_source = ast.get_source_segment(source, node) or ""
        self.assertIn("verify_database_target", startup_source)
        for forbidden in (
            "init_db(",
            "import_base_xlsx(",
            "seed_default_pops(",
            "ALTER TABLE",
            "CREATE INDEX",
            "UPDATE ",
        ):
            self.assertNotIn(forbidden, startup_source)

    def test_actual_web_database_gate_accepts_current_and_refuses_old_or_future(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            current_path = root / "current.db"
            current = connect(current_path)
            initialize_schema(current)
            current.close()
            self.assertTrue(verify_database_target(str(current_path)).compatible)

            behind_path = root / "behind.db"
            create_legacy_snapshot(behind_path)
            behind = connect(behind_path)
            baseline_existing_schema(behind, confirmed=True)
            behind.close()
            with self.assertRaises(SchemaCompatibilityError):
                verify_database_target(str(behind_path))

            future_path = root / "future.db"
            future = connect(future_path)
            initialize_schema(future)
            future.execute(
                f"INSERT INTO {MIGRATION_TABLE} (version, name, checksum) "
                "VALUES (999, 'future', 'future')"
            )
            future.commit()
            future.close()
            with self.assertRaises(SchemaCompatibilityError):
                verify_database_target(str(future_path))

    def test_behind_and_future_schema_are_refused_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            behind_path = Path(directory) / "behind.db"
            create_legacy_snapshot(behind_path)
            behind = connect(behind_path)
            try:
                baseline_existing_schema(behind, confirmed=True)
                before = behind.raw_conn.total_changes
                with self.assertRaises(SchemaCompatibilityError):
                    verify_schema_compatible(behind)
                self.assertEqual(before, behind.raw_conn.total_changes)
                self.assertNotIn("project_services", {
                    row["name"]
                    for row in behind.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                })
            finally:
                behind.close()

            future_path = Path(directory) / "future.db"
            future = connect(future_path)
            try:
                initialize_schema(future)
                future.execute(
                    f"INSERT INTO {MIGRATION_TABLE} (version, name, checksum) VALUES (999, 'future', 'future')"
                )
                future.commit()
                self.assertEqual(inspect_schema(future).state, SchemaState.AHEAD)
                with self.assertRaises(SchemaCompatibilityError):
                    verify_schema_compatible(future)
            finally:
                future.close()

    def test_corrupt_migration_metadata_is_unknown_and_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unknown.db"
            conn = connect(path)
            try:
                initialize_schema(conn)
                conn.execute(
                    f"UPDATE {MIGRATION_TABLE} SET checksum = 'tampered' WHERE version = 2"
                )
                conn.commit()
                before = conn.raw_conn.total_changes
                status = inspect_schema(conn)
                self.assertEqual(status.state, SchemaState.UNKNOWN)
                self.assertTrue(any("checksum" in issue for issue in status.issues))
                with self.assertRaises(SchemaCompatibilityError):
                    verify_schema_compatible(conn)
                self.assertEqual(before, conn.raw_conn.total_changes)
            finally:
                conn.close()

    def test_empty_production_target_is_not_created_by_startup_connection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.db"
            with self.assertRaises(FileNotFoundError):
                connect(path, allow_create=False)
            self.assertFalse(path.exists())

    def test_arbitrary_or_partial_schema_cannot_be_baselined(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "arbitrary.db"
            raw = sqlite3.connect(path)
            raw.execute("CREATE TABLE equipment (id INTEGER PRIMARY KEY, equipment_code TEXT)")
            raw.commit()
            raw.close()
            conn = connect(path)
            try:
                with self.assertRaises(ExistingSchemaMismatchError):
                    baseline_existing_schema(conn, confirmed=True)
                self.assertNotIn(MIGRATION_TABLE, {
                    row["name"]
                    for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                })
            finally:
                conn.close()

    def test_baseline_rejects_incompatible_critical_column_type(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wrong-type.db"
            raw = sqlite3.connect(path)
            raw.executescript(
                v001_legacy_core.SQL.replace(
                    "id INTEGER PRIMARY KEY AUTOINCREMENT",
                    "id TEXT PRIMARY KEY",
                    1,
                )
            )
            raw.commit()
            raw.close()
            conn = connect(path)
            try:
                with self.assertRaises(ExistingSchemaMismatchError) as context:
                    baseline_existing_schema(conn, confirmed=True)
                self.assertIn("tipo incompatível em equipment.id", str(context.exception))
                self.assertNotIn(MIGRATION_TABLE, {
                    row["name"]
                    for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                })
            finally:
                conn.close()

    def test_baseline_requires_explicit_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.db"
            create_legacy_snapshot(path)
            conn = connect(path)
            try:
                with self.assertRaises(ExistingSchemaMismatchError) as context:
                    baseline_existing_schema(conn)
                self.assertIn("confirmação explícita", str(context.exception))
                self.assertNotIn(MIGRATION_TABLE, {
                    row["name"]
                    for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                })
            finally:
                conn.close()

    def test_current_unversioned_snapshot_is_adopted_without_schema_or_data_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "restored-current.db"
            conn = connect(path)
            try:
                initialize_schema(conn)
                conn.execute(
                    "INSERT INTO equipment (equipment_code, equipment_name) "
                    "VALUES ('EQ-RESTORE', 'Equipamento restaurado')"
                )
                conn.execute(f"DROP TABLE {MIGRATION_TABLE}")
                conn.commit()
                before_tables = {
                    row["name"]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    ).fetchall()
                }
                before_changes = conn.raw_conn.total_changes
                status = baseline_existing_schema(conn, confirmed=True)
                after_tables = {
                    row["name"]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    ).fetchall()
                }
                self.assertTrue(status.compatible)
                self.assertEqual(status.current_version, LATEST_SCHEMA_VERSION)
                self.assertEqual(after_tables - before_tables, {MIGRATION_TABLE})
                self.assertEqual(
                    conn.execute("SELECT equipment_name FROM equipment").fetchone()["equipment_name"],
                    "Equipamento restaurado",
                )
                self.assertEqual(
                    conn.raw_conn.total_changes - before_changes,
                    LATEST_SCHEMA_VERSION,
                )
            finally:
                conn.close()

    def test_unversioned_v2_snapshot_is_adopted_then_upgraded_to_current(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "restored-v2.db"
            conn = connect(path)
            try:
                initialize_schema(conn)
                conn.execute(
                    "INSERT INTO users (full_name, email, role) VALUES ('V2 User', 'v2@example.invalid', 'member')"
                )
                conn.execute("DROP TABLE auth_rate_limit_events")
                conn.execute(f"DROP TABLE {MIGRATION_TABLE}")
                conn.commit()

                adopted = baseline_existing_schema(conn, confirmed=True)
                self.assertEqual(adopted.state, SchemaState.BEHIND)
                self.assertEqual(adopted.current_version, 2)
                self.assertEqual(adopted.pending_versions, (3, 4))
                current = upgrade_schema(conn)
                self.assertTrue(current.compatible)
                self.assertEqual(current.current_version, 4)
                self.assertEqual(
                    conn.execute("SELECT full_name FROM users").fetchone()["full_name"],
                    "V2 User",
                )
            finally:
                conn.close()

    def test_version_three_upgrades_to_v4_and_normalizes_supply_active(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "v3-to-v4.db"
            conn = connect(path)
            try:
                initialize_schema(conn)
                supply_id = create_supply(
                    conn,
                    supply_type="Insumo",
                    supply_name="Normalização v4",
                    supply_code=None,
                    commercial_name=None,
                    manufacturer=None,
                    manufacturer_code=None,
                    category=None,
                    physical_state=None,
                    application_function=None,
                    addition_mode=None,
                    compatible_model_family=None,
                    unit="kg",
                    current_quantity=0,
                    minimum_quantity=0,
                    lot=None,
                    expiration_date=None,
                    location=None,
                    responsible_name=None,
                    safety_doc_path=None,
                    technical_doc_path=None,
                    density=None,
                    recommended_concentration=None,
                    recommended_temperature=None,
                    characterization_summary=None,
                    notes=None,
                )
                conn.execute("UPDATE supplies SET active = NULL WHERE id = ?", [supply_id])
                conn.execute(f"DELETE FROM {MIGRATION_TABLE} WHERE version = 4")
                conn.commit()

                before = inspect_schema(conn)
                self.assertEqual(before.state, SchemaState.BEHIND)
                self.assertEqual(before.current_version, 3)
                self.assertEqual(before.pending_versions, (4,))

                current = upgrade_schema(conn)
                self.assertTrue(current.compatible)
                self.assertEqual(current.current_version, 4)
                row = conn.execute(
                    """
                    SELECT active, inactive_reason, inactive_by_id, inactive_at
                    FROM supplies
                    WHERE id = ?
                    """,
                    [supply_id],
                ).fetchone()
                self.assertEqual(int(row["active"]), 1)
                self.assertIsNone(row["inactive_reason"])
                self.assertIsNone(row["inactive_by_id"])
                self.assertIsNone(row["inactive_at"])
            finally:
                conn.close()

    def test_failed_migration_rolls_back_and_retry_is_safe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "retry.db"
            conn = connect(path)
            try:
                # Patch at a smaller seam so SQLite can prove DDL rollback.
                with patch("labcim_manager.schema._record_migration", side_effect=RuntimeError("synthetic record failure")):
                    with self.assertRaises(RuntimeError):
                        upgrade_schema(conn)
                self.assertEqual(inspect_schema(conn).state, SchemaState.MISSING)
                self.assertTrue(upgrade_schema(conn).compatible)
            finally:
                conn.close()

    def test_sqlite_concurrent_upgrade_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "locked.db"
            first = connect(path)
            second = connect(path)
            try:
                first.raw_conn.execute("BEGIN IMMEDIATE")
                with self.assertRaises(MigrationLockError):
                    upgrade_schema(second)
            finally:
                first.rollback()
                first.close()
                second.close()

    def test_postgresql_advisory_lock_conflict_is_rejected(self) -> None:
        class Cursor:
            @staticmethod
            def fetchone():
                return {"acquired": False}

        class PostgreSQLConnection:
            dialect = "postgres"

            @staticmethod
            def execute(sql, params):
                self.assertIn("pg_try_advisory_xact_lock", sql)
                self.assertEqual(len(params), 1)
                return Cursor()

        with self.assertRaises(MigrationLockError):
            _begin_migration(PostgreSQLConnection())

    def test_migration_cli_does_not_print_database_url_secret(self) -> None:
        sentinel = "migration-secret-sentinel-4317"
        environment = dict(os.environ)
        environment["DATABASE_URL"] = (
            f"postgresql://user:{sentinel}@127.0.0.1:1/labcim?connect_timeout=1"
        )
        result = subprocess.run(
            [sys.executable, "-m", "labcim_manager.db_migrate", "status"],
            cwd=REPO_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
        output = result.stdout + result.stderr
        self.assertNotIn(sentinel, output)
        self.assertNotIn("postgresql://", output)

    def test_postgresql_ddl_translation_is_deterministic(self) -> None:
        legacy_sql = migration_sql_for_dialect(v001_legacy_core.SQL, "postgres")
        self.assertNotIn("AUTOINCREMENT", legacy_sql)
        self.assertIn("GENERATED BY DEFAULT AS IDENTITY", legacy_sql)
        self.assertIn("DOUBLE PRECISION", migration_sql_for_dialect("cost REAL", "postgres"))
        approved_sql = migration_sql_for_dialect(
            v002_approved_schema.NEW_TABLES_SQL,
            "postgres",
        )
        self.assertNotIn("AUTOINCREMENT", approved_sql)
        self.assertNotIn(" REAL", approved_sql)
        self.assertIn("DOUBLE PRECISION", approved_sql)
        auth_sql = migration_sql_for_dialect(v003_auth_abuse_protection.SQL, "postgres")
        self.assertNotIn("AUTOINCREMENT", auth_sql)
        self.assertIn("GENERATED BY DEFAULT AS IDENTITY", auth_sql)
        self.assertIn("idx_auth_rate_identity_event_time", auth_sql)


if __name__ == "__main__":
    unittest.main()
