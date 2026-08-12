from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import sqlite3
from labcim_manager.db import DatabaseConnection, _execute_script, _postgres_schema, db_backend
from labcim_manager.migrations import v001_legacy_core, v002_approved_schema


MIGRATION_TABLE = "labcim_schema_migrations"
POSTGRES_MIGRATION_LOCK_ID = 4_521_019_027


class SchemaState(str, Enum):
    MISSING = "missing"
    UNVERSIONED = "unversioned"
    CURRENT = "current"
    BEHIND = "behind"
    AHEAD = "ahead"
    UNKNOWN = "unknown"


class SchemaLifecycleError(RuntimeError):
    """Base error for explicit database lifecycle operations."""


class SchemaCompatibilityError(SchemaLifecycleError):
    """Raised when the web process cannot safely use the selected database."""


class MigrationLockError(SchemaLifecycleError):
    """Raised when another process holds the schema migration lock."""


class ExistingSchemaMismatchError(SchemaLifecycleError):
    """Raised when an unversioned schema cannot be safely adopted."""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    checksum: str


@dataclass(frozen=True)
class SchemaStatus:
    state: SchemaState
    current_version: int | None
    expected_version: int
    pending_versions: tuple[int, ...]
    issues: tuple[str, ...] = ()

    @property
    def compatible(self) -> bool:
        return self.state is SchemaState.CURRENT and not self.issues


def _migration_payload(version: int) -> str:
    if version == v001_legacy_core.VERSION:
        return v001_legacy_core.SQL
    if version == v002_approved_schema.VERSION:
        return "\n".join(
            (
                v002_approved_schema.NEW_TABLES_SQL,
                repr(v002_approved_schema.COLUMN_ADDITIONS),
                v002_approved_schema.INDEX_SQL,
            )
        )
    raise ValueError(f"Versão de migration desconhecida: {version}.")


def _migration(version: int, name: str) -> Migration:
    payload = f"{version}:{name}\n{_migration_payload(version)}"
    return Migration(version, name, hashlib.sha256(payload.encode("utf-8")).hexdigest())


MIGRATIONS: tuple[Migration, ...] = (
    _migration(v001_legacy_core.VERSION, v001_legacy_core.NAME),
    _migration(v002_approved_schema.VERSION, v002_approved_schema.NAME),
)
LATEST_SCHEMA_VERSION = MIGRATIONS[-1].version


LEGACY_TABLE_COLUMNS: dict[str, frozenset[str]] = {
    "equipment": frozenset(
        {
            "id", "equipment_code", "equipment_name", "lab_unit", "location",
            "requires_operator", "responsible_name", "responsible_phone", "active",
            "operational_status", "unavailable_functions", "max_sample_capacity",
            "capacity_unit", "capacity_enforced", "technical_manager", "pop_title",
            "pop_path", "pop_version", "pop_updated_at", "pop_responsible",
            "document_notes", "notes", "created_at", "updated_at",
        }
    ),
    "users": frozenset(
        {
            "id", "full_name", "email", "phone_e164", "role", "lab_unit",
            "department", "advisor_name", "training_completed", "active", "notes",
            "created_at", "updated_at",
        }
    ),
    "projects": frozenset(
        {
            "id", "project_code", "project_name", "funding_source", "start_date",
            "end_date", "active", "notes", "created_at", "updated_at",
        }
    ),
    "bookings": frozenset(
        {
            "id", "equipment_id", "user_id", "project_id", "operator_id",
            "performed_by_id", "start_datetime", "end_datetime", "sample_count",
            "purpose", "status", "created_at", "updated_at",
        }
    ),
    "maintenance_preventive": frozenset(
        {
            "id", "equipment_id", "activity_type", "description", "periodicity",
            "planned_date", "planned_end_date", "performed_date", "execution_time",
            "checklist_path", "internal_responsible", "external_supplier",
            "supplier_contact", "service_order", "status", "certificate_path",
            "observations", "next_date", "blocks_booking", "notify_internal",
            "notify_manager", "notify_supplier", "notify_users", "created_at", "updated_at",
        }
    ),
    "maintenance_corrective": frozenset(
        {
            "id", "equipment_id", "reporter_id", "title", "description",
            "occurrence_datetime", "impact", "priority", "attachment_path", "assigned_to",
            "initial_diagnosis", "probable_cause", "operator_trained",
            "external_supplier_needed", "corrective_action", "replaced_parts", "costs",
            "downtime_hours", "conclusion_date", "status", "notify_technical",
            "notify_manager", "notify_supplier", "notify_reporter", "created_at", "updated_at",
        }
    ),
    "supplies": frozenset(
        {
            "id", "supply_name", "commercial_name", "manufacturer", "category",
            "physical_state", "application_function", "addition_mode", "unit",
            "current_quantity", "minimum_quantity", "lot", "expiration_date", "location",
            "responsible_name", "safety_doc_path", "technical_doc_path", "density",
            "recommended_concentration", "recommended_temperature", "characterization_summary",
            "active", "notes", "created_at", "updated_at",
        }
    ),
    "supply_movements": frozenset(
        {
            "id", "supply_id", "movement_type", "movement_date", "quantity", "unit",
            "user_id", "project_id", "purpose", "document_path", "created_at",
        }
    ),
    "access_codes": frozenset(
        {"id", "user_id", "email", "code_hash", "expires_at", "used_at", "attempts", "created_at"}
    ),
    "notification_log": frozenset(
        {
            "id", "event_type", "recipient_email", "subject", "body", "status",
            "error_message", "related_table", "related_id", "created_at",
        }
    ),
}


