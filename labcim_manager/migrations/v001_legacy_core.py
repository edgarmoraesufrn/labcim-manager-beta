from __future__ import annotations


VERSION = 1
NAME = "legacy_core"


SQL = """
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
