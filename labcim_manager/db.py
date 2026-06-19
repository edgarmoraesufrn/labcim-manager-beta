from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd


def connect(path: Path | str) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == column for r in rows)


def _add_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if not _has_column(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_code TEXT NOT NULL UNIQUE,
            equipment_name TEXT NOT NULL,
            lab_unit TEXT,
            location TEXT,
            requires_operator INTEGER DEFAULT 0,
            responsible_name TEXT,
            responsible_phone TEXT,
            active INTEGER DEFAULT 1,
            operational_status TEXT DEFAULT 'available',
            unavailable_functions TEXT,
            max_sample_capacity INTEGER,
            capacity_unit TEXT DEFAULT 'amostras',
            capacity_enforced INTEGER DEFAULT 0,
            technical_manager TEXT,
            pop_title TEXT,
            pop_path TEXT,
            pop_version TEXT,
            pop_updated_at TEXT,
            pop_responsible TEXT,
            document_notes TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT,
            phone_e164 TEXT,
            role TEXT DEFAULT 'member',
            lab_unit TEXT,
            department TEXT,
            advisor_name TEXT,
            training_completed INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_code TEXT,
            project_name TEXT NOT NULL,
            funding_source TEXT,
            start_date TEXT,
            end_date TEXT,
            active INTEGER DEFAULT 1,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            project_id INTEGER,
            operator_id INTEGER,
            performed_by_id INTEGER,
            start_datetime TEXT NOT NULL,
            end_datetime TEXT NOT NULL,
            sample_count INTEGER,
            purpose TEXT,
            status TEXT DEFAULT 'scheduled',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(equipment_id) REFERENCES equipment(id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(operator_id) REFERENCES users(id),
            FOREIGN KEY(performed_by_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS maintenance_preventive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id INTEGER NOT NULL,
            activity_type TEXT,
            description TEXT NOT NULL,
            periodicity TEXT,
            planned_date TEXT,
            planned_end_date TEXT,
            performed_date TEXT,
            execution_time TEXT,
            checklist_path TEXT,
            internal_responsible TEXT,
            external_supplier TEXT,
            supplier_contact TEXT,
            service_order TEXT,
            status TEXT,
            certificate_path TEXT,
            observations TEXT,
            next_date TEXT,
            blocks_booking INTEGER DEFAULT 1,
            notify_internal INTEGER DEFAULT 1,
            notify_manager INTEGER DEFAULT 1,
            notify_supplier INTEGER DEFAULT 0,
            notify_users INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(equipment_id) REFERENCES equipment(id)
        );

        CREATE TABLE IF NOT EXISTS maintenance_corrective (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id INTEGER NOT NULL,
            reporter_id INTEGER,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            occurrence_datetime TEXT,
            impact TEXT,
            priority TEXT,
            attachment_path TEXT,
            assigned_to TEXT,
            initial_diagnosis TEXT,
            probable_cause TEXT,
            operator_trained TEXT,
            external_supplier_needed INTEGER DEFAULT 0,
            corrective_action TEXT,
            replaced_parts TEXT,
            costs REAL,
            downtime_hours REAL,
            conclusion_date TEXT,
            status TEXT,
            notify_technical INTEGER DEFAULT 1,
            notify_manager INTEGER DEFAULT 1,
            notify_supplier INTEGER DEFAULT 0,
            notify_reporter INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(equipment_id) REFERENCES equipment(id),
            FOREIGN KEY(reporter_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS supplies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supply_name TEXT NOT NULL,
            commercial_name TEXT,
            manufacturer TEXT,
            category TEXT,
            physical_state TEXT,
            application_function TEXT,
            addition_mode TEXT,
            unit TEXT DEFAULT 'kg',
            current_quantity REAL DEFAULT 0,
            minimum_quantity REAL DEFAULT 0,
            lot TEXT,
            expiration_date TEXT,
            location TEXT,
            responsible_name TEXT,
            safety_doc_path TEXT,
            technical_doc_path TEXT,
            density REAL,
            recommended_concentration TEXT,
            recommended_temperature TEXT,
            characterization_summary TEXT,
            active INTEGER DEFAULT 1,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS supply_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supply_id INTEGER NOT NULL,
            movement_type TEXT NOT NULL,
            movement_date TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT,
            user_id INTEGER,
            project_id INTEGER,
            purpose TEXT,
            document_path TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(supply_id) REFERENCES supplies(id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS access_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            code_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used_at TEXT,
            attempts INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS notification_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            recipient_email TEXT,
            subject TEXT,
            body TEXT,
            status TEXT,
            error_message TEXT,
            related_table TEXT,
            related_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # Migrações leves para bancos já criados por versões anteriores.
    _add_column(conn, "equipment", "operational_status", "TEXT DEFAULT 'available'")
    _add_column(conn, "equipment", "unavailable_functions", "TEXT")
    _add_column(conn, "equipment", "max_sample_capacity", "INTEGER")
    _add_column(conn, "equipment", "capacity_unit", "TEXT DEFAULT 'amostras'")
    _add_column(conn, "equipment", "capacity_enforced", "INTEGER DEFAULT 0")
    _add_column(conn, "equipment", "technical_manager", "TEXT")
    _add_column(conn, "equipment", "pop_title", "TEXT")
    _add_column(conn, "equipment", "pop_path", "TEXT")
    _add_column(conn, "equipment", "pop_version", "TEXT")
    _add_column(conn, "equipment", "pop_updated_at", "TEXT")
    _add_column(conn, "equipment", "pop_responsible", "TEXT")
    _add_column(conn, "equipment", "document_notes", "TEXT")
    _add_column(conn, "equipment", "updated_at", "TEXT")
    _add_column(conn, "users", "updated_at", "TEXT")
    _add_column(conn, "projects", "start_date", "TEXT")
    _add_column(conn, "projects", "end_date", "TEXT")
    _add_column(conn, "projects", "notes", "TEXT")
    _add_column(conn, "projects", "updated_at", "TEXT")
    _add_column(conn, "bookings", "performed_by_id", "INTEGER")
    _add_column(conn, "maintenance_preventive", "planned_end_date", "TEXT")
    _add_column(conn, "maintenance_preventive", "blocks_booking", "INTEGER DEFAULT 1")
    _add_column(conn, "maintenance_preventive", "updated_at", "TEXT")
    _add_column(conn, "maintenance_corrective", "updated_at", "TEXT")
    conn.execute("UPDATE users SET role = 'manager' WHERE LOWER(COALESCE(role, '')) IN ('operator', 'operador', 'gerente')")
    conn.commit()


def query_df(conn: sqlite3.Connection, sql: str, params: list[Any] | tuple[Any, ...] | None = None) -> pd.DataFrame:
    return pd.read_sql_query(sql, conn, params=params or [])


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    tables = [
        "equipment",
        "users",
        "projects",
        "bookings",
        "maintenance_preventive",
        "maintenance_corrective",
        "supplies",
        "supply_movements",
        "access_codes",
        "notification_log",
    ]
    counts: dict[str, int] = {}
    for table in tables:
        counts[table] = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
    return counts


def get_active_user_by_email(conn: sqlite3.Connection, email: str) -> sqlite3.Row | None:
    email = str(email or "").strip().lower()
    if not email:
        return None
    return conn.execute(
        """
        SELECT *
        FROM users
        WHERE active = 1
          AND email IS NOT NULL
          AND LOWER(TRIM(email)) = ?
        LIMIT 1
        """,
        [email],
    ).fetchone()


def create_access_code_record(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    email: str,
    code_hash: str,
    expires_at: str,
) -> None:
    conn.execute(
        "UPDATE access_codes SET used_at = CURRENT_TIMESTAMP WHERE user_id = ? AND used_at IS NULL",
        [user_id],
    )
    conn.execute(
        """
        INSERT INTO access_codes (user_id, email, code_hash, expires_at)
        VALUES (?, ?, ?, ?)
        """,
        [user_id, email, code_hash, expires_at],
    )
    conn.commit()


def verify_access_code_record(conn: sqlite3.Connection, *, email: str, code_hash: str) -> tuple[bool, str, sqlite3.Row | None]:
    email = str(email or "").strip().lower()
    code_hash = str(code_hash or "").strip()
    if not email or not code_hash:
        return False, "Informe o e-mail e o código recebido.", None

    # Procura primeiro um código ativo que combine com o e-mail E com o código informado.
    # Isso evita falha quando há mais de um OTP recente para o mesmo usuário.
    row = conn.execute(
        """
        SELECT ac.*, u.full_name, u.role, u.active, u.email AS user_email
        FROM access_codes ac
        JOIN users u ON u.id = ac.user_id
        WHERE LOWER(TRIM(ac.email)) = ?
          AND ac.used_at IS NULL
          AND ac.code_hash = ?
        ORDER BY ac.created_at DESC, ac.id DESC
        LIMIT 1
        """,
        [email, code_hash],
    ).fetchone()

    if row:
        if int(row["active"] or 0) != 1:
            return False, "Usuário inativo.", None
        try:
            expired = datetime.fromisoformat(str(row["expires_at"])) < datetime.now()
        except Exception:
            expired = True
        if expired:
            conn.execute("UPDATE access_codes SET used_at = CURRENT_TIMESTAMP WHERE id = ?", [row["id"]])
            conn.commit()
            return False, "Código expirado. Solicite um novo código.", None
        if int(row["attempts"] or 0) >= 5:
            conn.execute("UPDATE access_codes SET used_at = CURRENT_TIMESTAMP WHERE id = ?", [row["id"]])
            conn.commit()
            return False, "Muitas tentativas. Solicite um novo código.", None
        conn.execute("UPDATE access_codes SET used_at = CURRENT_TIMESTAMP WHERE id = ?", [row["id"]])
        conn.commit()
        return True, "Acesso liberado.", row

    # Diagnóstico mais claro para o usuário.
    latest = conn.execute(
        """
        SELECT ac.*, u.active
        FROM access_codes ac
        JOIN users u ON u.id = ac.user_id
        WHERE LOWER(TRIM(ac.email)) = ?
        ORDER BY ac.created_at DESC, ac.id DESC
        LIMIT 1
        """,
        [email],
    ).fetchone()
    if not latest:
        return False, "Não há código ativo para este e-mail. Solicite uma nova senha volátil.", None
    if latest["used_at"]:
        return False, "O código mais recente já foi utilizado. Solicite uma nova senha volátil.", None
    try:
        expired = datetime.fromisoformat(str(latest["expires_at"])) < datetime.now()
    except Exception:
        expired = True
    if expired:
        conn.execute("UPDATE access_codes SET used_at = CURRENT_TIMESTAMP WHERE id = ?", [latest["id"]])
        conn.commit()
        return False, "Código expirado. Solicite um novo código.", None

    conn.execute("UPDATE access_codes SET attempts = COALESCE(attempts, 0) + 1 WHERE id = ?", [latest["id"]])
    conn.commit()
    return False, "Código incorreto. Confira o e-mail mais recente e digite apenas os 6 números.", None

def log_notification(
    conn: sqlite3.Connection,
    *,
    event_type: str,
    recipient_email: str | None,
    subject: str,
    body: str,
    status: str,
    error_message: str | None = None,
    related_table: str | None = None,
    related_id: int | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO notification_log (
            event_type, recipient_email, subject, body, status,
            error_message, related_table, related_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [event_type, recipient_email, subject, body, status, error_message, related_table, related_id],
    )
    conn.commit()


def _norm_col(name: str) -> str:
    return (
        str(name)
        .strip()
        .lower()
        .replace("á", "a")
        .replace("à", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("õ", "o")
        .replace("ô", "o")
        .replace("ú", "u")
        .replace("ç", "c")
        .replace("/", "_")
        .replace("-", "_")
        .replace(" ", "_")
    )


def _first(row: pd.Series, *names: str, default: Any = None) -> Any:
    normalized = {_norm_col(c): c for c in row.index}
    for name in names:
        key = _norm_col(name)
        if key in normalized:
            value = row[normalized[key]]
            if pd.notna(value):
                return value
    for name in names:
        key = _norm_col(name)
        for normalized_col, original_col in normalized.items():
            if key and key in normalized_col:
                value = row[original_col]
                if pd.notna(value):
                    return value
    return default


def _to_bool_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    if isinstance(value, bool):
        return int(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "sim", "yes", "y", "ativo", "concluído", "concluido"}:
        return 1
    if text in {"0", "false", "não", "nao", "no", "n", "inativo"}:
        return 0
    return default


def _clean_excel_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, float) and value.is_integer():
        text = str(int(value))
    else:
        text = str(value).strip()
    if text.lower() in {"", "nan", "none", "nat"}:
        return None
    return text


def _normalize_role(value: Any) -> str:
    role = str(_clean_excel_value(value) or "member").strip().lower()
    aliases = {
        "administrador": "admin",
        "admin": "admin",
        "gerente": "manager",
        "manager": "manager",
        "operator": "manager",
        "operador": "manager",
        "membro": "member",
        "member": "member",
        "usuario": "member",
        "usuário": "member",
        "user": "member",
    }
    return aliases.get(role, "member")


def import_base_xlsx(conn: sqlite3.Connection, path: Path | str) -> dict[str, int]:
    """Importa uma base Excel simples, aceitando nomes de abas flexíveis."""
    path = Path(path)
    xl = pd.ExcelFile(path)
    counts = {"equipment": 0, "users": 0, "projects": 0}

    for sheet in xl.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet)
        if df.empty:
            continue
        sheet_key = _norm_col(sheet)

        if "equip" in sheet_key:
            for _, row in df.iterrows():
                code = str(_first(row, "equipment_code", "codigo", "código", "patrimonio", "patrimônio", default="")).strip()
                name = str(_first(row, "equipment_name", "equipamento", "nome", default="")).strip()
                if not code or not name:
                    continue
                conn.execute(
                    """
                    INSERT INTO equipment (
                        equipment_code, equipment_name, lab_unit, location, requires_operator,
                        responsible_name, responsible_phone, active, operational_status,
                        unavailable_functions, max_sample_capacity, capacity_unit,
                        capacity_enforced, technical_manager, pop_title, pop_path,
                        pop_version, pop_updated_at, pop_responsible, document_notes, notes
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(equipment_code) DO UPDATE SET
                        equipment_name=excluded.equipment_name,
                        lab_unit=excluded.lab_unit,
                        location=excluded.location,
                        requires_operator=excluded.requires_operator,
                        responsible_name=excluded.responsible_name,
                        responsible_phone=excluded.responsible_phone,
                        active=excluded.active,
                        operational_status=excluded.operational_status,
                        unavailable_functions=excluded.unavailable_functions,
                        max_sample_capacity=excluded.max_sample_capacity,
                        capacity_unit=excluded.capacity_unit,
                        capacity_enforced=excluded.capacity_enforced,
                        technical_manager=excluded.technical_manager,
                        pop_title=excluded.pop_title,
                        pop_path=excluded.pop_path,
                        pop_version=excluded.pop_version,
                        pop_updated_at=excluded.pop_updated_at,
                        pop_responsible=excluded.pop_responsible,
                        document_notes=excluded.document_notes,
                        notes=excluded.notes,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (
                        code,
                        name,
                        _clean_excel_value(_first(row, "lab_unit", "unidade")),
                        _clean_excel_value(_first(row, "location", "local", "localizacao", "localização")),
                        _to_bool_int(_first(row, "requires_operator", "requer_operador", "operador", default=0)),
                        _clean_excel_value(_first(row, "responsible_name", "responsavel", "responsável")),
                        _clean_excel_value(_first(row, "responsible_phone", "telefone")),
                        _to_bool_int(_first(row, "active", "ativo", default=1), default=1),
                        _clean_excel_value(_first(row, "operational_status", "status_operacional", default="available")) or "available",
                        _clean_excel_value(_first(row, "unavailable_functions", "funcionalidades_indisponiveis", "funcionalidades_indisponíveis")),
                        _clean_excel_value(_first(row, "max_sample_capacity", "capacidade_maxima", "capacidade_máxima")),
                        _clean_excel_value(_first(row, "capacity_unit", "unidade_da_capacidade")),
                        _to_bool_int(_first(row, "capacity_enforced", "bloqueia_acima_da_capacidade", default=0)),
                        _clean_excel_value(_first(row, "technical_manager", "gestor_tecnico", "gestor_técnico")),
                        _clean_excel_value(_first(row, "pop_title", "titulo_pop", "título_pop")),
                        _clean_excel_value(_first(row, "pop_path", "caminho_pop", "link_pop")),
                        _clean_excel_value(_first(row, "pop_version", "versao_pop", "versão_pop")),
                        _clean_excel_value(_first(row, "pop_updated_at", "data_pop", "atualizacao_pop", "atualização_pop")),
                        _clean_excel_value(_first(row, "pop_responsible", "responsavel_pop", "responsável_pop")),
                        _clean_excel_value(_first(row, "document_notes", "observacoes_documentais", "observações_documentais")),
                        _clean_excel_value(_first(row, "notes", "observacoes", "observações")),
                    ),
                )
                counts["equipment"] += 1

        elif "usuario" in sheet_key or "user" in sheet_key:
            for _, row in df.iterrows():
                name = str(_first(row, "full_name", "nome", "nome_completo", default="")).strip()
                if not name:
                    continue
                email = _clean_excel_value(_first(row, "email", "e-mail"))
                phone = _clean_excel_value(_first(row, "phone_e164", "telefone", "celular"))
                existing = None
                if email:
                    existing = conn.execute("SELECT id FROM users WHERE LOWER(COALESCE(email, '')) = LOWER(?) LIMIT 1", [email]).fetchone()
                if existing is None and phone:
                    existing = conn.execute("SELECT id FROM users WHERE COALESCE(phone_e164, '') = ? LIMIT 1", [phone]).fetchone()
                if existing is None:
                    existing = conn.execute("SELECT id FROM users WHERE LOWER(full_name) = LOWER(?) LIMIT 1", [name]).fetchone()
                values = (
                    name,
                    email,
                    phone,
                    _normalize_role(_first(row, "role", "perfil", default="member")),
                    _clean_excel_value(_first(row, "lab_unit", "unidade")),
                    _clean_excel_value(_first(row, "department", "departamento", "programa")),
                    _clean_excel_value(_first(row, "advisor_name", "orientador")),
                    _to_bool_int(_first(row, "training_completed", "treinamento", default=0)),
                    _to_bool_int(_first(row, "active", "ativo", default=1), default=1),
                    _clean_excel_value(_first(row, "notes", "observacoes", "observações")),
                )
                if existing:
                    conn.execute(
                        """
                        UPDATE users
                        SET full_name = ?,
                            email = ?,
                            phone_e164 = ?,
                            role = ?,
                            lab_unit = ?,
                            department = ?,
                            advisor_name = ?,
                            training_completed = ?,
                            active = ?,
                            notes = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (*values, int(existing["id"])),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO users (full_name, email, phone_e164, role, lab_unit, department, advisor_name, training_completed, active, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        values,
                    )
                counts["users"] += 1

        elif "projeto" in sheet_key or "project" in sheet_key:
            for _, row in df.iterrows():
                name = str(_first(row, "project_name", "projeto", "nome", default="")).strip()
                if not name:
                    continue
                project_code = _clean_excel_value(_first(row, "project_code", "codigo", "código"))
                existing = None
                if project_code:
                    existing = conn.execute("SELECT id FROM projects WHERE LOWER(COALESCE(project_code, '')) = LOWER(?) LIMIT 1", [project_code]).fetchone()
                if existing is None:
                    existing = conn.execute("SELECT id FROM projects WHERE LOWER(project_name) = LOWER(?) LIMIT 1", [name]).fetchone()
                values = (
                    project_code,
                    name,
                    _clean_excel_value(_first(row, "funding_source", "financiador", "fonte")),
                    _clean_excel_value(_first(row, "start_date", "data_inicio", "data_de_inicio", "início", "inicio")),
                    _clean_excel_value(_first(row, "end_date", "data_fim", "data_de_fim", "fim", "termino", "término")),
                    _to_bool_int(_first(row, "active", "ativo", default=1), default=1),
                    _clean_excel_value(_first(row, "notes", "observacoes", "observações")),
                )
                if existing:
                    conn.execute(
                        """
                        UPDATE projects
                        SET project_code = ?,
                            project_name = ?,
                            funding_source = ?,
                            start_date = ?,
                            end_date = ?,
                            active = ?,
                            notes = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (*values, int(existing["id"])),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO projects (project_code, project_name, funding_source, start_date, end_date, active, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        values,
                    )
                counts["projects"] += 1

    conn.commit()
    return counts


def seed_default_pops(conn: sqlite3.Connection) -> int:
    """Associa POPs locais às famílias de equipamentos já cadastradas."""
    mappings = [
        ("AUT", "POP - Autoclave", "assets/pops/POP_Autoclave.pdf"),
        ("UCA", "POP - Ultrasonic Cement Analyzer (UCA)", "assets/pops/POP_UCA.pdf"),
        ("CP", "POP - Consistômetro pressurizado", "assets/pops/POP_Consistometro_pressurizado.pdf"),
        ("FP", "POP - Filtro prensa", "assets/pops/POP_Filtro.pdf"),
        ("REO", "POP - Reômetro", "assets/pops/POP_Reometro.pdf"),
    ]
    updated = 0
    for prefix, title, path in mappings:
        cur = conn.execute(
            """
            UPDATE equipment
            SET pop_title = COALESCE(NULLIF(pop_title, ''), ?),
                pop_path = COALESCE(NULLIF(pop_path, ''), ?),
                pop_version = COALESCE(NULLIF(pop_version, ''), 'v1'),
                pop_responsible = COALESCE(NULLIF(pop_responsible, ''), technical_manager, responsible_name),
                document_notes = COALESCE(NULLIF(document_notes, ''), 'POP local incluído na versão v7.4 do LabCim Manager.'),
                updated_at = CURRENT_TIMESTAMP
            WHERE equipment_code LIKE ?
              AND (pop_path IS NULL OR TRIM(pop_path) = '')
            """,
            [title, path, f"{prefix}%"],
        )
        updated += cur.rowcount if cur.rowcount is not None else 0
    conn.commit()
    return updated


def _overlap_clause(start_iso: str, end_iso: str) -> tuple[str, list[str]]:
    return "(datetime(start_datetime) < datetime(?) AND datetime(end_datetime) > datetime(?))", [end_iso, start_iso]


def _booking_conflict(conn: sqlite3.Connection, equipment_id: int, start_iso: str, end_iso: str) -> sqlite3.Row | None:
    clause, params = _overlap_clause(start_iso, end_iso)
    return conn.execute(
        f"""
        SELECT id, start_datetime, end_datetime, status
        FROM bookings
        WHERE equipment_id = ?
          AND status NOT IN ('cancelled', 'no_show')
          AND {clause}
        LIMIT 1
        """,
        [equipment_id, *params],
    ).fetchone()


def _preventive_conflict(conn: sqlite3.Connection, equipment_id: int, start_iso: str, end_iso: str) -> sqlite3.Row | None:
    start_dt = datetime.fromisoformat(start_iso)
    end_dt = datetime.fromisoformat(end_iso)
    rows = conn.execute(
        """
        SELECT id, activity_type, description, planned_date, planned_end_date, status
        FROM maintenance_preventive
        WHERE equipment_id = ?
          AND COALESCE(blocks_booking, 1) = 1
          AND LOWER(COALESCE(status, 'pendente')) NOT IN ('realizado', 'concluído', 'concluido', 'cancelado')
          AND planned_date IS NOT NULL
        """,
        [equipment_id],
    ).fetchall()
    for row in rows:
        try:
            prev_start = datetime.fromisoformat(str(row["planned_date"]))
        except ValueError:
            prev_start = datetime.fromisoformat(str(row["planned_date"]) + "T00:00:00")
        if row["planned_end_date"]:
            try:
                prev_end = datetime.fromisoformat(str(row["planned_end_date"]))
            except ValueError:
                prev_end = datetime.fromisoformat(str(row["planned_end_date"]) + "T23:59:59")
        else:
            prev_end = prev_start + timedelta(days=1)
        if prev_start < end_dt and prev_end > start_dt:
            return row
    return None


def create_booking(
    conn: sqlite3.Connection,
    *,
    equipment_id: int,
    user_id: int,
    project_id: int | None,
    operator_id: int | None,
    start_iso: str,
    end_iso: str,
    sample_count: int | None,
    purpose: str | None,
    performed_by_id: int | None = None,
) -> tuple[bool, str]:
    eq = conn.execute("SELECT * FROM equipment WHERE id = ?", [equipment_id]).fetchone()
    if not eq:
        return False, "Equipamento não encontrado."
    if int(eq["active"] or 0) != 1:
        return False, "Este equipamento está inativo."
    if eq["operational_status"] == "maintenance":
        return False, "Este equipamento está marcado como em manutenção."
    if sample_count and eq["max_sample_capacity"] and sample_count > int(eq["max_sample_capacity"]):
        if int(eq["capacity_enforced"] or 0) == 1:
            return False, f"A quantidade excede a capacidade máxima cadastrada ({eq['max_sample_capacity']} {eq['capacity_unit'] or 'amostras'})."

    conflict = _booking_conflict(conn, equipment_id, start_iso, end_iso)
    if conflict:
        return False, f"Conflito com a reserva #{conflict['id']} ({conflict['start_datetime']} a {conflict['end_datetime']})."

    maintenance = _preventive_conflict(conn, equipment_id, start_iso, end_iso)
    if maintenance:
        return False, f"Conflito com manutenção/calibração #{maintenance['id']}: {maintenance['description']}."

    conn.execute(
        """
        INSERT INTO bookings (
            equipment_id, user_id, project_id, operator_id, performed_by_id,
            start_datetime, end_datetime, sample_count, purpose, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'scheduled')
        """,
        [equipment_id, user_id, project_id, operator_id, performed_by_id, start_iso, end_iso, sample_count, purpose],
    )
    conn.commit()
    return True, "Reserva registrada com sucesso."


def update_booking_status(conn: sqlite3.Connection, booking_id: int, status: str) -> None:
    conn.execute("UPDATE bookings SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", [status, booking_id])
    conn.commit()


def update_equipment_operational_info(
    conn: sqlite3.Connection,
    equipment_id: int,
    *,
    location: str | None,
    operational_status: str,
    unavailable_functions: str | None,
    max_sample_capacity: int | None,
    capacity_unit: str | None,
    capacity_enforced: int,
    technical_manager: str | None,
    pop_title: str | None,
    pop_path: str | None,
    pop_version: str | None,
    pop_updated_at: str | None,
    pop_responsible: str | None,
    document_notes: str | None,
    notes: str | None,
) -> None:
    conn.execute(
        """
        UPDATE equipment
        SET location = ?,
            operational_status = ?,
            unavailable_functions = ?,
            max_sample_capacity = ?,
            capacity_unit = ?,
            capacity_enforced = ?,
            technical_manager = ?,
            pop_title = ?,
            pop_path = ?,
            pop_version = ?,
            pop_updated_at = ?,
            pop_responsible = ?,
            document_notes = ?,
            notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        [
            location,
            operational_status,
            unavailable_functions,
            max_sample_capacity,
            capacity_unit,
            capacity_enforced,
            technical_manager,
            pop_title,
            pop_path,
            pop_version,
            pop_updated_at,
            pop_responsible,
            document_notes,
            notes,
            equipment_id,
        ],
    )
    conn.commit()


def create_equipment(
    conn: sqlite3.Connection,
    *,
    equipment_code: str,
    equipment_name: str,
    lab_unit: str | None,
    location: str | None,
    requires_operator: int,
    responsible_name: str | None,
    responsible_phone: str | None,
    active: int,
    operational_status: str,
    unavailable_functions: str | None,
    max_sample_capacity: int | None,
    capacity_unit: str | None,
    capacity_enforced: int,
    technical_manager: str | None,
    pop_title: str | None,
    pop_path: str | None,
    pop_version: str | None,
    pop_updated_at: str | None,
    pop_responsible: str | None,
    document_notes: str | None,
    notes: str | None,
) -> tuple[bool, str]:
    equipment_code = equipment_code.strip()
    equipment_name = equipment_name.strip()
    if not equipment_code or not equipment_name:
        return False, "Informe código e nome do equipamento."
    try:
        conn.execute(
            """
            INSERT INTO equipment (
                equipment_code, equipment_name, lab_unit, location, requires_operator,
                responsible_name, responsible_phone, active, operational_status,
                unavailable_functions, max_sample_capacity, capacity_unit,
                capacity_enforced, technical_manager, pop_title, pop_path,
                pop_version, pop_updated_at, pop_responsible, document_notes, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                equipment_code,
                equipment_name,
                lab_unit,
                location,
                requires_operator,
                responsible_name,
                responsible_phone,
                active,
                operational_status,
                unavailable_functions,
                max_sample_capacity,
                capacity_unit,
                capacity_enforced,
                technical_manager,
                pop_title,
                pop_path,
                pop_version,
                pop_updated_at,
                pop_responsible,
                document_notes,
                notes,
            ],
        )
        conn.commit()
        return True, "Equipamento cadastrado com sucesso."
    except sqlite3.IntegrityError:
        return False, "Já existe um equipamento com este código."


def update_equipment_master(
    conn: sqlite3.Connection,
    equipment_id: int,
    *,
    equipment_code: str,
    equipment_name: str,
    lab_unit: str | None,
    location: str | None,
    requires_operator: int,
    responsible_name: str | None,
    responsible_phone: str | None,
    active: int,
    operational_status: str,
    unavailable_functions: str | None,
    max_sample_capacity: int | None,
    capacity_unit: str | None,
    capacity_enforced: int,
    technical_manager: str | None,
    pop_title: str | None,
    pop_path: str | None,
    pop_version: str | None,
    pop_updated_at: str | None,
    pop_responsible: str | None,
    document_notes: str | None,
    notes: str | None,
) -> tuple[bool, str]:
    equipment_code = equipment_code.strip()
    equipment_name = equipment_name.strip()
    if not equipment_code or not equipment_name:
        return False, "Informe código e nome do equipamento."
    try:
        conn.execute(
            """
            UPDATE equipment
            SET equipment_code = ?,
                equipment_name = ?,
                lab_unit = ?,
                location = ?,
                requires_operator = ?,
                responsible_name = ?,
                responsible_phone = ?,
                active = ?,
                operational_status = ?,
                unavailable_functions = ?,
                max_sample_capacity = ?,
                capacity_unit = ?,
                capacity_enforced = ?,
                technical_manager = ?,
                pop_title = ?,
                pop_path = ?,
                pop_version = ?,
                pop_updated_at = ?,
                pop_responsible = ?,
                document_notes = ?,
                notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            [
                equipment_code,
                equipment_name,
                lab_unit,
                location,
                requires_operator,
                responsible_name,
                responsible_phone,
                active,
                operational_status,
                unavailable_functions,
                max_sample_capacity,
                capacity_unit,
                capacity_enforced,
                technical_manager,
                pop_title,
                pop_path,
                pop_version,
                pop_updated_at,
                pop_responsible,
                document_notes,
                notes,
                equipment_id,
            ],
        )
        conn.commit()
        return True, "Equipamento atualizado com sucesso."
    except sqlite3.IntegrityError:
        return False, "Já existe outro equipamento com este código."


def create_user(
    conn: sqlite3.Connection,
    *,
    full_name: str,
    email: str | None,
    phone_e164: str | None,
    role: str,
    lab_unit: str | None,
    department: str | None,
    advisor_name: str | None,
    training_completed: int,
    active: int,
    notes: str | None,
) -> tuple[bool, str]:
    full_name = full_name.strip()
    if not full_name:
        return False, "Informe o nome completo do usuário."
    role = _normalize_role(role)
    conn.execute(
        """
        INSERT INTO users (
            full_name, email, phone_e164, role, lab_unit, department,
            advisor_name, training_completed, active, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [full_name, email, phone_e164, role, lab_unit, department, advisor_name, training_completed, active, notes],
    )
    conn.commit()
    return True, "Usuário cadastrado com sucesso."


def update_user(
    conn: sqlite3.Connection,
    user_id: int,
    *,
    full_name: str,
    email: str | None,
    phone_e164: str | None,
    role: str,
    lab_unit: str | None,
    department: str | None,
    advisor_name: str | None,
    training_completed: int,
    active: int,
    notes: str | None,
) -> tuple[bool, str]:
    full_name = full_name.strip()
    if not full_name:
        return False, "Informe o nome completo do usuário."
    role = _normalize_role(role)
    conn.execute(
        """
        UPDATE users
        SET full_name = ?,
            email = ?,
            phone_e164 = ?,
            role = ?,
            lab_unit = ?,
            department = ?,
            advisor_name = ?,
            training_completed = ?,
            active = ?,
            notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        [full_name, email, phone_e164, role, lab_unit, department, advisor_name, training_completed, active, notes, user_id],
    )
    conn.commit()
    return True, "Usuário atualizado com sucesso."


def create_project(
    conn: sqlite3.Connection,
    *,
    project_code: str | None,
    project_name: str,
    funding_source: str | None,
    start_date: str | None,
    end_date: str | None,
    active: int,
    notes: str | None,
) -> tuple[bool, str]:
    project_name = project_name.strip()
    if not project_name:
        return False, "Informe o nome do projeto."
    conn.execute(
        """
        INSERT INTO projects (
            project_code, project_name, funding_source, start_date, end_date, active, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [project_code, project_name, funding_source, start_date, end_date, active, notes],
    )
    conn.commit()
    return True, "Projeto cadastrado com sucesso."


def update_project(
    conn: sqlite3.Connection,
    project_id: int,
    *,
    project_code: str | None,
    project_name: str,
    funding_source: str | None,
    start_date: str | None,
    end_date: str | None,
    active: int,
    notes: str | None,
) -> tuple[bool, str]:
    project_name = project_name.strip()
    if not project_name:
        return False, "Informe o nome do projeto."
    conn.execute(
        """
        UPDATE projects
        SET project_code = ?,
            project_name = ?,
            funding_source = ?,
            start_date = ?,
            end_date = ?,
            active = ?,
            notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        [project_code, project_name, funding_source, start_date, end_date, active, notes, project_id],
    )
    conn.commit()
    return True, "Projeto atualizado com sucesso."


def create_preventive_activity(
    conn: sqlite3.Connection,
    *,
    equipment_id: int,
    activity_type: str,
    description: str,
    periodicity: str,
    planned_date: str | None,
    performed_date: str | None,
    execution_time: str | None,
    checklist_path: str | None,
    internal_responsible: str | None,
    external_supplier: str | None,
    supplier_contact: str | None,
    service_order: str | None,
    status: str,
    certificate_path: str | None,
    observations: str | None,
    next_date: str | None,
    notify_internal: int,
    notify_manager: int,
    notify_supplier: int,
    notify_users: int,
    planned_end_date: str | None = None,
    blocks_booking: int = 1,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO maintenance_preventive (
            equipment_id, activity_type, description, periodicity, planned_date, planned_end_date,
            performed_date, execution_time, checklist_path, internal_responsible,
            external_supplier, supplier_contact, service_order, status, certificate_path,
            observations, next_date, blocks_booking, notify_internal, notify_manager,
            notify_supplier, notify_users
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            equipment_id,
            activity_type,
            description,
            periodicity,
            planned_date,
            planned_end_date,
            performed_date,
            execution_time,
            checklist_path,
            internal_responsible,
            external_supplier,
            supplier_contact,
            service_order,
            status,
            certificate_path,
            observations,
            next_date,
            blocks_booking,
            notify_internal,
            notify_manager,
            notify_supplier,
            notify_users,
        ],
    )
    conn.commit()
    return int(cur.lastrowid)


def create_corrective_ticket(
    conn: sqlite3.Connection,
    *,
    equipment_id: int,
    reporter_id: int | None,
    title: str,
    description: str,
    occurrence_datetime: str,
    impact: str,
    priority: str,
    attachment_path: str | None,
    assigned_to: str | None,
    initial_diagnosis: str | None,
    probable_cause: str | None,
    operator_trained: str,
    external_supplier_needed: int,
    corrective_action: str | None,
    replaced_parts: str | None,
    costs: float | None,
    downtime_hours: float | None,
    conclusion_date: str | None,
    status: str,
    notify_technical: int,
    notify_manager: int,
    notify_supplier: int,
    notify_reporter: int,
) -> None:
    conn.execute(
        """
        INSERT INTO maintenance_corrective (
            equipment_id, reporter_id, title, description, occurrence_datetime, impact,
            priority, attachment_path, assigned_to, initial_diagnosis, probable_cause,
            operator_trained, external_supplier_needed, corrective_action, replaced_parts,
            costs, downtime_hours, conclusion_date, status, notify_technical,
            notify_manager, notify_supplier, notify_reporter
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            equipment_id,
            reporter_id,
            title,
            description,
            occurrence_datetime,
            impact,
            priority,
            attachment_path,
            assigned_to,
            initial_diagnosis,
            probable_cause,
            operator_trained,
            external_supplier_needed,
            corrective_action,
            replaced_parts,
            costs,
            downtime_hours,
            conclusion_date,
            status,
            notify_technical,
            notify_manager,
            notify_supplier,
            notify_reporter,
        ],
    )
    conn.commit()


def update_corrective_status(conn: sqlite3.Connection, ticket_id: int, status: str) -> None:
    conn.execute("UPDATE maintenance_corrective SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", [status, ticket_id])
    conn.commit()


def create_supply(
    conn: sqlite3.Connection,
    *,
    supply_name: str,
    commercial_name: str | None,
    manufacturer: str | None,
    category: str | None,
    physical_state: str | None,
    application_function: str | None,
    addition_mode: str | None,
    unit: str,
    current_quantity: float,
    minimum_quantity: float,
    lot: str | None,
    expiration_date: str | None,
    location: str | None,
    responsible_name: str | None,
    safety_doc_path: str | None,
    technical_doc_path: str | None,
    density: float | None,
    recommended_concentration: str | None,
    recommended_temperature: str | None,
    characterization_summary: str | None,
    notes: str | None,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO supplies (
            supply_name, commercial_name, manufacturer, category, physical_state,
            application_function, addition_mode, unit, current_quantity, minimum_quantity,
            lot, expiration_date, location, responsible_name, safety_doc_path,
            technical_doc_path, density, recommended_concentration,
            recommended_temperature, characterization_summary, active, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        """,
        [
            supply_name,
            commercial_name,
            manufacturer,
            category,
            physical_state,
            application_function,
            addition_mode,
            unit,
            current_quantity,
            minimum_quantity,
            lot,
            expiration_date,
            location,
            responsible_name,
            safety_doc_path,
            technical_doc_path,
            density,
            recommended_concentration,
            recommended_temperature,
            characterization_summary,
            notes,
        ],
    )
    conn.commit()
    return int(cur.lastrowid)


def update_supply(
    conn: sqlite3.Connection,
    supply_id: int,
    *,
    supply_name: str,
    commercial_name: str | None,
    manufacturer: str | None,
    category: str | None,
    physical_state: str | None,
    application_function: str | None,
    addition_mode: str | None,
    unit: str,
    minimum_quantity: float,
    lot: str | None,
    expiration_date: str | None,
    location: str | None,
    responsible_name: str | None,
    safety_doc_path: str | None,
    technical_doc_path: str | None,
    density: float | None,
    recommended_concentration: str | None,
    recommended_temperature: str | None,
    characterization_summary: str | None,
    active: int,
    notes: str | None,
) -> None:
    conn.execute(
        """
        UPDATE supplies
        SET supply_name = ?,
            commercial_name = ?,
            manufacturer = ?,
            category = ?,
            physical_state = ?,
            application_function = ?,
            addition_mode = ?,
            unit = ?,
            minimum_quantity = ?,
            lot = ?,
            expiration_date = ?,
            location = ?,
            responsible_name = ?,
            safety_doc_path = ?,
            technical_doc_path = ?,
            density = ?,
            recommended_concentration = ?,
            recommended_temperature = ?,
            characterization_summary = ?,
            active = ?,
            notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        [
            supply_name,
            commercial_name,
            manufacturer,
            category,
            physical_state,
            application_function,
            addition_mode,
            unit,
            minimum_quantity,
            lot,
            expiration_date,
            location,
            responsible_name,
            safety_doc_path,
            technical_doc_path,
            density,
            recommended_concentration,
            recommended_temperature,
            characterization_summary,
            active,
            notes,
            supply_id,
        ],
    )
    conn.commit()


def create_supply_movement(
    conn: sqlite3.Connection,
    *,
    supply_id: int,
    movement_type: str,
    movement_date: str,
    quantity: float,
    user_id: int | None,
    project_id: int | None,
    purpose: str | None,
    document_path: str | None,
) -> tuple[bool, str]:
    row = conn.execute("SELECT * FROM supplies WHERE id = ?", [supply_id]).fetchone()
    if not row:
        return False, "Insumo não encontrado."
    if quantity <= 0:
        return False, "A quantidade precisa ser maior que zero."

    movement_type = movement_type.lower()
    current = float(row["current_quantity"] or 0)
    delta_map = {
        "entrada": quantity,
        "saída": -quantity,
        "saida": -quantity,
        "descarte": -quantity,
        "ajuste positivo": quantity,
        "ajuste negativo": -quantity,
    }
    if movement_type not in delta_map:
        return False, "Tipo de movimentação inválido."
    new_quantity = current + delta_map[movement_type]
    if new_quantity < -1e-9:
        return False, f"Saldo insuficiente. Saldo atual: {current:g} {row['unit'] or ''}."

    conn.execute(
        """
        INSERT INTO supply_movements (
            supply_id, movement_type, movement_date, quantity, unit,
            user_id, project_id, purpose, document_path
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            supply_id,
            movement_type,
            movement_date,
            quantity,
            row["unit"],
            user_id,
            project_id,
            purpose,
            document_path,
        ],
    )
    conn.execute(
        "UPDATE supplies SET current_quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        [new_quantity, supply_id],
    )
    conn.commit()
    return True, f"Movimentação registrada. Novo saldo: {new_quantity:g} {row['unit'] or ''}."