CURRENT_TABLE_COLUMNS: dict[str, frozenset[str]] = dict(LEGACY_TABLE_COLUMNS)
for _table, _column, _definition in v002_approved_schema.COLUMN_ADDITIONS:
    CURRENT_TABLE_COLUMNS[_table] = CURRENT_TABLE_COLUMNS[_table] | {_column}
CURRENT_TABLE_COLUMNS.update(
    {
        "project_services": frozenset(
            {
                "id", "project_id", "service_code", "title", "service_type", "requester_id",
                "responsible_id", "status", "requested_date", "expected_date", "completed_date",
                "notes", "active", "created_at", "updated_at",
            }
        ),
        "booking_status_history": frozenset(
            {
                "id", "booking_id", "previous_status", "new_status", "changed_by_id",
                "changed_at", "reason", "source", "created_at",
            }
        ),
        "maintenance_status_history": frozenset(
            {
                "id", "entity_type", "entity_id", "previous_status", "new_status",
                "justification", "changed_by_id", "changed_at",
            }
        ),
        "supply_lots": frozenset(
            {
                "id", "supply_id", "lot_code", "expiration_date", "received_date",
                "supplier_name", "initial_quantity", "current_quantity", "unit", "location",
                "certificate_path", "notes", "is_active", "created_at", "updated_at",
            }
        ),
        "equipment_spare_parts": frozenset(
            {
                "id", "equipment_id", "supply_id", "notes", "is_active", "created_at", "updated_at",
            }
        ),
        "attachments": frozenset(
            {
                "id", "entity_type", "entity_id", "attachment_role", "original_filename",
                "storage_key", "storage_backend", "mime_type", "file_size", "sha256",
                "uploaded_by_id", "uploaded_at", "notes", "is_active",
            }
        ),
    }
)


CURRENT_INDEXES = frozenset(
    {
        "idx_project_services_project", "idx_project_services_code",
        "idx_maintenance_status_history_entity", "idx_supply_lots_supply_active_expiration",
        "idx_supply_lots_code", "idx_supply_movements_supply_date",
        "idx_equipment_spare_parts_equipment", "idx_equipment_spare_parts_supply",
        "idx_attachments_entity", "idx_attachments_sha256", "idx_bookings_service",
        "idx_supply_movements_service", "idx_supply_movements_lot",
        "idx_bookings_equipment_period_status", "idx_bookings_start_datetime",
        "idx_booking_status_history_booking_changed", "idx_booking_status_history_changed_at",
        "idx_booking_status_history_changed_by", "idx_supply_movements_movement_date",
        "idx_supply_movements_project_service_date", "idx_supply_movements_lot_date",
        "idx_supply_lots_active_expiration", "idx_attachments_entity_role_active",
    }
)


