from __future__ import annotations


VERSION = 2
NAME = "approved_schema_2026_08"


NEW_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS project_services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    service_code TEXT,
    title TEXT NOT NULL,
    service_type TEXT,
    requester_id INTEGER,
    responsible_id INTEGER,
    status TEXT DEFAULT 'em andamento',
    requested_date TEXT,
    expected_date TEXT,
    completed_date TEXT,
    notes TEXT,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id),
    FOREIGN KEY(requester_id) REFERENCES users(id),
    FOREIGN KEY(responsible_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS booking_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL,
    previous_status TEXT,
    new_status TEXT NOT NULL,
    changed_by_id INTEGER,
    changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reason TEXT,
    source TEXT DEFAULT 'ui',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(booking_id) REFERENCES bookings(id),
    FOREIGN KEY(changed_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS maintenance_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    previous_status TEXT,
    new_status TEXT NOT NULL,
    justification TEXT,
    changed_by_id INTEGER,
    changed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(changed_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS supply_lots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supply_id INTEGER NOT NULL,
    lot_code TEXT NOT NULL,
    expiration_date TEXT,
    received_date TEXT,
    supplier_name TEXT,
    initial_quantity REAL DEFAULT 0,
    current_quantity REAL DEFAULT 0,
    unit TEXT,
    location TEXT,
    certificate_path TEXT,
    notes TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(supply_id) REFERENCES supplies(id)
);

CREATE TABLE IF NOT EXISTS equipment_spare_parts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id INTEGER NOT NULL,
    supply_id INTEGER NOT NULL,
    notes TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(equipment_id) REFERENCES equipment(id),
    FOREIGN KEY(supply_id) REFERENCES supplies(id),
    UNIQUE(equipment_id, supply_id)
);

CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    attachment_role TEXT NOT NULL DEFAULT 'general',
    original_filename TEXT NOT NULL,
    storage_key TEXT NOT NULL,
    storage_backend TEXT NOT NULL,
    mime_type TEXT,
    file_size INTEGER,
    sha256 TEXT,
    uploaded_by_id INTEGER,
    uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY(uploaded_by_id) REFERENCES users(id),
    UNIQUE(storage_backend, storage_key)
);
"""


COLUMN_ADDITIONS = (
    ("equipment", "inactive_reason", "TEXT"),
    ("equipment", "inactive_by_id", "INTEGER"),
    ("equipment", "inactive_at", "TEXT"),
    ("projects", "objective", "TEXT"),
    ("projects", "requester_id", "INTEGER"),
    ("projects", "coordinator_id", "INTEGER"),
    ("projects", "status", "TEXT DEFAULT 'em andamento'"),
    ("bookings", "service_id", "INTEGER"),
    ("maintenance_preventive", "is_active", "INTEGER DEFAULT 1"),
    ("maintenance_preventive", "inactive_reason", "TEXT"),
    ("maintenance_preventive", "inactive_by_id", "INTEGER"),
    ("maintenance_preventive", "inactive_at", "TEXT"),
    ("maintenance_corrective", "is_active", "INTEGER DEFAULT 1"),
    ("maintenance_corrective", "inactive_reason", "TEXT"),
    ("maintenance_corrective", "inactive_by_id", "INTEGER"),
    ("maintenance_corrective", "inactive_at", "TEXT"),
    ("supplies", "supply_type", "TEXT DEFAULT 'Insumo'"),
    ("supplies", "supply_code", "TEXT"),
    ("supplies", "manufacturer_code", "TEXT"),
    ("supplies", "compatible_model_family", "TEXT"),
    ("supply_movements", "service_id", "INTEGER"),
    ("supply_movements", "supply_lot_id", "INTEGER"),
)


INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_project_services_project ON project_services (project_id, active, status);
CREATE INDEX IF NOT EXISTS idx_project_services_code ON project_services (service_code);
CREATE INDEX IF NOT EXISTS idx_maintenance_status_history_entity ON maintenance_status_history (entity_type, entity_id, changed_at);
CREATE INDEX IF NOT EXISTS idx_supply_lots_supply_active_expiration ON supply_lots (supply_id, is_active, expiration_date);
CREATE INDEX IF NOT EXISTS idx_supply_lots_code ON supply_lots (lot_code);
CREATE INDEX IF NOT EXISTS idx_supply_movements_supply_date ON supply_movements (supply_id, movement_date);
CREATE INDEX IF NOT EXISTS idx_equipment_spare_parts_equipment ON equipment_spare_parts (equipment_id, is_active);
CREATE INDEX IF NOT EXISTS idx_equipment_spare_parts_supply ON equipment_spare_parts (supply_id, is_active);
CREATE INDEX IF NOT EXISTS idx_attachments_entity ON attachments (entity_type, entity_id, is_active);
CREATE INDEX IF NOT EXISTS idx_attachments_sha256 ON attachments (sha256);
CREATE INDEX IF NOT EXISTS idx_bookings_service ON bookings (service_id);
CREATE INDEX IF NOT EXISTS idx_supply_movements_service ON supply_movements (service_id);
CREATE INDEX IF NOT EXISTS idx_supply_movements_lot ON supply_movements (supply_lot_id);
CREATE INDEX IF NOT EXISTS idx_bookings_equipment_period_status ON bookings (equipment_id, start_datetime, end_datetime, status);
CREATE INDEX IF NOT EXISTS idx_bookings_start_datetime ON bookings (start_datetime);
CREATE INDEX IF NOT EXISTS idx_booking_status_history_booking_changed ON booking_status_history (booking_id, changed_at);
CREATE INDEX IF NOT EXISTS idx_booking_status_history_changed_at ON booking_status_history (changed_at);
CREATE INDEX IF NOT EXISTS idx_booking_status_history_changed_by ON booking_status_history (changed_by_id, changed_at);
CREATE INDEX IF NOT EXISTS idx_supply_movements_movement_date ON supply_movements (movement_date);
CREATE INDEX IF NOT EXISTS idx_supply_movements_project_service_date ON supply_movements (project_id, service_id, movement_date);
CREATE INDEX IF NOT EXISTS idx_supply_movements_lot_date ON supply_movements (supply_lot_id, movement_date);
CREATE INDEX IF NOT EXISTS idx_supply_lots_active_expiration ON supply_lots (is_active, expiration_date);
CREATE INDEX IF NOT EXISTS idx_attachments_entity_role_active ON attachments (entity_type, attachment_role, is_active, entity_id);
"""