CRITICAL_COLUMN_TYPES: dict[tuple[str, str], str] = {
    ("equipment", "id"): "integer",
    ("equipment", "equipment_code"): "text",
    ("users", "id"): "integer",
    ("users", "email"): "text",
    ("projects", "id"): "integer",
    ("project_services", "id"): "integer",
    ("bookings", "id"): "integer",
    ("bookings", "equipment_id"): "integer",
    ("maintenance_preventive", "id"): "integer",
    ("maintenance_corrective", "id"): "integer",
    ("maintenance_status_history", "id"): "integer",
    ("supplies", "id"): "integer",
    ("supplies", "current_quantity"): "real",
    ("supply_lots", "id"): "integer",
    ("supply_lots", "current_quantity"): "real",
    ("supply_movements", "id"): "integer",
    ("supply_movements", "quantity"): "real",
    ("equipment_spare_parts", "id"): "integer",
    ("attachments", "id"): "integer",
    ("attachments", "storage_key"): "text",
    ("access_codes", "id"): "integer",
    ("notification_log", "id"): "integer",
}


def migration_sql_for_dialect(sql: str, dialect: str) -> str:
    return _postgres_schema(sql) if dialect == "postgres" else sql


def _table_names(conn: DatabaseConnection) -> set[str]:
    if db_backend(conn) == "sqlite":
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        return {str(row["name"]) for row in rows}
    rows = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()"
    ).fetchall()
    return {str(row["table_name"]) for row in rows}


def _column_names(conn: DatabaseConnection, table: str) -> set[str]:
    if db_backend(conn) == "sqlite":
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return {str(row["name"]) for row in rows}
    rows = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema() AND table_name = ?
        """,
        [table],
    ).fetchall()
    return {str(row["column_name"]) for row in rows}


def _column_types(conn: DatabaseConnection, table: str) -> dict[str, str]:
    if db_backend(conn) == "sqlite":
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return {str(row["name"]): str(row["type"]).strip().lower() for row in rows}
    rows = conn.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = current_schema() AND table_name = ?
        """,
        [table],
    ).fetchall()
    return {str(row["column_name"]): str(row["data_type"]).strip().lower() for row in rows}


def _type_matches(actual: str, expected: str) -> bool:
    aliases = {
        "integer": {"integer"},
        "text": {"text"},
        "real": {"real", "double precision"},
    }
    return actual in aliases[expected]


def _index_names(conn: DatabaseConnection) -> set[str]:
    if db_backend(conn) == "sqlite":
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        return {str(row["name"]) for row in rows}
    rows = conn.execute(
        "SELECT indexname FROM pg_indexes WHERE schemaname = current_schema()"
    ).fetchall()
    return {str(row["indexname"]) for row in rows}


def structural_issues(conn: DatabaseConnection, version: int = LATEST_SCHEMA_VERSION) -> tuple[str, ...]:
    contract = LEGACY_TABLE_COLUMNS if version == 1 else CURRENT_TABLE_COLUMNS
    tables = _table_names(conn)
    issues: list[str] = []
    for table, expected_columns in contract.items():
        if table not in tables:
            issues.append(f"tabela ausente: {table}")
            continue
        missing_columns = sorted(expected_columns - _column_names(conn, table))
        if missing_columns:
            issues.append(f"colunas ausentes em {table}: {', '.join(missing_columns)}")
    for (table, column), expected_type in CRITICAL_COLUMN_TYPES.items():
        if table not in contract or table not in tables or column not in contract[table]:
            continue
        actual_type = _column_types(conn, table).get(column, "")
        if not _type_matches(actual_type, expected_type):
            issues.append(
                f"tipo incompatível em {table}.{column}: esperado {expected_type}"
            )
    if version >= LATEST_SCHEMA_VERSION:
        missing_indexes = sorted(CURRENT_INDEXES - _index_names(conn))
        if missing_indexes:
            issues.append(f"índices ausentes: {', '.join(missing_indexes)}")
    return tuple(issues)


def _migration_rows(conn: DatabaseConnection) -> list[dict[str, object]]:
    rows = conn.execute(
        f"SELECT version, name, checksum FROM {MIGRATION_TABLE} ORDER BY version"
    ).fetchall()
    return [dict(row) for row in rows]


def inspect_schema(conn: DatabaseConnection) -> SchemaStatus:
    try:
        tables = _table_names(conn)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return SchemaStatus(
            SchemaState.UNKNOWN,
            None,
            LATEST_SCHEMA_VERSION,
            (),
            ("schema ilegível ou corrompido",),
        )
    if not tables:
        return SchemaStatus(
            SchemaState.MISSING,
            None,
            LATEST_SCHEMA_VERSION,
            tuple(migration.version for migration in MIGRATIONS),
        )
    if MIGRATION_TABLE not in tables:
        return SchemaStatus(
            SchemaState.UNVERSIONED,
            None,
            LATEST_SCHEMA_VERSION,
            (),
            ("schema existente sem metadados de versão",),
        )

    try:
        rows = _migration_rows(conn)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return SchemaStatus(
            SchemaState.UNKNOWN,
            None,
            LATEST_SCHEMA_VERSION,
            (),
            ("metadados de migrations ilegíveis ou corrompidos",),
        )
    if not rows:
        return SchemaStatus(
            SchemaState.UNKNOWN,
            None,
            LATEST_SCHEMA_VERSION,
            (),
            ("tabela de migrations existe, mas não possui versões aplicadas",),
        )
    try:
        versions = [int(row["version"]) for row in rows]
    except (KeyError, TypeError, ValueError):
        return SchemaStatus(
            SchemaState.UNKNOWN,
            None,
            LATEST_SCHEMA_VERSION,
            (),
            ("versões de migration inválidas",),
        )
    current = max(versions)
    if current > LATEST_SCHEMA_VERSION:
        return SchemaStatus(SchemaState.AHEAD, current, LATEST_SCHEMA_VERSION, ())

    expected_prefix = list(range(1, current + 1))
    issues: list[str] = []
    if versions != expected_prefix:
        issues.append("histórico de migrations não é contínuo")
    by_version = {migration.version: migration for migration in MIGRATIONS}
    for row in rows:
        version = int(row["version"])
        expected = by_version.get(version)
        if expected is None:
            issues.append(f"migration desconhecida: {version}")
        elif row["name"] != expected.name or row["checksum"] != expected.checksum:
            issues.append(f"metadados/checksum divergentes na migration {version}")
    issues.extend(structural_issues(conn, version=current))
    if issues:
        return SchemaStatus(
            SchemaState.UNKNOWN,
            current,
            LATEST_SCHEMA_VERSION,
            (),
            tuple(issues),
        )

    pending = tuple(migration.version for migration in MIGRATIONS if migration.version > current)
    state = SchemaState.CURRENT if not pending else SchemaState.BEHIND
    return SchemaStatus(state, current, LATEST_SCHEMA_VERSION, pending)


def verify_schema_compatible(conn: DatabaseConnection) -> SchemaStatus:
    status = inspect_schema(conn)
    if not status.compatible:
        raise SchemaCompatibilityError(
            "Database schema is not compatible with this LabCim Manager release. "
            "Run the documented migration procedure."
        )
    return status


def verify_database_target(
    path: str,
    database_url: str | None = None,
) -> SchemaStatus:
    """Open an existing target, verify it read-only, and always close the connection."""

    from labcim_manager.db import connect

    conn = connect(path, database_url=database_url, allow_create=False)
    try:
        return verify_schema_compatible(conn)
    finally:
        conn.close()


def _create_migration_table(conn: DatabaseConnection) -> None:
    sql = f"""
    CREATE TABLE IF NOT EXISTS {MIGRATION_TABLE} (
        version INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        checksum TEXT NOT NULL,
        applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
    conn.execute(migration_sql_for_dialect(sql, db_backend(conn)))


def _begin_migration(conn: DatabaseConnection) -> None:
    if db_backend(conn) == "sqlite":
        try:
            conn.raw_conn.execute("PRAGMA busy_timeout = 0")
            conn.raw_conn.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            raise MigrationLockError("Outro processo está usando o lock de migration SQLite.") from exc
        return
    row = conn.execute(
        "SELECT pg_try_advisory_xact_lock(?) AS acquired",
        [POSTGRES_MIGRATION_LOCK_ID],
    ).fetchone()
    if not row or not bool(row["acquired"]):
        raise MigrationLockError("Outro processo está executando migrations PostgreSQL.")


def _add_column(conn: DatabaseConnection, table: str, column: str, definition: str) -> None:
    if column not in _column_names(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _apply_migration(conn: DatabaseConnection, migration: Migration) -> None:
    if migration.version == 1:
        _execute_script(conn, migration_sql_for_dialect(v001_legacy_core.SQL, db_backend(conn)))
        return
    if migration.version == 2:
        _execute_script(
            conn,
            migration_sql_for_dialect(v002_approved_schema.NEW_TABLES_SQL, db_backend(conn)),
        )
        for table, column, definition in v002_approved_schema.COLUMN_ADDITIONS:
            _add_column(conn, table, column, definition)
        _execute_script(conn, v002_approved_schema.INDEX_SQL)
        return
    raise SchemaLifecycleError(f"Migration sem executor: {migration.version}.")


def _record_migration(conn: DatabaseConnection, migration: Migration) -> None:
    conn.execute(
        f"INSERT INTO {MIGRATION_TABLE} (version, name, checksum) VALUES (?, ?, ?)",
        [migration.version, migration.name, migration.checksum],
    )


def upgrade_schema(conn: DatabaseConnection) -> SchemaStatus:
    initial = inspect_schema(conn)
    if initial.state is SchemaState.UNVERSIONED:
        raise ExistingSchemaMismatchError(
            "Banco existente sem versão. Execute baseline-existing após inspeção estrutural."
        )
    if initial.state in {SchemaState.AHEAD, SchemaState.UNKNOWN}:
        raise SchemaLifecycleError("O schema não pode ser atualizado com segurança no estado atual.")
    if initial.state is SchemaState.CURRENT:
        return initial

    try:
        _begin_migration(conn)
        locked_status = inspect_schema(conn)
        if locked_status.state is SchemaState.CURRENT:
            conn.commit()
            return locked_status
        if locked_status.state is SchemaState.UNVERSIONED:
            raise ExistingSchemaMismatchError(
                "Banco existente sem versão. Execute baseline-existing após inspeção estrutural."
            )
        if locked_status.state in {SchemaState.AHEAD, SchemaState.UNKNOWN}:
            raise SchemaLifecycleError(
                "O schema não pode ser atualizado com segurança no estado atual."
            )
        _create_migration_table(conn)
        current = locked_status.current_version or 0
        for migration in MIGRATIONS:
            if migration.version <= current:
                continue
            _apply_migration(conn, migration)
            _record_migration(conn, migration)
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    status = inspect_schema(conn)
    if not status.compatible:
        raise SchemaLifecycleError("Migration concluída sem produzir o contrato estrutural esperado.")
    return status


def initialize_schema(conn: DatabaseConnection) -> SchemaStatus:
    status = inspect_schema(conn)
    if status.state is not SchemaState.MISSING:
        raise SchemaLifecycleError("initialize exige um banco sem schema de aplicação.")
    return upgrade_schema(conn)


def _adoptable_version(conn: DatabaseConnection) -> tuple[int | None, tuple[str, ...]]:
    current_issues = structural_issues(conn, LATEST_SCHEMA_VERSION)
    if not current_issues:
        return LATEST_SCHEMA_VERSION, ()
    tables = _table_names(conn)
    version_two_tables = set(CURRENT_TABLE_COLUMNS) - set(LEGACY_TABLE_COLUMNS)
    version_two_columns = {
        (table, column)
        for table, column, _definition in v002_approved_schema.COLUMN_ADDITIONS
    }
    has_version_two_signal = bool(tables & version_two_tables) or any(
        table in tables and column in _column_names(conn, table)
        for table, column in version_two_columns
    )
    if has_version_two_signal:
        return None, current_issues
    legacy_issues = structural_issues(conn, 1)
    if not legacy_issues:
        return 1, ()
    return None, legacy_issues


def baseline_existing_schema(conn: DatabaseConnection, *, confirmed: bool = False) -> SchemaStatus:
    status = inspect_schema(conn)
    if status.state is not SchemaState.UNVERSIONED:
        raise ExistingSchemaMismatchError("baseline-existing exige um schema não versionado.")
    version, issues = _adoptable_version(conn)
    if version is None:
        summary = "; ".join(issues[:5])
        raise ExistingSchemaMismatchError(f"Schema incompatível; adoção recusada: {summary}")
    if not confirmed:
        raise ExistingSchemaMismatchError(
            f"Schema estruturalmente compatível com a versão {version}; repita com confirmação explícita."
        )

    try:
        _begin_migration(conn)
        locked_status = inspect_schema(conn)
        if locked_status.state is not SchemaState.UNVERSIONED:
            raise ExistingSchemaMismatchError(
                "O estado do schema mudou durante a adoção; execute a inspeção novamente."
            )
        locked_version, locked_issues = _adoptable_version(conn)
        if locked_version != version or locked_issues:
            raise ExistingSchemaMismatchError(
                "O contrato estrutural mudou durante a adoção; execute a inspeção novamente."
            )
        _create_migration_table(conn)
        for migration in MIGRATIONS:
            if migration.version <= version:
                _record_migration(conn, migration)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return inspect_schema(conn)
