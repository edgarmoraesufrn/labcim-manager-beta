## cd C:\Moraes\Pesquisa\LabCim\Reservas\LabCim_Manager_Fase1_3\labcim_manager
## python -m venv .venv
## Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
## .venv\Scripts\activate
## pip install -r requirements.txt
## streamlit run app.py

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from email.message import EmailMessage
import hashlib
from html import escape
from io import BytesIO
from numbers import Integral, Real
import os
import secrets as py_secrets
import smtplib
import zipfile
from pathlib import Path
import re

import pandas as pd
import plotly.express as px
import qrcode
import streamlit as st

from labcim_manager.db import (
    connect,
    create_attachment,
    create_booking,
    create_corrective_ticket,
    create_equipment,
    create_access_code_record,
    create_preventive_activity,
    create_project,
    create_supply,
    create_supply_movement,
    create_user,
    get_active_user_by_email,
    get_attachment,
    get_latest_attachment_for_entity,
    import_base_xlsx,
    init_db,
    is_operational_database_empty,
    list_attachments,
    list_equipment_for_spare_part,
    list_spare_parts_for_equipment,
    log_notification,
    query_df,
    seed_default_pops,
    set_spare_part_equipment_links,
    table_counts,
    update_booking_status,
    update_corrective_status,
    update_equipment_master,
    update_equipment_operational_info,
    update_legacy_attachment_path,
    update_project,
    update_supply,
    update_user,
    verify_access_code_record,
)
from labcim_manager.storage import (
    LocalStorageBackend,
    R2StorageBackend,
    StorageConfigurationError,
    get_active_storage_backend,
    get_storage_backend_for_name,
)

APP_TITLE = "LabCim Manager"
APP_SUBTITLE = "Sistema de Gestão de Estoque, Equipamentos, Reservas e Manutenção do LabCim"
DB_PATH = Path("data/labcim_manager.db")
BASE_XLSX = Path("data/LabCim_Base.xlsx")
LOGO_PATH = Path("assets/logo_labcim.png")
POP_DIR = Path("assets/pops")
ACCESS_CODE_TTL_MINUTES = 10

LAB_BLUE = "#0033A0"
LAB_CYAN = "#00AEEF"
LAB_DARK = "#102A43"
LAB_BG = "#F7FAFC"


STATUS_LABELS = {
    "scheduled": "Agendada",
    "done": "Concluída",
    "cancelled": "Cancelada",
    "no_show": "Não compareceu",
}
STATUS_REVERSE = {v: k for k, v in STATUS_LABELS.items()}

EQUIPMENT_STATUS_LABELS = {
    "available": "Apto",
    "restricted": "Uso restrito",
    "maintenance": "Em manutenção",
    "inactive": "Inativo",
}
EQUIPMENT_STATUS_REVERSE = {v: k for k, v in EQUIPMENT_STATUS_LABELS.items()}

ROLE_LABELS = {
    "member": "Membro",
    "manager": "Gerente",
    "admin": "Administrador",
}
ROLE_REVERSE = {v: k for k, v in ROLE_LABELS.items()}

BOOLEAN_LABELS = {0: "Não", 1: "Sim", False: "Não", True: "Sim"}
SUPPLY_TYPES = ["Insumo", "Peça de reposição"]

PAGE_LABELS = [
    "Painel inicial",
    "Reservas",
    "Equipamentos",
    "Insumos",
    "Usuários",
    "Projetos",
    "Manutenção",
    "QR Codes",
    "Relatórios",
    "Importar base",
]

COLUMN_LABELS = {
    "id": "ID",
    "equipment_code": "Código",
    "equipment_name": "Equipamento",
    "lab_unit": "Unidade",
    "location": "Localização",
    "requires_operator": "Requer operador?",
    "operational_status": "Status operacional",
    "unavailable_functions": "Funcionalidades indisponíveis",
    "max_sample_capacity": "Capacidade máxima",
    "capacity_unit": "Unidade da capacidade",
    "capacity_enforced": "Bloqueia acima da capacidade?",
    "technical_manager": "Gestor técnico",
    "pop_title": "POP",
    "pop_path": "Arquivo POP",
    "pop_version": "Versão do POP",
    "pop_updated_at": "Atualização do POP",
    "pop_responsible": "Responsável pelo POP",
    "document_notes": "Observações documentais",
    "responsible_name": "Responsável",
    "responsible_phone": "Telefone do responsável",
    "supply_type": "Tipo de item",
    "supply_name": "Insumo",
    "supply_code": "Código interno",
    "commercial_name": "Nome comercial",
    "manufacturer": "Fabricante",
    "manufacturer_code": "Código do fabricante",
    "category": "Categoria",
    "physical_state": "Estado físico",
    "application_function": "Função/aplicação",
    "addition_mode": "Modo de adição",
    "compatible_model_family": "Modelo/família compatível",
    "unit": "Unidade",
    "current_quantity": "Saldo atual",
    "minimum_quantity": "Estoque mínimo",
    "lot": "Lote",
    "expiration_date": "Validade",
    "safety_doc_path": "FDS/FISPQ",
    "technical_doc_path": "Ficha técnica/caracterização",
    "density": "Massa específica",
    "recommended_concentration": "Faixa de concentração",
    "recommended_temperature": "Faixa de temperatura",
    "characterization_summary": "Caracterização",
    "movement_type": "Movimentação",
    "movement_date": "Data",
    "quantity": "Quantidade",
    "document_path": "Documento",
    "stock_status": "Status de estoque",
    "association_notes": "Observação da associação",
    "active": "Ativo?",
    "is_active": "Ativo?",
    "association_active": "Associação ativa?",
    "notes": "Observações",
    "created_at": "Criado em",
    "full_name": "Nome completo",
    "phone_e164": "Celular",
    "role": "Perfil",
    "department": "Departamento/Programa",
    "advisor_name": "Orientador(a)",
    "email": "E-mail",
    "training_completed": "Treinamento concluído?",
    "project_code": "Código do projeto",
    "project_name": "Projeto",
    "funding_source": "Fonte de financiamento",
    "start_date": "Início do projeto",
    "end_date": "Fim do projeto",
    "start_datetime": "Início",
    "end_datetime": "Fim",
    "sample_count": "Amostras",
    "purpose": "Finalidade/observações",
    "status": "Status",
    "operator": "Operador",
    "executante": "Executante",
    "solicitante": "Solicitante",
    "performed_by": "Executante",
    "blocks_booking": "Bloqueia reservas?",
    "planned_end_date": "Fim previsto",
}


def setup_page() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🔬", layout="wide")
    st.markdown(
        f"""
        <style>
        .stApp {{ background: {LAB_BG}; }}
        .stApp, .stMarkdown, .stText, p, label, span, div {{
            color: {LAB_DARK};
        }}
        .main .block-container {{ padding-top: 1.5rem; padding-bottom: 3rem; }}
        h1, h2, h3 {{ color: {LAB_DARK}; }}
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #FFFFFF 0%, #EEF7FF 100%);
            border-right: 1px solid #E6EEF8;
        }}
        [data-testid="stSidebar"] * {{
            color: {LAB_DARK} !important;
        }}
        [data-testid="stSidebar"] [role="radiogroup"] label {{
            color: {LAB_DARK} !important;
            opacity: 1 !important;
        }}
        .lab-hero {{
            background: linear-gradient(135deg, {LAB_BLUE} 0%, #0B4FD4 45%, {LAB_CYAN} 100%);
            color: white; padding: 1.25rem 1.5rem; border-radius: 22px;
            box-shadow: 0 12px 30px rgba(0, 51, 160, 0.18);
            margin-bottom: 1rem;
        }}
        .lab-hero, .lab-hero * {{ color: #FFFFFF !important; }}
        .lab-hero h1 {{ margin: 0; font-size: 2.1rem; font-weight: 850; }}
        .lab-hero p {{ margin: .35rem 0 0 0; opacity: .98; font-size: 1rem; }}
        .metric-card {{
            background: white; border: 1px solid #E6EEF8; border-radius: 18px; padding: 1rem;
            box-shadow: 0 8px 20px rgba(16, 42, 67, .06);
        }}
        .soft-card {{
            background: white; border: 1px solid #E6EEF8; border-radius: 18px; padding: 1rem;
            box-shadow: 0 8px 20px rgba(16, 42, 67, .05);
            color: {LAB_DARK};
        }}
        .soft-card, .soft-card * {{ color: {LAB_DARK} !important; opacity: 1 !important; }}
        .success-card {{
            background: linear-gradient(135deg, #ECFDF3 0%, #F7FFF9 100%);
            border: 1px solid #86EFAC;
            border-left: 7px solid #16A34A;
            border-radius: 18px;
            padding: 1rem 1.15rem;
            margin: .75rem 0 1rem 0;
            box-shadow: 0 10px 24px rgba(22, 163, 74, .10);
        }}
        .success-card, .success-card * {{ color: #14532D !important; opacity: 1 !important; }}
        .success-card-title {{ font-size: 1.08rem; font-weight: 850; margin-bottom: .25rem; }}
        .calendar-shell {{
            background: white; border: 1px solid #D9EAFB; border-radius: 20px;
            padding: .75rem; box-shadow: 0 8px 20px rgba(16, 42, 67, .05);
        }}
        .calendar-grid-week {{
            display: grid; grid-template-columns: repeat(7, minmax(120px, 1fr)); gap: .55rem;
        }}
        .calendar-grid-month {{
            display: grid; grid-template-columns: repeat(7, minmax(105px, 1fr)); gap: .35rem;
        }}
        .calendar-day {{
            min-height: 155px; border: 1px solid #E6EEF8; border-radius: 16px; padding: .55rem;
            background: #FBFDFF;
        }}
        .calendar-day-muted {{ background: #F3F7FB; opacity: .72; }}
        .calendar-today {{ border: 2px solid {LAB_CYAN}; background: #F2FBFF; }}
        .calendar-head {{
            font-weight: 800; color: {LAB_DARK}; font-size: .92rem; margin-bottom: .35rem;
        }}
        .calendar-date {{
            color: #627D98; font-size: .78rem; font-weight: 600;
        }}
        .calendar-pill {{
            display: block; border-radius: 10px; padding: .38rem .45rem; margin-top: .35rem;
            font-size: .76rem; line-height: 1.15rem; border-left: 4px solid #0033A0;
            background: #EEF7FF; color: #102A43;
        }}
        .calendar-pill-done {{ background: #ECFDF3; border-left-color: #2E7D32; }}
        .calendar-pill-cancelled {{ background: #F3F4F6; border-left-color: #9CA3AF; color: #6B7280; text-decoration: line-through; }}
        .calendar-pill-maintenance {{ background: #FFF7ED; border-left-color: #F97316; }}
        .calendar-pill-restricted {{ background: #FEFCE8; border-left-color: #CA8A04; }}
        .calendar-more {{ color: #627D98; font-size: .75rem; margin-top: .35rem; }}
        div[data-testid="stMetricValue"] {{ color: {LAB_BLUE}; }}
        div[data-testid="stMetricLabel"] {{ color: {LAB_DARK}; opacity: 1; }}
        .stButton>button {{ border-radius: 12px; border: 1px solid {LAB_CYAN}; }}
        .stDownloadButton>button {{ border-radius: 12px; }}
        .stButton>button,
        .stDownloadButton>button {{
            font-weight: 750 !important;
            color: {LAB_DARK} !important;
        }}
        div[data-testid="stFormSubmitButton"] button,
        .stFormSubmitButton button,
        button[data-testid="stBaseButton-primary"],
        div[data-testid="stBaseButton-primary"] button,
        .stButton>button[kind="primary"] {{
            background: {LAB_BLUE} !important;
            color: #FFFFFF !important;
            border: 1px solid {LAB_BLUE} !important;
            box-shadow: 0 8px 18px rgba(0, 51, 160, .18);
            font-weight: 800 !important;
        }}
        div[data-testid="stFormSubmitButton"] button *,
        .stFormSubmitButton button *,
        button[data-testid="stBaseButton-primary"] *,
        div[data-testid="stBaseButton-primary"] button *,
        .stButton>button[kind="primary"] * {{
            color: #FFFFFF !important;
            opacity: 1 !important;
        }}
        div[data-testid="stFormSubmitButton"] button:hover,
        .stFormSubmitButton button:hover,
        .stButton>button:hover {{
            border-color: {LAB_BLUE} !important;
            filter: brightness(.98);
        }}

        /* Tema claro robusto para widgets do Streamlit/BaseWeb */
        [data-testid="stSelectbox"] div[data-baseweb="select"],
        [data-testid="stMultiSelect"] div[data-baseweb="select"],
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] > div {{
            background-color: #FFFFFF !important;
            color: {LAB_DARK} !important;
            border-color: #CBD5E1 !important;
        }}
        [data-testid="stSelectbox"] div[data-baseweb="select"] *,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] *,
        [data-testid="stSelectbox"] span,
        [data-testid="stMultiSelect"] span {{
            color: {LAB_DARK} !important;
            fill: {LAB_DARK} !important;
            opacity: 1 !important;
        }}
        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        .stDateInput input,
        .stTimeInput input {{
            color: {LAB_DARK} !important;
            background-color: #FFFFFF !important;
            border-color: #CBD5E1 !important;
        }}
        [data-baseweb="popover"],
        [data-baseweb="popover"] > div,
        [data-baseweb="menu"],
        [role="listbox"],
        [data-baseweb="calendar"] {{
            background-color: #FFFFFF !important;
            color: {LAB_DARK} !important;
            border-color: #CBD5E1 !important;
        }}
        [data-baseweb="popover"] *,
        [data-baseweb="menu"] *,
        [role="listbox"] *,
        [data-baseweb="calendar"] *,
        div[role="option"] {{
            color: {LAB_DARK} !important;
            background-color: transparent !important;
            opacity: 1 !important;
        }}
        div[role="option"]:hover {{
            background-color: #EEF7FF !important;
        }}
        .stTabs [data-baseweb="tab-list"] {{
            gap: .45rem;
            border-bottom: 1px solid #D9E2EC;
            padding-bottom: .45rem;
            margin-bottom: .75rem;
        }}
        .stTabs [data-baseweb="tab"] {{
            color: {LAB_DARK} !important;
            background: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 999px !important;
            padding: .45rem .9rem !important;
            font-weight: 750 !important;
            box-shadow: 0 4px 10px rgba(16, 42, 67, .04);
        }}
        .stTabs [data-baseweb="tab"] * {{
            color: {LAB_DARK} !important;
            opacity: 1 !important;
        }}
        .stTabs [aria-selected="true"] {{
            background: {LAB_BLUE} !important;
            border-color: {LAB_BLUE} !important;
            color: #FFFFFF !important;
            font-weight: 850 !important;
            box-shadow: 0 8px 18px rgba(0, 51, 160, .18);
        }}
        .stTabs [aria-selected="true"] * {{ color: #FFFFFF !important; }}
        .stTabs [data-baseweb="tab-highlight"] {{ background: transparent !important; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _database_url() -> str | None:
    for key in ("DATABASE_URL", "database_url"):
        try:
            if hasattr(st, "secrets") and key in st.secrets:
                value = str(st.secrets[key]).strip()
                if value:
                    return value
        except Exception:
            pass
    try:
        if hasattr(st, "secrets") and "database" in st.secrets:
            database_secrets = st.secrets["database"]
            for key in ("url", "DATABASE_URL", "database_url"):
                if key in database_secrets:
                    value = str(database_secrets[key]).strip()
                    if value:
                        return value
    except Exception:
        pass
    return os.environ.get("DATABASE_URL") or None


def get_conn():
    conn = connect(DB_PATH, database_url=_database_url())
    init_db(conn)
    if BASE_XLSX.exists() and is_operational_database_empty(conn):
        import_base_xlsx(conn, BASE_XLSX)
    seed_default_pops(conn)
    return conn


def _secret_value(*keys: str, default: str | None = None) -> str | None:
    for key in keys:
        try:
            if hasattr(st, "secrets") and key in st.secrets:
                return st.secrets[key]
        except Exception:
            pass
        try:
            if hasattr(st, "secrets") and "email" in st.secrets and key in st.secrets["email"]:
                return st.secrets["email"][key]
        except Exception:
            pass
        env_value = os.environ.get(key)
        if env_value:
            return env_value
    return default


def _email_config() -> dict[str, str | int | bool | None]:
    host = _secret_value("LABCIM_SMTP_HOST", "smtp_host")
    port = int(_secret_value("LABCIM_SMTP_PORT", "smtp_port", default="587") or "587")
    user = _secret_value("LABCIM_SMTP_USER", "smtp_user")
    password = _secret_value("LABCIM_SMTP_PASSWORD", "smtp_password")
    sender = _secret_value("LABCIM_SMTP_FROM", "smtp_from", default=user or "LabCim Manager <no-reply@labcim.local>")
    tls_raw = str(_secret_value("LABCIM_SMTP_TLS", "smtp_tls", default="true")).lower()
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "sender": sender,
        "use_tls": tls_raw not in {"0", "false", "nao", "não", "no"},
    }


def email_is_configured() -> bool:
    cfg = _email_config()
    return bool(cfg["host"] and cfg["user"] and cfg["password"])


def send_email(to_email: str, subject: str, body: str) -> tuple[bool, str]:
    cfg = _email_config()
    if not email_is_configured():
        return False, "SMTP não configurado."
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = str(cfg["sender"])
    msg["To"] = to_email
    msg.set_content(body)
    try:
        with smtplib.SMTP(str(cfg["host"]), int(cfg["port"]), timeout=20) as smtp:
            if cfg["use_tls"]:
                smtp.starttls()
            smtp.login(str(cfg["user"]), str(cfg["password"]))
            smtp.send_message(msg)
        return True, "E-mail enviado."
    except Exception as exc:
        return False, str(exc)


def _unique_emails(values) -> list[str]:
    seen = set()
    emails: list[str] = []
    for value in values:
        email = clean_input(value).lower()
        if email and "@" in email and email not in seen:
            emails.append(email)
            seen.add(email)
    return emails


def maintenance_notification_recipients(conn, equipment_id: int, include_future_users: bool = True) -> list[str]:
    manager_rows = conn.execute(
        """
        SELECT email
        FROM users
        WHERE active = 1
          AND email IS NOT NULL
          AND TRIM(email) != ''
          AND role IN ('admin', 'manager')
        """
    ).fetchall()
    specific_rows = conn.execute(
        """
        SELECT DISTINCT u.email
        FROM equipment e
        JOIN users u
          ON u.active = 1
         AND u.email IS NOT NULL
         AND TRIM(u.email) != ''
         AND (
             LOWER(u.full_name) = LOWER(COALESCE(e.responsible_name, ''))
             OR LOWER(u.full_name) = LOWER(COALESCE(e.technical_manager, ''))
         )
        WHERE e.id = ?
        """,
        [equipment_id],
    ).fetchall()
    emails = [r["email"] for r in manager_rows] + [r["email"] for r in specific_rows]
    if include_future_users:
        now_iso = datetime.now().isoformat(timespec="minutes")
        future_rows = conn.execute(
            """
            SELECT DISTINCT u.email
            FROM bookings b
            JOIN users u ON u.id = b.user_id
            WHERE b.equipment_id = ?
              AND b.status = 'scheduled'
              AND b.start_datetime >= ?
              AND u.active = 1
              AND u.email IS NOT NULL
              AND TRIM(u.email) != ''
            """,
            [equipment_id, now_iso],
        ).fetchall()
        emails.extend([r["email"] for r in future_rows])
    return _unique_emails(emails)


def notify_equipment_maintenance(
    conn,
    *,
    equipment_id: int,
    title: str,
    message: str,
    related_table: str,
    related_id: int | None = None,
    include_future_users: bool = True,
) -> tuple[int, int]:
    equipment = conn.execute("SELECT * FROM equipment WHERE id = ?", [equipment_id]).fetchone()
    if not equipment:
        return 0, 0
    recipients = maintenance_notification_recipients(conn, equipment_id, include_future_users=include_future_users)
    subject = f"LabCim Manager - {title}: {equipment['equipment_code']}"
    body = (
        f"Equipamento: {equipment['equipment_code']} — {equipment['equipment_name']}\n"
        f"Localização: {clean_value(equipment['location'])}\n"
        f"Responsável: {clean_value(equipment['responsible_name'])}\n\n"
        f"{message}\n\n"
        "Esta é uma notificação automática do LabCim Manager."
    )
    sent = 0
    total = 0
    for email in recipients:
        total += 1
        ok, error = send_email(email, subject, body)
        if ok:
            sent += 1
        log_notification(
            conn,
            event_type="equipment_maintenance",
            recipient_email=email,
            subject=subject,
            body=body,
            status="sent" if ok else "skipped_no_smtp" if not email_is_configured() else "error",
            error_message=None if ok else error,
            related_table=related_table,
            related_id=related_id or equipment_id,
        )
    return sent, total


def _hash_access_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _normalize_session_role(role: str | None) -> str:
    role = clean_input(role).lower()
    if role in {"admin", "manager", "member"}:
        return role
    if role in {"operator", "operador", "gerente"}:
        return "manager"
    return "member"


def is_authenticated() -> bool:
    return bool(st.session_state.get("auth_user"))


def current_user() -> dict:
    return st.session_state.get("auth_user", {})


def _set_authenticated_user(row) -> None:
    role = _normalize_session_role(row["role"])
    st.session_state["auth_user"] = {
        "id": int(row["user_id"] if "user_id" in row.keys() else row["id"]),
        "full_name": str(row["full_name"]),
        "email": str(row["user_email"] if "user_email" in row.keys() else row["email"]),
        "role": role,
    }
    st.session_state["access_role"] = role


def logout() -> None:
    for key in ["auth_user", "access_role", "pending_login_email", "last_access_code"]:
        if key in st.session_state:
            del st.session_state[key]


def request_access_code(conn, email: str) -> tuple[bool, str]:
    user = get_active_user_by_email(conn, email)
    if not user:
        return False, "E-mail não encontrado entre usuários ativos do LabCim Manager."
    code = f"{py_secrets.randbelow(1_000_000):06d}"
    expires_at = (datetime.now() + timedelta(minutes=ACCESS_CODE_TTL_MINUTES)).isoformat(timespec="seconds")
    create_access_code_record(
        conn,
        user_id=int(user["id"]),
        email=str(user["email"]).strip().lower(),
        code_hash=_hash_access_code(code),
        expires_at=expires_at,
    )
    subject = "Código de acesso - LabCim Manager"
    body = (
        f"Olá, {user['full_name']}.\n\n"
        f"Seu código de acesso ao LabCim Manager é: {code}\n\n"
        f"Ele expira em {ACCESS_CODE_TTL_MINUTES} minutos.\n"
        "Se você não solicitou este acesso, ignore esta mensagem.\n\n"
        "LabCim Manager"
    )
    ok, msg = send_email(str(user["email"]), subject, body)
    log_notification(
        conn,
        event_type="access_code",
        recipient_email=str(user["email"]),
        subject=subject,
        body=body if not ok else "Código de acesso enviado por e-mail.",
        status="sent" if ok else "beta_code_available",
        error_message=None if ok else msg,
        related_table="users",
        related_id=int(user["id"]),
    )
    st.session_state["pending_login_email"] = str(user["email"]).strip().lower()
    if not ok:
        st.session_state["last_access_code"] = code
        return True, "SMTP ainda não configurado. Modo beta: o código foi exibido na tela."
    st.session_state.pop("last_access_code", None)
    return True, f"Código enviado para {user['email']}."


def page_login(conn) -> None:
    hero()
    st.subheader("Acesso ao sistema")
    st.caption("Digite seu e-mail cadastrado. O sistema enviará uma senha volátil com validade curta.")

    with st.container(border=True):
        st.markdown("### Solicitar senha volátil")
        email = st.text_input(
            "E-mail cadastrado",
            value=clean_input(st.session_state.get("pending_login_email", "")),
            placeholder="seu.email@ufrn.br",
            key="login_email",
        ).strip().lower()
        if st.button("Enviar senha volátil", type="primary", key="send_access_code"):
            ok, msg = request_access_code(conn, email)
            (st.success if ok else st.error)(msg)

        if st.session_state.get("last_access_code"):
            st.warning(
                f"Modo beta local: código de teste **{st.session_state['last_access_code']}**. "
                "Configure o SMTP para ocultar este código e enviar somente por e-mail."
            )

    with st.container(border=True):
        st.markdown("### Validar código")
        pending_email = clean_input(st.session_state.get("pending_login_email", "")).lower()
        if pending_email:
            st.info(f"Validando acesso para: **{pending_email}**")
        else:
            st.warning("Primeiro solicite uma senha volátil para o seu e-mail.")
        code = st.text_input(
            "Código recebido",
            max_chars=6,
            placeholder="000000",
            key="verify_code",
        ).strip()
        if st.button("Entrar", type="primary", key="verify_access_code"):
            if not pending_email:
                st.error("Solicite uma senha volátil antes de validar o código.")
                return
            if not code:
                st.error("Informe o código recebido por e-mail.")
                return
            ok, msg, row = verify_access_code_record(conn, email=pending_email, code_hash=_hash_access_code(code))
            if ok and row is not None:
                _set_authenticated_user(row)
                st.success("Acesso liberado.")
                st.rerun()
            else:
                st.error(msg)

    if not email_is_configured():
        with st.expander("Configuração de e-mail SMTP para produção"):
            st.code(
                """
# .streamlit/secrets.toml
[email]
smtp_host = "smtp.seudominio.br"
smtp_port = 587
smtp_user = "usuario@seudominio.br"
smtp_password = "COLE_AQUI_A_SENHA_DE_APP"
smtp_from = "LabCim Manager <usuario@seudominio.br>"
smtp_tls = true
                """.strip(),
                language="toml",
            )


def hero():
    cols = st.columns([1, 4])
    with cols[0]:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), use_container_width=True)
        else:
            st.markdown("# 🔬")
    with cols[1]:
        st.markdown(
            f"""
            <div class="lab-hero">
                <h1>{APP_TITLE}</h1>
                <p>{APP_SUBTITLE}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _initial_page_from_url() -> str:
    view = st.query_params.get("view", "")
    if view == "reserva":
        return "Reservas"
    if view == "manutencao":
        return "Manutenção"
    if view == "insumo":
        return "Insumos"
    if view == "pop":
        return "Reservas"
    return "Painel inicial"


def sidebar(default_page: str | None = None):
    if LOGO_PATH.exists():
        st.sidebar.image(str(LOGO_PATH), use_container_width=True)
    st.sidebar.markdown("### LabCim Manager")
    selected_default = default_page or _initial_page_from_url()
    index = PAGE_LABELS.index(selected_default) if selected_default in PAGE_LABELS else 0
    page = st.sidebar.radio("Navegação", PAGE_LABELS, index=index)
    st.sidebar.markdown("---")
    user = current_user()
    st.sidebar.markdown(f"**Usuário:** {clean_value(user.get('full_name'))}")
    st.sidebar.caption(f"{clean_value(user.get('email'))} · {role_badge(user.get('role'))}")
    if current_access_role() == "admin":
        st.sidebar.success("Administrador")
    elif current_access_role() == "manager":
        st.sidebar.info("Gerente")
    else:
        st.sidebar.caption("Membro")
    if st.sidebar.button("Sair"):
        logout()
        st.rerun()
    return page


def current_access_role() -> str:
    if st.session_state.get("access_role"):
        return st.session_state.get("access_role", "member")
    user = current_user()
    return _normalize_session_role(user.get("role")) if user else "member"


def is_admin() -> bool:
    return current_access_role() == "admin"


def can_manage_master_data() -> bool:
    return current_access_role() in {"manager", "admin"}


def can_edit_operational_data() -> bool:
    return current_access_role() in {"manager", "admin"}


def admin_required_message(action: str = "alterar cadastros estruturais") -> None:
    st.info(f"Para {action}, selecione perfil Gerente ou Administrador. Este bloqueio será ligado ao login na próxima etapa.")


def status_badge(value: str) -> str:
    if is_blank(value):
        return "-"
    return STATUS_LABELS.get(value, value)


def equipment_status_badge(value: str) -> str:
    if is_blank(value):
        return "Apto"
    return EQUIPMENT_STATUS_LABELS.get(str(value), str(value))


def role_badge(value: str) -> str:
    if is_blank(value):
        return "-"
    if str(value).lower() in {"operator", "operador", "gerente"}:
        return "Gerente"
    return ROLE_LABELS.get(value, value)


def is_blank(value) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except Exception:
        pass
    text = str(value).strip()
    return text == "" or text.lower() in {"nan", "none", "nat"}


def clean_value(value, default: str = "-") -> str:
    if is_blank(value):
        return default
    return str(value).strip()


def clean_input(value) -> str:
    return "" if is_blank(value) else str(value).strip()


def truthy(value) -> bool:
    if is_blank(value):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, Integral):
        return int(value) == 1
    if isinstance(value, Real):
        return float(value) == 1.0
    text = str(value).strip().lower()
    return text in {"1", "true", "sim", "yes", "y", "ativo"}


def yes_no(value) -> str:
    if is_blank(value):
        return "-"
    return "Sim" if truthy(value) else "Não"


def _format_datetime(value: str | None) -> str:
    if not value:
        return "-"
    try:
        text = str(value)
        parsed = datetime.fromisoformat(text)
        if len(text) == 10:
            return parsed.strftime("%d/%m/%Y")
        return parsed.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(value)


def _date_input_value(value, default=None):
    if is_blank(value):
        return default
    try:
        return datetime.fromisoformat(str(value)).date()
    except Exception:
        try:
            return pd.to_datetime(value).date()
        except Exception:
            return default


def _resolve_local_doc(path_value) -> Path | None:
    path_text = clean_input(path_value)
    if not path_text:
        return None
    path = Path(path_text)
    if not path.is_absolute():
        path = Path.cwd() / path
    try:
        path = path.resolve()
        cwd = Path.cwd().resolve()
        if cwd not in path.parents and path != cwd:
            return None
    except Exception:
        return None
    return path if path.exists() and path.is_file() else None


def pop_download_button(equipment_row, key_prefix: str = "pop") -> None:
    raw_path = clean_input(equipment_row.get("pop_path"))
    if raw_path.lower().startswith(("http://", "https://")):
        st.link_button(f"📄 Abrir {clean_value(equipment_row.get('pop_title'), 'POP do equipamento')}", raw_path)
        return
    doc_path = _resolve_local_doc(raw_path)
    title = clean_value(equipment_row.get("pop_title"), "POP do equipamento")
    version = clean_value(equipment_row.get("pop_version"), "sem versão")
    responsible = clean_value(equipment_row.get("pop_responsible"))
    if doc_path:
        st.download_button(
            f"📄 Baixar {title}",
            data=doc_path.read_bytes(),
            file_name=doc_path.name,
            mime="application/pdf",
            key=f"{key_prefix}_{clean_value(equipment_row.get('equipment_code'), 'eq')}",
            help=f"{title} · {version} · Responsável: {responsible}",
        )
    else:
        st.info("Nenhum POP/documento operacional cadastrado para este equipamento.")


def _display_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in ["status"]:
        if c in out.columns:
            out[c] = out[c].map(status_badge).fillna(out[c])
    for c in ["operational_status"]:
        if c in out.columns:
            out[c] = out[c].map(equipment_status_badge).fillna(out[c])
    for c in ["role"]:
        if c in out.columns:
            out[c] = out[c].map(role_badge).fillna(out[c])
    for c in ["active", "is_active", "association_active", "requires_operator", "training_completed", "capacity_enforced", "blocks_booking"]:
        if c in out.columns:
            out[c] = out[c].map(yes_no)
    for c in [
        "start_datetime",
        "end_datetime",
        "created_at",
        "updated_at",
        "occurrence_datetime",
        "expiration_date",
        "movement_date",
        "planned_date",
        "planned_end_date",
        "performed_date",
        "next_date",
        "conclusion_date",
        "start_date",
        "end_date",
    ]:
        if c in out.columns:
            out[c] = out[c].map(_format_datetime)
    return out.rename(columns=COLUMN_LABELS)


def load_reference_data(conn):
    equipment = query_df(conn, "SELECT * FROM equipment ORDER BY active DESC, equipment_code")
    users = query_df(conn, "SELECT * FROM users ORDER BY active DESC, full_name")
    projects = query_df(conn, "SELECT * FROM projects ORDER BY active DESC, project_name")
    operators = users[users["role"].isin(["manager", "operator", "admin"])] if not users.empty else users
    return equipment, users, projects, operators


def page_dashboard(conn):
    hero()
    st.subheader("Visão geral da base LabCim")
    counts = table_counts(conn)
    metrics = [
        ("Equipamentos", counts["equipment"]),
        ("Usuários", counts["users"]),
        ("Projetos", counts["projects"]),
        ("Reservas", counts["bookings"]),
        ("Preventivas", counts.get("maintenance_preventive", 0)),
        ("Corretivas", counts.get("maintenance_corrective", 0)),
        ("Insumos", counts.get("supplies", 0)),
    ]
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.metric(label, value)

    st.markdown("---")
    equipment = query_df(conn, "SELECT lab_unit, active, COUNT(*) AS total FROM equipment GROUP BY lab_unit, active")
    users = query_df(conn, "SELECT lab_unit, role, COUNT(*) AS total FROM users GROUP BY lab_unit, role")
    bookings = query_df(
        conn,
        """
        SELECT b.id, e.equipment_code, e.equipment_name, u.full_name, p.project_name,
               b.start_datetime, b.end_datetime, b.status, b.sample_count
        FROM bookings b
        JOIN equipment e ON e.id=b.equipment_id
        JOIN users u ON u.id=b.user_id
        LEFT JOIN projects p ON p.id=b.project_id
        ORDER BY b.start_datetime DESC
        LIMIT 12
        """,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Equipamentos por unidade")
        if not equipment.empty:
            fig = px.bar(
                equipment,
                x="lab_unit",
                y="total",
                color="active",
                barmode="group",
                labels={"lab_unit": "Unidade", "total": "Quantidade", "active": "Ativo"},
                color_discrete_sequence=[LAB_CYAN, LAB_BLUE],
            )
            fig.update_layout(height=360, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum equipamento cadastrado.")
    with c2:
        st.markdown("#### Usuários por perfil")
        if not users.empty:
            fig = px.bar(
                users,
                x="role",
                y="total",
                color="lab_unit",
                barmode="group",
                labels={"role": "Perfil", "total": "Quantidade", "lab_unit": "Unidade"},
                color_discrete_sequence=[LAB_BLUE, LAB_CYAN, "#6BAED6"],
            )
            fig.update_layout(height=360, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum usuário cadastrado.")

    st.markdown("#### Últimas reservas")
    if bookings.empty:
        st.info("Ainda não há reservas registradas.")
    else:
        st.dataframe(_display_df(bookings), use_container_width=True, hide_index=True)

    supplies = query_df(conn, "SELECT * FROM supplies WHERE active=1")
    if not supplies.empty:
        supplies["alerta"] = supplies.apply(_supply_alert_status, axis=1)
        critical = supplies[supplies["alerta"].isin(["Estoque baixo", "Vencido", "Vence em até 60 dias"])]
        if not critical.empty:
            st.markdown("#### Alertas de insumos")
            st.dataframe(
                _display_df(critical[["alerta", "supply_name", "current_quantity", "unit", "minimum_quantity", "expiration_date", "location"]]),
                use_container_width=True,
                hide_index=True,
            )


def _select_index_by_code(equipment: pd.DataFrame, code: str | None) -> int:
    if not code or equipment.empty:
        return 0
    codes = [str(c).upper() for c in equipment["equipment_code"].tolist()]
    code = str(code).upper()
    return codes.index(code) if code in codes else 0


def _user_options(users: pd.DataFrame) -> list[str]:
    return users.apply(lambda r: f"{clean_value(r.get('full_name'))} ({clean_value(r.get('department'), 'sem vínculo')})", axis=1).tolist()


def _project_options(projects: pd.DataFrame) -> list[str]:
    if projects.empty:
        return ["Sem projeto específico"]
    return ["Sem projeto específico"] + projects.apply(
        lambda r: f"{clean_value(r.get('project_code'), 'Sem código')} — {clean_value(r.get('project_name'))}",
        axis=1,
    ).tolist()


def _operator_options(operators: pd.DataFrame) -> list[str]:
    if operators.empty:
        return ["Selecionar depois"]
    return ["Selecionar depois"] + operators.apply(lambda r: f"{clean_value(r.get('full_name'))} ({role_badge(clean_value(r.get('role'), 'member'))})", axis=1).tolist()


def _booking_query_for_equipment(conn, equipment_id: int, start_date: date, end_date: date, include_cancelled: bool = True) -> pd.DataFrame:
    start_iso = datetime.combine(start_date, time.min).isoformat(timespec="minutes")
    end_iso = datetime.combine(end_date + timedelta(days=1), time.min).isoformat(timespec="minutes")
    sql = """
        SELECT b.id, e.equipment_code, e.equipment_name, u.full_name AS solicitante,
               p.project_name, op.full_name AS operador, perf.full_name AS executante,
               b.start_datetime, b.end_datetime,
               b.sample_count, b.purpose, b.status
        FROM bookings b
        JOIN equipment e ON e.id=b.equipment_id
        JOIN users u ON u.id=b.user_id
        LEFT JOIN users op ON op.id=b.operator_id
        LEFT JOIN users perf ON perf.id=b.performed_by_id
        LEFT JOIN projects p ON p.id=b.project_id
        WHERE b.equipment_id = ?
          AND b.start_datetime >= ?
          AND b.start_datetime < ?
    """
    params = [equipment_id, start_iso, end_iso]
    if not include_cancelled:
        sql += " AND b.status != 'cancelled'"
    sql += " ORDER BY b.start_datetime"
    return query_df(conn, sql, params)


def _calendar_events_for_equipment(conn, equipment_id: int, start_date: date, end_date: date, include_cancelled: bool = False) -> pd.DataFrame:
    """Eventos de reserva e manutenção que cruzam o intervalo informado."""
    start_iso = datetime.combine(start_date, time.min).isoformat(timespec="minutes")
    end_iso = datetime.combine(end_date + timedelta(days=1), time.min).isoformat(timespec="minutes")

    bookings_sql = """
        SELECT 'booking' AS event_type, b.id, e.equipment_code, e.equipment_name,
               u.full_name AS solicitante, op.full_name AS operador, perf.full_name AS executante,
               p.project_name, b.start_datetime AS start_datetime, b.end_datetime AS end_datetime,
               b.sample_count, b.purpose, b.status
        FROM bookings b
        JOIN equipment e ON e.id=b.equipment_id
        JOIN users u ON u.id=b.user_id
        LEFT JOIN users op ON op.id=b.operator_id
        LEFT JOIN users perf ON perf.id=b.performed_by_id
        LEFT JOIN projects p ON p.id=b.project_id
        WHERE b.equipment_id = ?
          AND b.start_datetime < ?
          AND b.end_datetime > ?
    """
    params = [equipment_id, end_iso, start_iso]
    if not include_cancelled:
        bookings_sql += " AND b.status != 'cancelled'"
    booking_events = query_df(conn, bookings_sql + " ORDER BY b.start_datetime", params)

    maintenance_events = query_df(
        conn,
        """
        SELECT 'maintenance' AS event_type, mp.id, e.equipment_code, e.equipment_name,
               NULL AS solicitante, NULL AS operador, NULL AS executante,
               NULL AS project_name,
               mp.planned_date AS start_datetime,
               COALESCE(mp.planned_end_date, mp.planned_date) AS end_datetime,
               NULL AS sample_count,
               mp.description AS purpose,
               COALESCE(mp.status, 'pendente') AS status,
               mp.activity_type,
               mp.blocks_booking
        FROM maintenance_preventive mp
        JOIN equipment e ON e.id=mp.equipment_id
        WHERE mp.equipment_id = ?
          AND mp.planned_date IS NOT NULL
          AND mp.planned_date <= ?
          AND COALESCE(mp.planned_end_date, mp.planned_date) >= ?
        ORDER BY mp.planned_date
        """,
        [equipment_id, end_date.isoformat(), start_date.isoformat()],
    )
    if booking_events.empty:
        return maintenance_events
    if maintenance_events.empty:
        return booking_events
    return pd.concat([booking_events, maintenance_events], ignore_index=True, sort=False)


def _coerce_event_datetime(value, end_of_day: bool = False) -> datetime:
    if not value:
        return datetime.max if end_of_day else datetime.min
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        parsed = datetime.fromisoformat(text + ("T23:59:59" if end_of_day else "T00:00:00"))
    if end_of_day and len(text) == 10:
        return datetime.combine(parsed.date(), time.max)
    return parsed


def _event_overlaps_day(row: pd.Series, day: date) -> bool:
    start_dt = _coerce_event_datetime(row.get("start_datetime"))
    end_dt = _coerce_event_datetime(row.get("end_datetime"), end_of_day=True)
    day_start = datetime.combine(day, time.min)
    day_end = datetime.combine(day, time.max)
    return start_dt <= day_end and end_dt >= day_start


def _event_time_label(row: pd.Series, day: date) -> str:
    if row.get("event_type") == "maintenance":
        start_dt = _coerce_event_datetime(row.get("start_datetime"))
        end_dt = _coerce_event_datetime(row.get("end_datetime"), end_of_day=True)
        if start_dt.date() == end_dt.date():
            return "manutenção"
        return f"{start_dt.strftime('%d/%m')}–{end_dt.strftime('%d/%m')}"
    start_dt = _coerce_event_datetime(row.get("start_datetime"))
    end_dt = _coerce_event_datetime(row.get("end_datetime"), end_of_day=True)
    if start_dt.date() == day and end_dt.date() == day:
        return f"{start_dt.strftime('%H:%M')}–{end_dt.strftime('%H:%M')}"
    if start_dt.date() == day:
        return f"{start_dt.strftime('%H:%M')}→"
    if end_dt.date() == day:
        return f"→{end_dt.strftime('%H:%M')}"
    return "continuação"


def _event_css_class(row: pd.Series, selected_eq: pd.Series) -> str:
    if row.get("event_type") == "maintenance":
        return "calendar-pill calendar-pill-maintenance"
    if str(row.get("status")) == "done":
        return "calendar-pill calendar-pill-done"
    if str(row.get("status")) == "cancelled":
        return "calendar-pill calendar-pill-cancelled"
    if selected_eq.get("operational_status") == "restricted":
        return "calendar-pill calendar-pill-restricted"
    return "calendar-pill"


def _render_event_pill(row: pd.Series, day: date, selected_eq: pd.Series) -> str:
    css = _event_css_class(row, selected_eq)
    time_label = escape(_event_time_label(row, day))
    if row.get("event_type") == "maintenance":
        title = f"{clean_value(row.get('activity_type'), 'Manutenção')} #{int(row.get('id')) if pd.notna(row.get('id')) else ''}"
        desc = clean_value(row.get("purpose"))
        status = clean_value(row.get("status"))
        return (
            f"<span class='{css}'><b>{time_label}</b><br>"
            f"{escape(str(title))}<br><small>{escape(str(desc))} · {escape(str(status))}</small></span>"
        )
    title = f"Reserva #{int(row.get('id')) if pd.notna(row.get('id')) else ''}"
    who = clean_value(row.get("solicitante"), "Solicitante não informado")
    samples = ""
    if pd.notna(row.get("sample_count")) and row.get("sample_count") not in ["", None]:
        try:
            samples = f" · {int(row.get('sample_count'))} am."
        except Exception:
            samples = f" · {row.get('sample_count')} am."
    status = status_badge(str(row.get("status")))
    return (
        f"<span class='{css}'><b>{time_label}</b><br>"
        f"{escape(title)} · {escape(str(who))}<br><small>{escape(status)}{escape(samples)}</small></span>"
    )


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _render_week_calendar(events: pd.DataFrame, selected_eq: pd.Series, week_start: date) -> str:
    day_names = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    days = [week_start + timedelta(days=i) for i in range(7)]
    html = ["<div class='calendar-shell'><div class='calendar-grid-week'>"]
    today = date.today()
    for label, day in zip(day_names, days):
        cls = "calendar-day calendar-today" if day == today else "calendar-day"
        html.append(
            f"<div class='{cls}'><div class='calendar-head'>{label}<br>"
            f"<span class='calendar-date'>{day.strftime('%d/%m/%Y')}</span></div>"
        )
        if events.empty:
            html.append("<div class='calendar-more'>Livre</div>")
        else:
            day_events = events[events.apply(lambda r: _event_overlaps_day(r, day), axis=1)].copy()
            if day_events.empty:
                html.append("<div class='calendar-more'>Livre</div>")
            else:
                day_events["_sort"] = day_events["start_datetime"].astype(str)
                day_events = day_events.sort_values("_sort")
                for _, row in day_events.head(4).iterrows():
                    html.append(_render_event_pill(row, day, selected_eq))
                if len(day_events) > 4:
                    html.append(f"<div class='calendar-more'>+{len(day_events) - 4} evento(s)</div>")
        html.append("</div>")
    html.append("</div></div>")
    return "".join(html)


def _month_grid_days(year: int, month: int) -> list[date]:
    first = date(year, month, 1)
    start = _week_start(first)
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    last = next_month - timedelta(days=1)
    end = last + timedelta(days=(6 - last.weekday()))
    days = []
    d = start
    while d <= end:
        days.append(d)
        d += timedelta(days=1)
    return days


def _render_month_calendar(events: pd.DataFrame, selected_eq: pd.Series, anchor_day: date) -> str:
    days = _month_grid_days(anchor_day.year, anchor_day.month)
    day_names = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    html = ["<div class='calendar-shell'>"]
    html.append("<div class='calendar-grid-month'>")
    for label in day_names:
        html.append(f"<div class='calendar-head' style='text-align:center'>{label}</div>")
    today = date.today()
    for day in days:
        cls = "calendar-day"
        if day.month != anchor_day.month:
            cls += " calendar-day-muted"
        if day == today:
            cls += " calendar-today"
        html.append(f"<div class='{cls}' style='min-height:112px'><div class='calendar-head'>{day.day}</div>")
        if not events.empty:
            day_events = events[events.apply(lambda r: _event_overlaps_day(r, day), axis=1)].copy()
            if not day_events.empty:
                for _, row in day_events.head(2).iterrows():
                    html.append(_render_event_pill(row, day, selected_eq))
                if len(day_events) > 2:
                    html.append(f"<div class='calendar-more'>+{len(day_events) - 2}</div>")
        html.append("</div>")
    html.append("</div></div>")
    return "".join(html)


def page_reservas(conn):
    hero()
    st.subheader("Agenda funcional dos equipamentos")
    st.caption("MVP real da Fase 2: página por equipamento, criação de reserva, validação de conflito, cancelamento, status simples e integração com QR Code.")

    equipment, users, projects, operators = load_reference_data(conn)
    if equipment.empty or users.empty:
        st.warning("Cadastre/importe equipamentos e usuários antes de criar reservas.")
        return

    active_equipment = equipment[equipment["active"] == 1].copy()
    active_users = users[users["active"] == 1].copy()
    active_projects = projects[projects["active"] == 1].copy()
    if active_equipment.empty or active_users.empty:
        st.warning("É necessário ter ao menos um equipamento e um usuário ativos.")
        return

    qr_eq = st.query_params.get("eq", None)
    eq_labels = _equipment_options(active_equipment)
    selected_index = _select_index_by_code(active_equipment, qr_eq)

    top1, top2 = st.columns([2, 1])
    with top1:
        eq_label = st.selectbox("Equipamento", eq_labels, index=selected_index, key="booking_eq_main")
    equipment_id = _equipment_id_from_label(active_equipment, eq_label)
    selected_eq = active_equipment[active_equipment["id"] == equipment_id].iloc[0]
    with top2:
        st.metric("Status do equipamento", equipment_status_badge(selected_eq.get("operational_status") or "available"))

    cap_text = "-"
    if pd.notna(selected_eq.get("max_sample_capacity")) and selected_eq.get("max_sample_capacity"):
        cap_text = f"{int(selected_eq.get('max_sample_capacity'))} {clean_value(selected_eq.get('capacity_unit'), 'amostras')}"
    unavailable = clean_input(selected_eq.get("unavailable_functions"))
    st.markdown(
        f"""
        <div class="soft-card">
        <b>{clean_value(selected_eq.get('equipment_code'))} — {clean_value(selected_eq.get('equipment_name'))}</b><br>
        Unidade: {clean_value(selected_eq.get('lab_unit'))} · Local: {clean_value(selected_eq.get('location'))} ·
        Responsável: {clean_value(selected_eq.get('responsible_name'))} · Requer operador: {yes_no(selected_eq.get('requires_operator', 0))}<br>
        Capacidade usual: {cap_text} · Gestor técnico: {clean_value(selected_eq.get('technical_manager'))}
        </div>
        """,
        unsafe_allow_html=True,
    )
    if selected_eq.get("operational_status") == "restricted":
        st.warning(f"Equipamento em uso restrito. Funcionalidades indisponíveis: {unavailable or 'não especificadas'}.")
    elif selected_eq.get("operational_status") == "maintenance":
        st.error("Equipamento marcado como em manutenção. Novas reservas serão bloqueadas.")

    with st.container(border=True):
        st.markdown("#### Documentação operacional")
        d1, d2 = st.columns([1, 2])
        with d1:
            pop_download_button(selected_eq, key_prefix="booking_pop")
        with d2:
            st.caption(
                f"{clean_value(selected_eq.get('pop_title'), 'Sem POP cadastrado')} · "
                f"Versão: {clean_value(selected_eq.get('pop_version'))} · "
                f"Responsável: {clean_value(selected_eq.get('pop_responsible'))}"
            )
            if not is_blank(selected_eq.get("document_notes")):
                st.caption(clean_value(selected_eq.get("document_notes")))

    confirmation = st.session_state.get("booking_confirmation")
    if confirmation:
        st.markdown(
            f"""
            <div class="success-card">
                <div class="success-card-title">✅ Reserva confirmada</div>
                <div>
                    <b>{escape(clean_value(confirmation.get("equipment")))}</b><br>
                    Solicitante: {escape(clean_value(confirmation.get("user")))} ·
                    Período: {escape(clean_value(confirmation.get("period")))} ·
                    Amostras: {escape(clean_value(confirmation.get("samples")))}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Ocultar confirmação", key="dismiss_booking_confirmation"):
            st.session_state.pop("booking_confirmation", None)
            st.rerun()

    st.markdown("#### Escolha uma ação")
    tab_cal_sem, tab_cal_mes, tab_agenda, tab_nova, tab_gerenciar = st.tabs([
        "Calendário semanal",
        "Calendário mensal",
        "Agenda linear",
        "Nova reserva",
        "Gerenciar reservas",
    ])

    with tab_cal_sem:
        st.markdown("### Calendário semanal")
        c1, c2 = st.columns([1, 2])
        with c1:
            selected_week_day = st.date_input("Semana de referência", value=date.today(), format="DD/MM/YYYY", key="calendar_week_day")
        with c2:
            include_cancelled_week = st.checkbox("Mostrar reservas canceladas", value=False, key="calendar_week_cancelled")
        current_week_start = _week_start(selected_week_day)
        current_week_end = current_week_start + timedelta(days=6)
        week_events = _calendar_events_for_equipment(
            conn,
            equipment_id,
            current_week_start,
            current_week_end,
            include_cancelled=include_cancelled_week,
        )
        st.caption(f"Semana de {current_week_start.strftime('%d/%m/%Y')} a {current_week_end.strftime('%d/%m/%Y')}.")
        st.markdown(_render_week_calendar(week_events, selected_eq, current_week_start), unsafe_allow_html=True)
        if not week_events.empty:
            with st.expander("Ver eventos da semana em tabela"):
                st.dataframe(_display_df(week_events.drop(columns=[c for c in ["activity_type", "blocks_booking"] if c in week_events.columns])), use_container_width=True, hide_index=True)

    with tab_cal_mes:
        st.markdown("### Calendário mensal")
        c1, c2 = st.columns([1, 2])
        with c1:
            selected_month_day = st.date_input("Mês de referência", value=date.today(), format="DD/MM/YYYY", key="calendar_month_day")
        with c2:
            include_cancelled_month = st.checkbox("Mostrar canceladas no mês", value=False, key="calendar_month_cancelled")
        month_start = date(selected_month_day.year, selected_month_day.month, 1)
        if selected_month_day.month == 12:
            month_end = date(selected_month_day.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(selected_month_day.year, selected_month_day.month + 1, 1) - timedelta(days=1)
        month_events = _calendar_events_for_equipment(
            conn,
            equipment_id,
            month_start,
            month_end,
            include_cancelled=include_cancelled_month,
        )
        st.caption(f"{month_start.strftime('%m/%Y')} · {len(month_events)} evento(s) no mês para este equipamento.")
        st.markdown(_render_month_calendar(month_events, selected_eq, selected_month_day), unsafe_allow_html=True)

    with tab_agenda:
        st.markdown("### Agenda linear")
        st.caption("Visual técnico complementar, útil quando há muitos eventos no mesmo período.")
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            start_day = st.date_input("Início da visualização", value=date.today(), format="DD/MM/YYYY", key="agenda_start")
        with c2:
            days = st.selectbox("Período", [7, 14, 30, 60], index=1, format_func=lambda x: f"{x} dias", key="agenda_days")
        with c3:
            include_cancelled = st.checkbox("Mostrar canceladas", value=False, key="agenda_include_cancelled")
        end_day = start_day + timedelta(days=int(days))
        agenda_df = _booking_query_for_equipment(conn, equipment_id, start_day, end_day, include_cancelled=include_cancelled)

        if agenda_df.empty:
            st.info("Não há reservas para este equipamento no período selecionado.")
        else:
            graph_df = agenda_df.copy()
            graph_df["Início"] = pd.to_datetime(graph_df["start_datetime"])
            graph_df["Fim"] = pd.to_datetime(graph_df["end_datetime"])
            graph_df["Início formatado"] = graph_df["start_datetime"].map(_format_datetime)
            graph_df["Fim formatado"] = graph_df["end_datetime"].map(_format_datetime)
            graph_df["Reserva"] = graph_df.apply(
                lambda r: f"#{r['id']} · {r['solicitante']} · {status_badge(r['status'])}", axis=1
            )
            graph_df["Status"] = graph_df["status"].map(status_badge)
            fig = px.timeline(
                graph_df,
                x_start="Início",
                x_end="Fim",
                y="Reserva",
                color="Status",
                custom_data=["Início formatado", "Fim formatado"],
                hover_data={"Início": False, "Fim": False, "Reserva": False},
                color_discrete_sequence=[LAB_BLUE, LAB_CYAN, "#6BAED6", "#9ECAE1"],
            )
            fig.update_traces(hovertemplate="<b>%{y}</b><br>Início: %{customdata[0]}<br>Fim: %{customdata[1]}<extra></extra>")
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(height=max(300, min(720, 70 + 36 * len(graph_df))), margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(_display_df(agenda_df), use_container_width=True, hide_index=True)

    with tab_nova:
        with st.form("form_nova_reserva", clear_on_submit=False):
            st.markdown("### Criar reserva")
            c1, c2, c3 = st.columns(3)
            with c1:
                user_placeholder = "Selecione o solicitante"
                user_labels = [user_placeholder] + _user_options(active_users)
                user_label = st.selectbox("Solicitante", user_labels, key="booking_user")
                user_id = None
                if user_label != user_placeholder:
                    user_id = int(active_users.iloc[user_labels.index(user_label) - 1]["id"])
                booking_date = st.date_input("Data", value=date.today(), format="DD/MM/YYYY", key="booking_date")
            with c2:
                start_t = st.time_input("Horário inicial", value=time(9, 0), step=timedelta(minutes=30), key="booking_start")
                end_t = st.time_input("Horário final", value=time(10, 0), step=timedelta(minutes=30), key="booking_end")
                sample_count = st.number_input("Número de amostras", min_value=0, step=1, value=0, key="booking_samples")
            with c3:
                project_options = _project_options(active_projects)
                project_label = st.selectbox("Projeto", project_options, key="booking_project")
                project_id = None
                if project_label != "Sem projeto específico" and not active_projects.empty:
                    project_id = int(active_projects.iloc[project_options.index(project_label) - 1]["id"])
                operator_id = None
                if truthy(selected_eq.get("requires_operator")):
                    op_options = _operator_options(operators)
                    op_label = st.selectbox("Operador", op_options, key="booking_operator")
                    if op_label != "Selecionar depois" and not operators.empty:
                        operator_id = int(operators.iloc[op_options.index(op_label) - 1]["id"])
                    st.caption("Este equipamento está marcado como operação assistida/requer operador.")
                else:
                    st.info("Este equipamento não exige operador obrigatório.")

            purpose = st.text_area("Finalidade / observações", placeholder="Ex.: análise MEV com EDS; ensaio mecânico; preparação de amostras...", key="booking_purpose")
            submitted = st.form_submit_button("Nova Reserva", type="primary")

        if submitted:
            start_dt = datetime.combine(booking_date, start_t)
            end_dt = datetime.combine(booking_date, end_t)
            max_capacity = None if is_blank(selected_eq.get("max_sample_capacity")) else int(selected_eq.get("max_sample_capacity"))
            capacity_unit = clean_value(selected_eq.get("capacity_unit"), "amostras")
            if user_id is None:
                st.error("Selecione o solicitante para criar a reserva.")
            elif end_dt <= start_dt:
                st.error("O horário final precisa ser maior que o horário inicial.")
            elif max_capacity and sample_count and int(sample_count) > max_capacity and truthy(selected_eq.get("capacity_enforced")):
                st.error(f"A quantidade excede a capacidade máxima cadastrada para este equipamento ({max_capacity} {capacity_unit}).")
            else:
                if max_capacity and sample_count and int(sample_count) > max_capacity:
                    st.warning("A quantidade informada excede a capacidade usual. Como o bloqueio rígido não está ativo, a reserva será tentada mesmo assim.")
                ok, msg, booking_id = create_booking(
                    conn,
                    equipment_id=equipment_id,
                    user_id=user_id,
                    project_id=project_id,
                    operator_id=operator_id,
                    performed_by_id=user_id,
                    start_iso=start_dt.isoformat(timespec="minutes"),
                    end_iso=end_dt.isoformat(timespec="minutes"),
                    sample_count=int(sample_count) if sample_count else None,
                    purpose=purpose,
                )
                if ok:
                    st.session_state["booking_confirmation"] = {
                        "id": booking_id,
                        "equipment": f"{clean_value(selected_eq.get('equipment_code'))} — {clean_value(selected_eq.get('equipment_name'))}",
                        "user": user_label,
                        "period": f"{start_dt.strftime('%d/%m/%Y %H:%M')} a {end_dt.strftime('%H:%M')}",
                        "samples": str(int(sample_count)) if sample_count else "-",
                    }
                    st.rerun()
                else:
                    st.error(msg)

    with tab_gerenciar:
        st.markdown("### Gerenciar reservas")
        c1, c2 = st.columns([1, 1])
        with c1:
            status_label = st.selectbox("Filtrar por status", ["Todos"] + list(STATUS_LABELS.values()), key="manage_status_filter")
        with c2:
            manage_days = st.slider("Próximos dias", 1, 90, 30, key="manage_days")
        manage_start = date.today() - timedelta(days=1)
        manage_end = date.today() + timedelta(days=int(manage_days))
        manage_df = _booking_query_for_equipment(conn, equipment_id, manage_start, manage_end, include_cancelled=True)
        if status_label != "Todos" and not manage_df.empty:
            internal_status = STATUS_REVERSE[status_label]
            manage_df = manage_df[manage_df["status"] == internal_status]

        if manage_df.empty:
            st.info("Nenhuma reserva encontrada para os filtros atuais.")
        else:
            st.dataframe(_display_df(manage_df), use_container_width=True, hide_index=True)
            options = manage_df["id"].tolist()
            def _booking_format(x):
                row = manage_df[manage_df["id"] == x].iloc[0]
                return f"#{x} · {row['solicitante']} · {_format_datetime(row['start_datetime'])} · {status_badge(row['status'])}"
            booking_id = st.selectbox("Selecionar reserva", options, format_func=_booking_format, key="manage_booking_id")
            a1, a2, a3 = st.columns(3)
            with a1:
                if st.button("Marcar como concluída", key="booking_mark_done"):
                    update_booking_status(conn, int(booking_id), "done")
                    st.rerun()
            with a2:
                if st.button("Cancelar reserva", key="booking_cancel"):
                    update_booking_status(conn, int(booking_id), "cancelled")
                    st.rerun()
            with a3:
                if st.button("Marcar como não compareceu", key="booking_no_show"):
                    update_booking_status(conn, int(booking_id), "no_show")
                    st.rerun()


def page_table(conn, table_name: str, title: str):
    hero()
    st.subheader(title)
    df = query_df(conn, f"SELECT * FROM {table_name}")
    if df.empty:
        st.info("Nenhum registro encontrado.")
    else:
        display = _display_df(df)
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.download_button(
            "Baixar CSV",
            data=display.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{table_name}.csv",
            mime="text/csv",
        )


def page_usuarios(conn):
    hero()
    st.subheader("Usuários")
    st.caption("Cadastro simples de usuários, perfil de acesso, vínculo e treinamento. A autenticação real virá na etapa da senha volátil.")

    users = query_df(conn, "SELECT * FROM users ORDER BY active DESC, full_name")
    display_cols = ["full_name", "email", "phone_e164", "role", "lab_unit", "department", "advisor_name", "training_completed", "active", "notes"]
    if users.empty:
        st.info("Nenhum usuário cadastrado.")
    else:
        st.dataframe(_display_df(users[[c for c in display_cols if c in users.columns]]), use_container_width=True, hide_index=True)

    if not can_manage_master_data():
        admin_required_message("incluir ou atualizar usuários")
        return

    st.markdown("### Incluir ou atualizar usuário")
    mode = st.radio("Modo", ["Novo usuário", "Editar usuário existente"], horizontal=True, key="user_edit_mode")
    selected = None
    user_id = None
    if mode == "Editar usuário existente":
        if users.empty:
            st.info("Cadastre um usuário antes de editar.")
            return
        labels = users.apply(lambda r: f"{clean_value(r.get('full_name'))} ({role_badge(clean_value(r.get('role'), 'member'))})", axis=1).tolist()
        label = st.selectbox("Selecionar usuário", labels, key="user_edit_select")
        selected = users.iloc[labels.index(label)]
        user_id = int(selected["id"])

    with st.form("form_user_master"):
        c1, c2, c3 = st.columns(3)
        with c1:
            full_name = st.text_input("Nome completo", value=clean_input(selected.get("full_name")) if selected is not None else "")
            email = st.text_input("E-mail", value=clean_input(selected.get("email")) if selected is not None else "")
            phone = st.text_input("Celular/WhatsApp", value=clean_input(selected.get("phone_e164")) if selected is not None else "")
        with c2:
            current_role = clean_value(selected.get("role"), "member") if selected is not None else "member"
            if current_role == "operator":
                current_role = "manager"
            role_label = st.selectbox(
                "Perfil",
                list(ROLE_LABELS.values()),
                index=list(ROLE_LABELS.keys()).index(current_role) if current_role in ROLE_LABELS else 0,
            )
            lab_unit = st.text_input("Unidade/laboratório", value=clean_input(selected.get("lab_unit")) if selected is not None else "LabCim")
            department = st.text_input("Departamento/programa", value=clean_input(selected.get("department")) if selected is not None else "")
        with c3:
            advisor_name = st.text_input("Orientador(a)", value=clean_input(selected.get("advisor_name")) if selected is not None else "")
            training_completed = st.checkbox("Treinamento concluído", value=truthy(selected.get("training_completed")) if selected is not None else False)
            active = st.checkbox("Usuário ativo", value=truthy(selected.get("active")) if selected is not None else True)
        notes = st.text_area("Observações", value=clean_input(selected.get("notes")) if selected is not None else "")
        submitted = st.form_submit_button("Salvar usuário", type="primary")

    if submitted:
        payload = dict(
            full_name=full_name,
            email=email.strip() or None,
            phone_e164=phone.strip() or None,
            role=ROLE_REVERSE[role_label],
            lab_unit=lab_unit.strip() or None,
            department=department.strip() or None,
            advisor_name=advisor_name.strip() or None,
            training_completed=int(training_completed),
            active=int(active),
            notes=notes.strip() or None,
        )
        if mode == "Novo usuário":
            ok, msg = create_user(conn, **payload)
        else:
            ok, msg = update_user(conn, int(user_id), **payload)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)


def page_projetos(conn):
    hero()
    st.subheader("Projetos")
    st.caption("Cadastro de projetos usado nas reservas, movimentações de insumos e relatórios semestrais/anuais.")

    projects = query_df(conn, "SELECT * FROM projects ORDER BY active DESC, project_name")
    display_cols = ["project_code", "project_name", "funding_source", "start_date", "end_date", "active", "notes"]
    if projects.empty:
        st.info("Nenhum projeto cadastrado.")
    else:
        st.dataframe(_display_df(projects[[c for c in display_cols if c in projects.columns]]), use_container_width=True, hide_index=True)

    if not can_manage_master_data():
        admin_required_message("incluir ou atualizar projetos")
        return

    st.markdown("### Incluir ou atualizar projeto")
    mode = st.radio("Modo", ["Novo projeto", "Editar projeto existente"], horizontal=True, key="project_edit_mode")
    selected = None
    project_id = None
    if mode == "Editar projeto existente":
        if projects.empty:
            st.info("Cadastre um projeto antes de editar.")
            return
        labels = projects.apply(lambda r: f"{clean_value(r.get('project_code'), 'Sem código')} — {clean_value(r.get('project_name'))}", axis=1).tolist()
        label = st.selectbox("Selecionar projeto", labels, key="project_edit_select")
        selected = projects.iloc[labels.index(label)]
        project_id = int(selected["id"])

    with st.form("form_project_master"):
        c1, c2 = st.columns(2)
        with c1:
            project_code = st.text_input("Código do projeto", value=clean_input(selected.get("project_code")) if selected is not None else "")
            project_name = st.text_input("Nome do projeto", value=clean_input(selected.get("project_name")) if selected is not None else "")
            funding_source = st.text_input("Fonte de financiamento", value=clean_input(selected.get("funding_source")) if selected is not None else "")
        with c2:
            start_value = _date_input_value(selected.get("start_date"), None) if selected is not None else None
            end_value = _date_input_value(selected.get("end_date"), None) if selected is not None else None
            start_date_value = st.date_input("Data de início", value=start_value, key="project_start_date")
            end_date_value = st.date_input("Data de fim", value=end_value, key="project_end_date")
            active = st.checkbox("Projeto ativo", value=truthy(selected.get("active")) if selected is not None else True)
        notes = st.text_area("Observações", value=clean_input(selected.get("notes")) if selected is not None else "")
        submitted = st.form_submit_button("Salvar projeto", type="primary")

    if submitted:
        if start_date_value and end_date_value and start_date_value > end_date_value:
            st.error("A data de início não pode ser posterior à data de fim.")
            return
        payload = dict(
            project_code=project_code.strip() or None,
            project_name=project_name,
            funding_source=funding_source.strip() or None,
            start_date=start_date_value.isoformat() if start_date_value else None,
            end_date=end_date_value.isoformat() if end_date_value else None,
            active=int(active),
            notes=notes.strip() or None,
        )
        if mode == "Novo projeto":
            ok, msg = create_project(conn, **payload)
        else:
            ok, msg = update_project(conn, int(project_id), **payload)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)


def page_equipamentos(conn):
    hero()
    st.subheader("Equipamentos")
    st.caption("Cadastro operacional simples: status, capacidade, funcionalidades indisponíveis, documentação e localização. O cadastro mestre fica restrito ao administrador.")

    equipment = query_df(conn, "SELECT * FROM equipment ORDER BY active DESC, equipment_code")
    display_cols = [
        "equipment_code",
        "equipment_name",
        "lab_unit",
        "location",
        "operational_status",
        "max_sample_capacity",
        "capacity_unit",
        "capacity_enforced",
        "unavailable_functions",
        "technical_manager",
        "pop_title",
        "pop_version",
        "pop_responsible",
        "requires_operator",
        "active",
    ]
    if equipment.empty:
        st.info("Nenhum equipamento cadastrado.")
    else:
        existing_cols = [c for c in display_cols if c in equipment.columns]
        st.dataframe(_display_df(equipment[existing_cols]), use_container_width=True, hide_index=True)

    tab_oper, tab_parts, tab_master = st.tabs(["Atualizar dados operacionais", "Peças de reposição", "Cadastro mestre"])

    with tab_oper:
        if equipment.empty:
            st.info("Cadastre um equipamento antes de atualizar dados operacionais.")
        elif not can_edit_operational_data():
            st.info("Para atualizar dados operacionais, use perfil Gerente ou Administrador.")
        else:
            eq_label = st.selectbox("Selecionar equipamento", _equipment_options(equipment), key="equip_edit_select")
            equipment_id = _equipment_id_from_label(equipment, eq_label)
            selected = equipment[equipment["id"] == equipment_id].iloc[0]

            with st.form("form_equip_operational"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    current_status = selected.get("operational_status") or "available"
                    status_label = st.selectbox(
                        "Status operacional",
                        list(EQUIPMENT_STATUS_LABELS.values()),
                        index=list(EQUIPMENT_STATUS_LABELS.keys()).index(current_status) if current_status in EQUIPMENT_STATUS_LABELS else 0,
                    )
                    location = st.text_input("Localização", value=clean_input(selected.get("location")), placeholder="Ex.: Lab Tecnológico, Sala de Raios X...")
                    technical_manager = st.text_input("Gestor técnico", value=clean_input(selected.get("technical_manager")) or clean_input(selected.get("responsible_name")))
                with c2:
                    raw_capacity = selected.get("max_sample_capacity")
                    initial_capacity = int(raw_capacity) if not is_blank(raw_capacity) and raw_capacity else 0
                    max_sample_capacity = st.number_input("Capacidade máxima por reserva", min_value=0, value=initial_capacity, step=1)
                    capacity_unit = st.text_input("Unidade da capacidade", value=clean_value(selected.get("capacity_unit"), "amostras"))
                    capacity_enforced = st.checkbox("Bloquear acima da capacidade", value=truthy(selected.get("capacity_enforced")))
                with c3:
                    unavailable_functions = st.text_area(
                        "Funcionalidades indisponíveis",
                        value=clean_input(selected.get("unavailable_functions")),
                        placeholder="Ex.: EDS indisponível; vácuo parcial; forno sem rampa automática...",
                    )
                    notes = st.text_area("Observações operacionais", value=clean_input(selected.get("notes")))

                st.markdown("#### Documentação operacional")
                d1, d2, d3 = st.columns(3)
                with d1:
                    pop_title = st.text_input("Título do POP", value=clean_input(selected.get("pop_title")), placeholder="Ex.: POP - Autoclave")
                    pop_version = st.text_input("Versão do POP", value=clean_input(selected.get("pop_version")), placeholder="Ex.: v1, Rev. 02")
                with d2:
                    pop_path = st.text_input("Arquivo/link do POP", value=clean_input(selected.get("pop_path")), placeholder="Ex.: assets/pops/POP_Autoclave.pdf")
                    pop_updated_at = st.text_input("Data de atualização do POP", value=clean_input(selected.get("pop_updated_at")), placeholder="Ex.: 19/06/2026")
                with d3:
                    pop_responsible = st.text_input("Responsável pelo POP", value=clean_input(selected.get("pop_responsible")) or clean_input(selected.get("technical_manager")) or clean_input(selected.get("responsible_name")))
                    document_notes = st.text_area("Observações documentais", value=clean_input(selected.get("document_notes")))

                submitted = st.form_submit_button("Salvar dados operacionais", type="primary")

            pop_download_button(selected, key_prefix="equip_pop")

            if submitted:
                old_status = clean_input(selected.get("operational_status")) or "available"
                new_status = EQUIPMENT_STATUS_REVERSE[status_label]
                update_equipment_operational_info(
                    conn,
                    equipment_id,
                    location=location.strip() or None,
                    operational_status=new_status,
                    unavailable_functions=unavailable_functions.strip() or None,
                    max_sample_capacity=int(max_sample_capacity) if max_sample_capacity else None,
                    capacity_unit=capacity_unit.strip() or "amostras",
                    capacity_enforced=int(capacity_enforced),
                    technical_manager=technical_manager.strip() or None,
                    pop_title=pop_title.strip() or None,
                    pop_path=pop_path.strip() or None,
                    pop_version=pop_version.strip() or None,
                    pop_updated_at=pop_updated_at.strip() or None,
                    pop_responsible=pop_responsible.strip() or None,
                    document_notes=document_notes.strip() or None,
                    notes=notes.strip() or None,
                )
                if new_status == "maintenance" and old_status != "maintenance":
                    sent, total = notify_equipment_maintenance(
                        conn,
                        equipment_id=equipment_id,
                        title="equipamento em manutenção",
                        message=(
                            "O equipamento foi marcado como EM MANUTENÇÃO no sistema.\n"
                            f"Observações: {notes.strip() or unavailable_functions.strip() or 'Sem observações adicionais.'}"
                        ),
                        related_table="equipment",
                        related_id=equipment_id,
                    )
                    if total:
                        st.info(f"Notificação de manutenção registrada para {total} destinatário(s). Enviadas: {sent}.")
                st.success("Dados operacionais do equipamento atualizados.")
                st.rerun()

    with tab_parts:
        st.markdown("### Peças de reposição associadas")
        if equipment.empty:
            st.info("Cadastre um equipamento antes de consultar peças de reposição.")
        else:
            eq_label = st.selectbox("Selecionar equipamento", _equipment_options(equipment), key="equipment_spare_parts_select")
            equipment_id = _equipment_id_from_label(equipment, eq_label)
            selected = equipment[equipment["id"] == equipment_id].iloc[0]
            st.caption(
                f"{clean_value(selected.get('equipment_code'))} — {clean_value(selected.get('equipment_name'))} · "
                f"Local: {clean_value(selected.get('location'))}"
            )
            spare_parts = list_spare_parts_for_equipment(conn, equipment_id)
            render_equipment_spare_parts(spare_parts)

    with tab_master:
        if not can_manage_master_data():
            admin_required_message("incluir ou atualizar equipamentos")
        else:
            mode = st.radio("Modo", ["Novo equipamento", "Editar equipamento existente"], horizontal=True, key="equipment_master_mode")
            selected = None
            equipment_id = None
            if mode == "Editar equipamento existente":
                if equipment.empty:
                    st.info("Cadastre um equipamento antes de editar.")
                    return
                eq_label = st.selectbox("Selecionar equipamento", _equipment_options(equipment), key="equipment_master_select")
                equipment_id = _equipment_id_from_label(equipment, eq_label)
                selected = equipment[equipment["id"] == equipment_id].iloc[0]

            with st.form("form_equipment_master"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    equipment_code = st.text_input("Código/patrimônio", value=clean_input(selected.get("equipment_code")) if selected is not None else "")
                    equipment_name = st.text_input("Nome do equipamento", value=clean_input(selected.get("equipment_name")) if selected is not None else "")
                    lab_unit = st.text_input("Unidade/laboratório", value=clean_input(selected.get("lab_unit")) if selected is not None else "LabCim")
                    location = st.text_input("Localização", value=clean_input(selected.get("location")) if selected is not None else "")
                with c2:
                    responsible_name = st.text_input("Responsável", value=clean_input(selected.get("responsible_name")) if selected is not None else "")
                    responsible_phone = st.text_input("Telefone do responsável", value=clean_input(selected.get("responsible_phone")) if selected is not None else "")
                    technical_manager = st.text_input("Gestor técnico", value=clean_input(selected.get("technical_manager")) if selected is not None else "")
                    requires_operator = st.checkbox("Requer operador", value=truthy(selected.get("requires_operator")) if selected is not None else False)
                with c3:
                    current_status = selected.get("operational_status") if selected is not None else "available"
                    status_label = st.selectbox(
                        "Status operacional",
                        list(EQUIPMENT_STATUS_LABELS.values()),
                        index=list(EQUIPMENT_STATUS_LABELS.keys()).index(current_status) if current_status in EQUIPMENT_STATUS_LABELS else 0,
                        key="equipment_master_status",
                    )
                    raw_capacity = selected.get("max_sample_capacity") if selected is not None else None
                    initial_capacity = int(raw_capacity) if not is_blank(raw_capacity) and raw_capacity else 0
                    max_sample_capacity = st.number_input("Capacidade máxima", min_value=0, value=initial_capacity, step=1, key="equipment_master_capacity")
                    capacity_unit = st.text_input("Unidade da capacidade", value=clean_value(selected.get("capacity_unit"), "amostras") if selected is not None else "amostras")
                    capacity_enforced = st.checkbox("Bloquear acima da capacidade", value=truthy(selected.get("capacity_enforced")) if selected is not None else False, key="equipment_master_enforce")
                    active = st.checkbox("Equipamento ativo", value=truthy(selected.get("active")) if selected is not None else True)

                unavailable_functions = st.text_area("Funcionalidades indisponíveis", value=clean_input(selected.get("unavailable_functions")) if selected is not None else "")
                notes = st.text_area("Observações", value=clean_input(selected.get("notes")) if selected is not None else "")
                st.markdown("#### POP / documentação operacional")
                d1, d2, d3 = st.columns(3)
                with d1:
                    pop_title = st.text_input("Título do POP", value=clean_input(selected.get("pop_title")) if selected is not None else "")
                    pop_version = st.text_input("Versão do POP", value=clean_input(selected.get("pop_version")) if selected is not None else "")
                with d2:
                    pop_path = st.text_input("Arquivo/link do POP", value=clean_input(selected.get("pop_path")) if selected is not None else "")
                    pop_updated_at = st.text_input("Data de atualização do POP", value=clean_input(selected.get("pop_updated_at")) if selected is not None else "")
                with d3:
                    pop_responsible = st.text_input("Responsável pelo POP", value=clean_input(selected.get("pop_responsible")) if selected is not None else "")
                    document_notes = st.text_area("Observações documentais", value=clean_input(selected.get("document_notes")) if selected is not None else "")

                submitted = st.form_submit_button("Salvar equipamento", type="primary")

            if submitted:
                payload = dict(
                    equipment_code=equipment_code,
                    equipment_name=equipment_name,
                    lab_unit=lab_unit.strip() or None,
                    location=location.strip() or None,
                    requires_operator=int(requires_operator),
                    responsible_name=responsible_name.strip() or None,
                    responsible_phone=responsible_phone.strip() or None,
                    active=int(active),
                    operational_status=EQUIPMENT_STATUS_REVERSE[status_label],
                    unavailable_functions=unavailable_functions.strip() or None,
                    max_sample_capacity=int(max_sample_capacity) if max_sample_capacity else None,
                    capacity_unit=capacity_unit.strip() or "amostras",
                    capacity_enforced=int(capacity_enforced),
                    technical_manager=technical_manager.strip() or None,
                    pop_title=pop_title.strip() or None,
                    pop_path=pop_path.strip() or None,
                    pop_version=pop_version.strip() or None,
                    pop_updated_at=pop_updated_at.strip() or None,
                    pop_responsible=pop_responsible.strip() or None,
                    document_notes=document_notes.strip() or None,
                    notes=notes.strip() or None,
                )
                if mode == "Novo equipamento":
                    ok, msg = create_equipment(conn, **payload)
                else:
                    old_status = clean_input(selected.get("operational_status")) or "available"
                    ok, msg = update_equipment_master(conn, int(equipment_id), **payload)
                    if ok and payload["operational_status"] == "maintenance" and old_status != "maintenance":
                        sent, total = notify_equipment_maintenance(
                            conn,
                            equipment_id=int(equipment_id),
                            title="equipamento em manutenção",
                            message=(
                                "O equipamento foi marcado como EM MANUTENÇÃO no cadastro mestre.\n"
                                f"Observações: {payload.get('notes') or payload.get('unavailable_functions') or 'Sem observações adicionais.'}"
                            ),
                            related_table="equipment",
                            related_id=int(equipment_id),
                        )
                        if total:
                            st.info(f"Notificação de manutenção registrada para {total} destinatário(s). Enviadas: {sent}.")
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    with st.expander("Biblioteca de POPs disponíveis no projeto"):
        docs = sorted(POP_DIR.glob("*.pdf")) if POP_DIR.exists() else []
        if not docs:
            st.info("Nenhum PDF de POP encontrado em assets/pops.")
        else:
            for idx, doc in enumerate(docs):
                st.download_button(
                    f"📄 {doc.name}",
                    data=doc.read_bytes(),
                    file_name=doc.name,
                    mime="application/pdf",
                    key=f"library_pop_{idx}_{doc.name}",
                )



def _equipment_options(equipment: pd.DataFrame) -> list[str]:
    return equipment.apply(lambda r: f"{clean_value(r.get('equipment_code'))} — {clean_value(r.get('equipment_name'))}", axis=1).tolist()


def _equipment_id_from_label(equipment: pd.DataFrame, label: str) -> int:
    labels = _equipment_options(equipment)
    return int(equipment.iloc[labels.index(label)]["id"])


def _current_user_id() -> int | None:
    user = current_user()
    try:
        return int(user.get("id")) if user.get("id") is not None else None
    except Exception:
        return None


def _attachment_ref(attachment_id: int) -> str:
    return f"attachment:{int(attachment_id)}"


def _attachment_id_from_ref(path_value) -> int | None:
    path_text = clean_input(path_value)
    if not path_text.lower().startswith("attachment:"):
        return None
    try:
        return int(path_text.split(":", 1)[1])
    except Exception:
        return None


def _ensure_storage_ready_for_upload(*uploaded_files) -> bool:
    if not any(uploaded_file is not None for uploaded_file in uploaded_files):
        return True
    try:
        get_active_storage_backend(database_url=_database_url())
        return True
    except StorageConfigurationError as exc:
        st.error(str(exc))
        return False


def _save_upload(
    conn,
    uploaded_file,
    *,
    entity_type: str,
    entity_id: int,
    attachment_role: str,
    notes: str | None = None,
) -> str | None:
    if uploaded_file is None:
        return None
    backend = get_active_storage_backend(database_url=_database_url())
    content = uploaded_file.getvalue()
    stored = backend.save_file(
        entity_type=entity_type,
        entity_id=int(entity_id),
        original_filename=uploaded_file.name,
        content=content,
        mime_type=getattr(uploaded_file, "type", None),
    )
    attachment_id = create_attachment(
        conn,
        entity_type=entity_type,
        entity_id=int(entity_id),
        attachment_role=attachment_role,
        original_filename=stored.original_filename,
        storage_key=stored.storage_key,
        storage_backend=stored.storage_backend,
        mime_type=stored.mime_type,
        file_size=stored.file_size,
        sha256=stored.sha256,
        uploaded_by_id=_current_user_id(),
        notes=notes,
    )
    return _attachment_ref(attachment_id)


def _supply_options(supplies: pd.DataFrame) -> list[str]:
    def _label(r: pd.Series) -> str:
        qty = 0.0 if is_blank(r.get("current_quantity")) else float(r.get("current_quantity"))
        item_type = clean_value(r.get("supply_type"), "Insumo")
        code = clean_input(r.get("supply_code"))
        code_text = f"{code} · " if code else ""
        return f"{int(r['id'])} — {code_text}{clean_value(r.get('supply_name'))} · {item_type} · saldo: {qty:g} {clean_value(r.get('unit'), '')}"
    return supplies.apply(_label, axis=1).tolist()


def _supply_id_from_label(supplies: pd.DataFrame, label: str) -> int:
    labels = _supply_options(supplies)
    return int(supplies.iloc[labels.index(label)]["id"])


def _supply_type_value(row: pd.Series | None) -> str:
    value = clean_input(row.get("supply_type")) if row is not None else ""
    return value if value in SUPPLY_TYPES else "Insumo"


def _is_spare_part(row: pd.Series | None) -> bool:
    return _supply_type_value(row) == "Peça de reposição"


def _spare_part_stock_status(row: pd.Series) -> str:
    qty = float(row.get("current_quantity") or 0)
    min_qty = float(row.get("minimum_quantity") or 0)
    return "Abaixo do mínimo" if qty < min_qty else "OK"


def _equipment_ids_from_labels(equipment: pd.DataFrame, labels: list[str]) -> list[int]:
    if equipment.empty:
        return []
    return [_equipment_id_from_label(equipment, label) for label in labels]


def render_equipment_spare_parts(spare_parts: pd.DataFrame) -> None:
    if spare_parts.empty:
        st.info("Nenhuma peça de reposição associada a este equipamento.")
        return
    display = spare_parts.copy()
    display["stock_status"] = display.apply(_spare_part_stock_status, axis=1)
    cols = [
        "supply_name",
        "supply_code",
        "manufacturer_code",
        "manufacturer",
        "current_quantity",
        "unit",
        "minimum_quantity",
        "stock_status",
        "location",
        "compatible_model_family",
        "association_notes",
    ]
    st.dataframe(
        _display_df(display[[c for c in cols if c in display.columns]]),
        use_container_width=True,
        hide_index=True,
    )


def _select_index_by_supply_id(supplies: pd.DataFrame, supply_id: str | int | None) -> int:
    if supply_id is None or supplies.empty:
        return 0
    try:
        supply_id = int(supply_id)
    except Exception:
        return 0
    ids = supplies["id"].astype(int).tolist()
    return ids.index(supply_id) if supply_id in ids else 0


def _render_attachment_download(attachment_row, label: str, key: str) -> bool:
    if not attachment_row:
        return False
    try:
        backend = get_storage_backend_for_name(attachment_row["storage_backend"])
        filename = clean_value(attachment_row["original_filename"], "arquivo")
        mime = clean_value(attachment_row["mime_type"], "application/octet-stream")
        if isinstance(backend, R2StorageBackend):
            url = backend.generate_download_url(attachment_row["storage_key"], filename)
            st.link_button(label, url)
            return True
        if isinstance(backend, LocalStorageBackend):
            st.download_button(
                label,
                data=backend.get_file_bytes(attachment_row["storage_key"]),
                file_name=filename,
                mime=mime,
                key=key,
            )
            return True
    except Exception as exc:
        st.warning(f"Não foi possível abrir o anexo persistido: {exc}")
    return False


def _format_file_size(size_value) -> str:
    try:
        size = int(size_value or 0)
    except Exception:
        return "-"
    if size <= 0:
        return "-"
    value = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"


def _attachment_metadata_caption(attachment_row) -> str:
    details = [
        _format_file_size(attachment_row["file_size"] if "file_size" in attachment_row.keys() else None),
        _format_datetime(attachment_row["uploaded_at"] if "uploaded_at" in attachment_row.keys() else None),
    ]
    backend = clean_input(attachment_row["storage_backend"] if "storage_backend" in attachment_row.keys() else "")
    if backend:
        details.append(f"armazenado em {backend.upper() if backend == 'r2' else backend}")
    return " · ".join(detail for detail in details if detail and detail != "-")


def render_attachment_list(
    conn,
    *,
    entity_type: str,
    entity_id: int,
    attachment_role: str,
    legacy_path=None,
    key_prefix: str,
    title: str | None = "Anexos cadastrados",
    empty_message: str = "Nenhum anexo cadastrado.",
) -> None:
    if title:
        st.markdown(f"##### {title}")
    rows = list_attachments(
        conn,
        entity_type=entity_type,
        entity_id=int(entity_id),
        attachment_role=attachment_role,
    )
    rendered = False
    for row in rows:
        rendered = True
        filename = clean_value(row["original_filename"], "arquivo")
        st.caption(f"{filename} · {_attachment_metadata_caption(row)}")
        _render_attachment_download(row, "Baixar", f"{key_prefix}_attachment_{int(row['id'])}")

    listed_ids = {int(row["id"]) for row in rows}
    legacy_attachment_id = _attachment_id_from_ref(legacy_path)
    if legacy_attachment_id is not None and legacy_attachment_id not in listed_ids:
        legacy_attachment = get_attachment(conn, legacy_attachment_id)
        if legacy_attachment is not None:
            rendered = True
            filename = clean_value(legacy_attachment["original_filename"], "arquivo")
            st.caption(f"{filename} · {_attachment_metadata_caption(legacy_attachment)}")
            _render_attachment_download(legacy_attachment, "Baixar", f"{key_prefix}_legacy_attachment_{legacy_attachment_id}")

    if not rendered and not is_blank(legacy_path):
        rendered = True
        _download_or_link_document(conn, legacy_path, "Baixar anexo legado", f"{key_prefix}_legacy")

    if not rendered:
        st.caption(empty_message)


def _download_or_link_document(
    conn,
    path_value,
    label: str,
    key: str,
    *,
    entity_type: str | None = None,
    entity_id: int | None = None,
    attachment_role: str | None = None,
) -> None:
    if entity_type and entity_id is not None:
        latest = get_latest_attachment_for_entity(
            conn,
            entity_type=entity_type,
            entity_id=int(entity_id),
            attachment_role=attachment_role,
        )
        if _render_attachment_download(latest, label, key):
            return

    attachment_id = _attachment_id_from_ref(path_value)
    if attachment_id is not None and _render_attachment_download(get_attachment(conn, attachment_id), label, key):
        return

    path_text = clean_input(path_value)
    if not path_text:
        return
    if path_text.lower().startswith(("http://", "https://")):
        st.link_button(label, path_text)
        return
    doc_path = _resolve_local_doc(path_text)
    if doc_path:
        mime = "application/pdf" if doc_path.suffix.lower() == ".pdf" else "application/octet-stream"
        st.download_button(label, data=doc_path.read_bytes(), file_name=doc_path.name, mime=mime, key=key)


def render_supply_quick_card(conn, supply_row: pd.Series) -> None:
    alert = _supply_alert_status(supply_row)
    qty = 0.0 if is_blank(supply_row.get("current_quantity")) else float(supply_row.get("current_quantity"))
    min_qty = 0.0 if is_blank(supply_row.get("minimum_quantity")) else float(supply_row.get("minimum_quantity"))
    type_line = f"Tipo: {clean_value(supply_row.get('supply_type'), 'Insumo')} · "
    if _is_spare_part(supply_row):
        type_line += (
            f"Código interno: {clean_value(supply_row.get('supply_code'))} · "
            f"Código fabricante: {clean_value(supply_row.get('manufacturer_code'))}<br>"
            f"Modelo/família compatível: {clean_value(supply_row.get('compatible_model_family'))}<br>"
        )
    st.markdown(
        f"""
        <div class="soft-card">
        <b>{clean_value(supply_row.get('supply_name'))}</b><br>
        {type_line}
        Categoria: {clean_value(supply_row.get('category'))} · Estado: {clean_value(supply_row.get('physical_state'))} ·
        Fabricante: {clean_value(supply_row.get('manufacturer'))}<br>
        Saldo: <b>{qty:g} {clean_value(supply_row.get('unit'), '')}</b> · Estoque mínimo: {min_qty:g} {clean_value(supply_row.get('unit'), '')}<br>
        Lote: {clean_value(supply_row.get('lot'))} · Validade: {_format_datetime(supply_row.get('expiration_date'))} ·
        Localização: {clean_value(supply_row.get('location'))}<br>
        Responsável: {clean_value(supply_row.get('responsible_name'))} · Status: <b>{alert}</b>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        _download_or_link_document(
            conn,
            supply_row.get("safety_doc_path"),
            "📄 Baixar/abrir FDS/FISPQ",
            f"supply_safety_qr_{int(supply_row['id'])}",
            entity_type="supply",
            entity_id=int(supply_row["id"]),
            attachment_role="safety_doc",
        )
    with c2:
        _download_or_link_document(
            conn,
            supply_row.get("technical_doc_path"),
            "📎 Baixar/abrir ficha técnica",
            f"supply_technical_qr_{int(supply_row['id'])}",
            entity_type="supply",
            entity_id=int(supply_row["id"]),
            attachment_role="technical_doc",
        )


def _project_id_from_label(projects: pd.DataFrame, label: str) -> int | None:
    options = _project_options(projects)
    if label == "Sem projeto específico" or projects.empty:
        return None
    return int(projects.iloc[options.index(label) - 1]["id"])


def _user_id_from_label(users: pd.DataFrame, label: str) -> int | None:
    options = ["Não informado"] + _user_options(users)
    if label == "Não informado" or users.empty:
        return None
    return int(users.iloc[options.index(label) - 1]["id"])


def _supply_alert_status(row: pd.Series) -> str:
    qty = float(row.get("current_quantity") or 0)
    min_qty = float(row.get("minimum_quantity") or 0)
    if min_qty and (qty < min_qty if _is_spare_part(row) else qty <= min_qty):
        return "Estoque baixo"
    exp = row.get("expiration_date")
    if not is_blank(exp):
        try:
            exp_date = datetime.fromisoformat(str(exp)).date()
            today = date.today()
            if exp_date < today:
                return "Vencido"
            if exp_date <= today + timedelta(days=60):
                return "Vence em até 60 dias"
        except Exception:
            pass
    if not _is_spare_part(row) and is_blank(row.get("safety_doc_path")):
        return "Sem FDS/FISPQ"
    return "OK"


def page_insumos(conn):
    hero()
    st.subheader("Insumos e almoxarifado")
    st.caption("Controle simples de estoque: cadastro mínimo, saldo atual, lote, validade, localização, documentos e histórico de movimentações.")

    supplies = query_df(conn, "SELECT * FROM supplies ORDER BY active DESC, supply_name")
    users = query_df(conn, "SELECT * FROM users WHERE active=1 ORDER BY full_name")
    projects = query_df(conn, "SELECT * FROM projects WHERE active=1 ORDER BY project_name")
    equipment = query_df(conn, "SELECT * FROM equipment ORDER BY active DESC, equipment_code")

    qr_supply_id = st.query_params.get("sid", None)
    if qr_supply_id and not supplies.empty:
        try:
            qr_supply_id_int = int(qr_supply_id)
            qr_supply = supplies[supplies["id"].astype(int) == qr_supply_id_int]
        except Exception:
            qr_supply = pd.DataFrame()
        if not qr_supply.empty:
            st.markdown("### Ficha rápida do insumo")
            render_supply_quick_card(conn, qr_supply.iloc[0])
            st.info("QR de insumo detectado. Use a aba **Movimentar estoque** para registrar entrada, saída, descarte ou ajuste.")
        else:
            st.warning("QR de insumo detectado, mas o insumo não foi encontrado no banco atual.")

    tab_visao, tab_cadastro, tab_mov, tab_hist = st.tabs([
        "Visão geral",
        "Cadastrar/editar insumo",
        "Movimentar estoque",
        "Histórico",
    ])

    with tab_visao:
        st.markdown("### Visão geral do almoxarifado")
        active_supplies = supplies[supplies["active"] == 1].copy() if not supplies.empty else supplies
        if supplies.empty:
            st.info("Nenhum insumo cadastrado ainda.")
        else:
            active_supplies["alerta"] = active_supplies.apply(_supply_alert_status, axis=1)
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Itens ativos", int((supplies["active"] == 1).sum()))
            k2.metric("Estoque baixo", int((active_supplies["alerta"] == "Estoque baixo").sum()))
            k3.metric("Vencidos", int((active_supplies["alerta"] == "Vencido").sum()))
            k4.metric("Sem FDS/FISPQ", int((active_supplies["alerta"] == "Sem FDS/FISPQ").sum()))

            alert_df = active_supplies[active_supplies["alerta"] != "OK"].copy()
            if not alert_df.empty:
                st.markdown("#### Alertas")
                st.dataframe(
                    _display_df(alert_df[[
                        "alerta", "supply_type", "supply_name", "supply_code", "category",
                        "current_quantity", "unit", "minimum_quantity", "lot",
                        "expiration_date", "location", "responsible_name"
                    ]]),
                    use_container_width=True,
                    hide_index=True,
                )
            st.markdown("#### Estoque atual")
            cols = [
                "supply_type", "supply_name", "supply_code", "manufacturer_code",
                "commercial_name", "manufacturer", "category", "physical_state",
                "compatible_model_family", "current_quantity", "unit", "minimum_quantity",
                "lot", "expiration_date", "location", "responsible_name", "active"
            ]
            st.dataframe(_display_df(supplies[[c for c in cols if c in supplies.columns]]), use_container_width=True, hide_index=True)
            st.download_button(
                "Baixar estoque em CSV",
                data=_display_df(supplies).to_csv(index=False).encode("utf-8-sig"),
                file_name="labcim_insumos_estoque.csv",
                mime="text/csv",
            )

    with tab_cadastro:
        st.markdown("### Cadastro de item de estoque")
        if not can_manage_master_data():
            st.info("Membros podem registrar entrada, saída e descarte na aba **Movimentar estoque**. Cadastro/edição estrutural de insumos fica com Gerente ou Administrador.")
        mode = st.radio("Modo", ["Novo item", "Editar item existente"], horizontal=True, key="supply_edit_mode")
        selected_supply = None
        if mode == "Editar item existente":
            if supplies.empty:
                st.info("Cadastre um item de estoque antes de editar.")
                return
            label = st.selectbox("Selecionar item", _supply_options(supplies), key="supply_edit_select")
            selected_supply = supplies[supplies["id"] == _supply_id_from_label(supplies, label)].iloc[0]

        current_supply_type = _supply_type_value(selected_supply)
        supply_type_key = f"supply_type_{mode}_{int(selected_supply['id']) if selected_supply is not None else 'new'}"
        supply_type = st.radio(
            "Tipo de item",
            SUPPLY_TYPES,
            index=SUPPLY_TYPES.index(current_supply_type),
            horizontal=True,
            key=supply_type_key,
        )
        is_spare_part = supply_type == "Peça de reposição"
        selected_equipment_ids: list[int] = []
        current_item_is_spare_part = _is_spare_part(selected_supply)

        with st.form("form_supply"):
            c1, c2, c3 = st.columns(3)
            with c1:
                supply_name = st.text_input(
                    "Nome da peça *" if is_spare_part else "Nome do insumo *",
                    value=clean_input(selected_supply.get("supply_name")) if selected_supply is not None else "",
                    placeholder="Ex.: rotor, vedação, filtro" if is_spare_part else "Ex.: Cimento Portland Classe G",
                )
                supply_code = clean_input(selected_supply.get("supply_code")) if selected_supply is not None else ""
                manufacturer_code = clean_input(selected_supply.get("manufacturer_code")) if selected_supply is not None else ""
                compatible_model_family = clean_input(selected_supply.get("compatible_model_family")) if selected_supply is not None else ""
                if is_spare_part:
                    supply_code = st.text_input("Código interno", value=supply_code, placeholder="Ex.: PR-0001")
                commercial_name = st.text_input("Nome comercial", value=clean_input(selected_supply.get("commercial_name")) if selected_supply is not None else "")
                manufacturer = st.text_input("Fabricante", value=clean_input(selected_supply.get("manufacturer")) if selected_supply is not None else "")
                if is_spare_part:
                    manufacturer_code = st.text_input("Código do fabricante", value=manufacturer_code, placeholder="Ex.: part number, SKU ou referência do fabricante")
                    category = st.text_input(
                        "Categoria",
                        value=clean_input(selected_supply.get("category")) if selected_supply is not None else "",
                        placeholder="Ex.: filtro, vedação, sensor, placa eletrônica",
                    )
                else:
                    category = st.selectbox(
                        "Categoria",
                        ["Cimento", "Aditivo", "Sal", "Polímero", "Pozolana", "Carga mineral", "Lavador/espaçador", "Reagente", "Consumível", "Outro"],
                        index=0,
                        key="supply_category",
                    )
                    if selected_supply is not None and clean_input(selected_supply.get("category")):
                        category = st.text_input("Categoria cadastrada", value=clean_input(selected_supply.get("category")))
            with c2:
                if is_spare_part:
                    physical_state = clean_input(selected_supply.get("physical_state")) if current_item_is_spare_part and selected_supply is not None else ""
                    physical_state = physical_state or "Não se aplica"
                    application_function = clean_input(selected_supply.get("application_function")) if current_item_is_spare_part and selected_supply is not None else ""
                    addition_mode = clean_input(selected_supply.get("addition_mode")) if current_item_is_spare_part and selected_supply is not None else ""
                    addition_mode = addition_mode or "Não se aplica"
                    compatible_model_family = st.text_input("Modelo/família compatível", value=compatible_model_family, placeholder="Ex.: Reômetro modelo X, Autoclave série Y")
                    unit = clean_input(selected_supply.get("unit")) if current_item_is_spare_part and selected_supply is not None else ""
                    unit = unit or "unidade"
                else:
                    physical_state = st.selectbox("Estado físico", ["Sólido", "Líquido", "Gás", "Pasta/suspensão", "Outro"], key="supply_state")
                    if selected_supply is not None and clean_input(selected_supply.get("physical_state")):
                        physical_state = st.text_input("Estado físico cadastrado", value=clean_input(selected_supply.get("physical_state")))
                    application_function = st.text_input("Função/aplicação", value=clean_input(selected_supply.get("application_function")) if selected_supply is not None else "", placeholder="Ex.: retardador, expansivo, salmoura, cimento base")
                    addition_mode = st.selectbox("Modo de adição", ["Não se aplica", "Misturado a seco", "Água de mistura", "Solução", "Outro"], key="supply_addition")
                    if selected_supply is not None and clean_input(selected_supply.get("addition_mode")):
                        addition_mode = st.text_input("Modo de adição cadastrado", value=clean_input(selected_supply.get("addition_mode")))
                    unit = st.selectbox("Unidade de controle", ["kg", "g", "L", "mL", "unidade", "frasco", "saco"], key="supply_unit")
                    if selected_supply is not None and clean_input(selected_supply.get("unit")):
                        unit = st.text_input("Unidade cadastrada", value=clean_input(selected_supply.get("unit")))
            with c3:
                initial_qty_default = float(selected_supply.get("current_quantity") or 0) if selected_supply is not None else 0.0
                current_quantity = st.number_input("Saldo inicial/atual", min_value=0.0, value=initial_qty_default, step=1.0, disabled=(mode == "Editar item existente"), help="Depois do cadastro, o saldo deve ser alterado por movimentações.")
                min_qty_default = float(selected_supply.get("minimum_quantity") or 0) if selected_supply is not None else 0.0
                minimum_quantity = st.number_input("Estoque mínimo", min_value=0.0, value=min_qty_default, step=1.0)
                lot = st.text_input("Lote", value=clean_input(selected_supply.get("lot")) if selected_supply is not None else "")
                expiration_date = _date_input_value(selected_supply.get("expiration_date")) if is_spare_part and selected_supply is not None else None
                if not is_spare_part:
                    expiration_date = st.date_input(
                        "Validade",
                        value=None if selected_supply is None or is_blank(selected_supply.get("expiration_date")) else datetime.fromisoformat(str(selected_supply.get("expiration_date"))).date(),
                        key="supply_expiration",
                    )
                location = st.text_input("Localização", value=clean_input(selected_supply.get("location")) if selected_supply is not None else "", placeholder="Ex.: Almoxarifado 1, armário A")
                responsible_name = st.text_input("Responsável", value=clean_input(selected_supply.get("responsible_name")) if selected_supply is not None else "")

            density = selected_supply.get("density") if selected_supply is not None else None
            recommended_concentration = clean_input(selected_supply.get("recommended_concentration")) if selected_supply is not None else ""
            recommended_temperature = clean_input(selected_supply.get("recommended_temperature")) if selected_supply is not None else ""
            characterization_summary = clean_input(selected_supply.get("characterization_summary")) if selected_supply is not None else ""
            safety_doc_path = clean_input(selected_supply.get("safety_doc_path")) if selected_supply is not None else ""
            technical_doc_path = clean_input(selected_supply.get("technical_doc_path")) if selected_supply is not None else ""
            safety_upload = None
            technical_upload = None
            if not is_spare_part:
                st.markdown("#### Dados técnicos opcionais")
                t1, t2, t3 = st.columns(3)
                with t1:
                    density_default = float(selected_supply.get("density") or 0) if selected_supply is not None and not is_blank(selected_supply.get("density")) else 0.0
                    density = st.number_input("Massa específica", min_value=0.0, value=density_default, step=0.01)
                    recommended_concentration = st.text_input("Faixa de concentração", value=recommended_concentration, placeholder="Ex.: 0,5–3,0% BWOC")
                with t2:
                    recommended_temperature = st.text_input("Faixa de temperatura", value=recommended_temperature, placeholder="Ex.: 25–90 °C")
                    characterization_summary = st.text_area("Caracterização resumida", value=characterization_summary, placeholder="Ex.: FRX/DRX realizados; arquivo anexado...")
                with t3:
                    safety_doc_path = st.text_input("FDS/FISPQ existente ou link", value=safety_doc_path)
                    technical_doc_path = st.text_input("Ficha técnica/caracterização existente ou link", value=technical_doc_path)
                    safety_upload = st.file_uploader("Anexar FDS/FISPQ", type=["pdf", "png", "jpg", "jpeg"], key="safety_doc_upload")
                    technical_upload = st.file_uploader("Anexar ficha/caracterização", type=["pdf", "png", "jpg", "jpeg", "xlsx"], key="technical_doc_upload")

            if is_spare_part:
                st.markdown("#### Equipamentos associados")
                if equipment.empty:
                    st.info("Cadastre equipamentos antes de associar peças de reposição.")
                else:
                    linked_equipment = (
                        list_equipment_for_spare_part(conn, int(selected_supply["id"]))
                        if selected_supply is not None
                        else pd.DataFrame()
                    )
                    linked_ids = set(linked_equipment["id"].astype(int).tolist()) if not linked_equipment.empty else set()
                    equipment_options = _equipment_options(equipment)
                    default_equipment_labels = [
                        label for label in equipment_options
                        if _equipment_id_from_label(equipment, label) in linked_ids
                    ]
                    selected_equipment_labels = st.multiselect(
                        "Equipamentos associados",
                        equipment_options,
                        default=default_equipment_labels,
                        key=f"spare_equipment_links_{int(selected_supply['id']) if selected_supply is not None else 'new'}",
                    )
                    selected_equipment_ids = _equipment_ids_from_labels(equipment, selected_equipment_labels)

            notes = st.text_area("Observações", value=clean_input(selected_supply.get("notes")) if selected_supply is not None else "")
            active = st.checkbox("Item ativo", value=True if selected_supply is None else truthy(selected_supply.get("active")))
            submitted = st.form_submit_button("Salvar insumo", type="primary")

        if selected_supply is not None and not is_spare_part:
            st.markdown("#### Documentos cadastrados")
            a1, a2 = st.columns(2)
            with a1:
                render_attachment_list(
                    conn,
                    entity_type="supply",
                    entity_id=int(selected_supply["id"]),
                    attachment_role="safety_doc",
                    legacy_path=selected_supply.get("safety_doc_path"),
                    key_prefix=f"supply_{int(selected_supply['id'])}_safety_doc",
                    title="FDS/FISPQ",
                    empty_message="Nenhuma FDS/FISPQ cadastrada.",
                )
            with a2:
                render_attachment_list(
                    conn,
                    entity_type="supply",
                    entity_id=int(selected_supply["id"]),
                    attachment_role="technical_doc",
                    legacy_path=selected_supply.get("technical_doc_path"),
                    key_prefix=f"supply_{int(selected_supply['id'])}_technical_doc",
                    title="Ficha técnica/caracterização",
                    empty_message="Nenhuma ficha técnica/caracterização cadastrada.",
                )

        if submitted:
            if not can_manage_master_data():
                st.error("Cadastro/edição estrutural de insumos exige perfil Gerente ou Administrador.")
            elif not supply_name.strip():
                st.error("Informe o nome do item.")
            elif not _ensure_storage_ready_for_upload(safety_upload, technical_upload):
                pass
            else:
                if mode == "Novo item":
                    supply_id = create_supply(
                        conn,
                        supply_type=supply_type,
                        supply_name=supply_name.strip(),
                        supply_code=supply_code.strip() or None,
                        commercial_name=commercial_name.strip() or None,
                        manufacturer=manufacturer.strip() or None,
                        manufacturer_code=manufacturer_code.strip() or None,
                        category=category.strip() or None,
                        physical_state=physical_state.strip() or None,
                        application_function=application_function.strip() or None,
                        addition_mode=addition_mode.strip() or None,
                        compatible_model_family=compatible_model_family.strip() or None,
                        unit=unit.strip() or "kg",
                        current_quantity=0.0,
                        minimum_quantity=float(minimum_quantity),
                        lot=lot.strip() or None,
                        expiration_date=expiration_date.isoformat() if expiration_date else None,
                        location=location.strip() or None,
                        responsible_name=responsible_name.strip() or None,
                        safety_doc_path=safety_doc_path.strip() or None,
                        technical_doc_path=technical_doc_path.strip() or None,
                        density=float(density) if density else None,
                        recommended_concentration=recommended_concentration.strip() or None,
                        recommended_temperature=recommended_temperature.strip() or None,
                        characterization_summary=characterization_summary.strip() or None,
                        notes=notes.strip() or None,
                    )
                    if is_spare_part:
                        set_spare_part_equipment_links(
                            conn,
                            supply_id=supply_id,
                            equipment_ids=selected_equipment_ids,
                        )
                    if current_quantity:
                        create_supply_movement(
                            conn,
                            supply_id=supply_id,
                            movement_type="entrada",
                            movement_date=date.today().isoformat(),
                            quantity=float(current_quantity),
                            user_id=None,
                            project_id=None,
                            purpose="Saldo inicial cadastrado.",
                            document_path=None,
                        )
                    if safety_upload is not None:
                        safety_ref = _save_upload(
                            conn,
                            safety_upload,
                            entity_type="supply",
                            entity_id=supply_id,
                            attachment_role="safety_doc",
                        )
                        update_legacy_attachment_path(
                            conn,
                            table="supplies",
                            row_id=supply_id,
                            column="safety_doc_path",
                            value=safety_ref,
                        )
                    if technical_upload is not None:
                        technical_ref = _save_upload(
                            conn,
                            technical_upload,
                            entity_type="supply",
                            entity_id=supply_id,
                            attachment_role="technical_doc",
                        )
                        update_legacy_attachment_path(
                            conn,
                            table="supplies",
                            row_id=supply_id,
                            column="technical_doc_path",
                            value=technical_ref,
                        )
                    st.success("Item cadastrado com sucesso.")
                    st.rerun()
                else:
                    supply_id = int(selected_supply["id"])
                    safety_final = safety_doc_path.strip() or None
                    technical_final = technical_doc_path.strip() or None
                    if safety_upload is not None:
                        safety_final = _save_upload(
                            conn,
                            safety_upload,
                            entity_type="supply",
                            entity_id=supply_id,
                            attachment_role="safety_doc",
                        )
                    if technical_upload is not None:
                        technical_final = _save_upload(
                            conn,
                            technical_upload,
                            entity_type="supply",
                            entity_id=supply_id,
                            attachment_role="technical_doc",
                        )
                    update_supply(
                        conn,
                        supply_id,
                        supply_type=supply_type,
                        supply_name=supply_name.strip(),
                        supply_code=supply_code.strip() or None,
                        commercial_name=commercial_name.strip() or None,
                        manufacturer=manufacturer.strip() or None,
                        manufacturer_code=manufacturer_code.strip() or None,
                        category=category.strip() or None,
                        physical_state=physical_state.strip() or None,
                        application_function=application_function.strip() or None,
                        addition_mode=addition_mode.strip() or None,
                        compatible_model_family=compatible_model_family.strip() or None,
                        unit=unit.strip() or "kg",
                        minimum_quantity=float(minimum_quantity),
                        lot=lot.strip() or None,
                        expiration_date=expiration_date.isoformat() if expiration_date else None,
                        location=location.strip() or None,
                        responsible_name=responsible_name.strip() or None,
                        safety_doc_path=safety_final,
                        technical_doc_path=technical_final,
                        density=float(density) if density else None,
                        recommended_concentration=recommended_concentration.strip() or None,
                        recommended_temperature=recommended_temperature.strip() or None,
                        characterization_summary=characterization_summary.strip() or None,
                        active=int(active),
                        notes=notes.strip() or None,
                    )
                    set_spare_part_equipment_links(
                        conn,
                        supply_id=supply_id,
                        equipment_ids=selected_equipment_ids if is_spare_part else [],
                    )
                    st.success("Item atualizado com sucesso.")
                    st.rerun()

    with tab_mov:
        st.markdown("### Movimentar estoque")
        active_supplies = supplies[supplies["active"] == 1].copy() if not supplies.empty else supplies
        if active_supplies.empty:
            st.info("Cadastre ao menos um item ativo para movimentar estoque.")
        else:
            with st.form("form_supply_movement"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    supply_label = st.selectbox(
                        "Item de estoque",
                        _supply_options(active_supplies),
                        index=_select_index_by_supply_id(active_supplies, qr_supply_id),
                        key="movement_supply",
                    )
                    supply_id = _supply_id_from_label(active_supplies, supply_label)
                    movement_type = st.selectbox("Tipo de movimentação", ["entrada", "saída", "descarte", "ajuste positivo", "ajuste negativo"])
                    movement_date = st.date_input("Data", value=date.today(), key="movement_date")
                with c2:
                    quantity = st.number_input("Quantidade", min_value=0.0, value=0.0, step=1.0, key="movement_qty")
                    user_label = st.selectbox("Responsável pela movimentação", ["Não informado"] + _user_options(users), key="movement_user")
                    project_label = st.selectbox("Projeto", _project_options(projects), key="movement_project")
                with c3:
                    purpose = st.text_area("Finalidade/observação", placeholder="Ex.: preparo de pasta; recebimento de material; descarte por vencimento...")
                    movement_doc = st.file_uploader("Anexo da movimentação", type=["pdf", "png", "jpg", "jpeg", "xlsx"], key="movement_doc")
                move_submitted = st.form_submit_button("Registrar movimentação", type="primary")

            selected_movement_supply = active_supplies[active_supplies["id"].astype(int) == int(supply_id)].iloc[0]
            st.markdown("#### Documentos do item selecionado")
            d1, d2 = st.columns(2)
            with d1:
                render_attachment_list(
                    conn,
                    entity_type="supply",
                    entity_id=int(supply_id),
                    attachment_role="safety_doc",
                    legacy_path=selected_movement_supply.get("safety_doc_path"),
                    key_prefix=f"movement_supply_{int(supply_id)}_safety_doc",
                    title="FDS/FISPQ",
                    empty_message="Nenhuma FDS/FISPQ cadastrada.",
                )
            with d2:
                render_attachment_list(
                    conn,
                    entity_type="supply",
                    entity_id=int(supply_id),
                    attachment_role="technical_doc",
                    legacy_path=selected_movement_supply.get("technical_doc_path"),
                    key_prefix=f"movement_supply_{int(supply_id)}_technical_doc",
                    title="Ficha técnica/caracterização",
                    empty_message="Nenhuma ficha técnica/caracterização cadastrada.",
                )

            if move_submitted:
                if _ensure_storage_ready_for_upload(movement_doc):
                    ok, msg, movement_id = create_supply_movement(
                        conn,
                        supply_id=supply_id,
                        movement_type=movement_type,
                        movement_date=movement_date.isoformat(),
                        quantity=float(quantity),
                        user_id=_user_id_from_label(users, user_label),
                        project_id=_project_id_from_label(projects, project_label),
                        purpose=purpose.strip() or None,
                        document_path=None,
                    )
                    if ok and movement_doc is not None and movement_id is not None:
                        doc_ref = _save_upload(
                            conn,
                            movement_doc,
                            entity_type="supply_movement",
                            entity_id=movement_id,
                            attachment_role="movement_document",
                        )
                        update_legacy_attachment_path(
                            conn,
                            table="supply_movements",
                            row_id=movement_id,
                            column="document_path",
                            value=doc_ref,
                        )
                    (st.success if ok else st.error)(msg)
                    if ok:
                        st.rerun()

    with tab_hist:
        st.markdown("### Histórico de movimentações")
        hist = query_df(
            conn,
            """
            SELECT sm.id, s.supply_name, sm.movement_type, sm.movement_date, sm.quantity, sm.unit,
                   u.full_name AS responsible_name, p.project_name, sm.purpose, sm.document_path, sm.created_at
            FROM supply_movements sm
            JOIN supplies s ON s.id = sm.supply_id
            LEFT JOIN users u ON u.id = sm.user_id
            LEFT JOIN projects p ON p.id = sm.project_id
            ORDER BY sm.movement_date DESC, sm.id DESC
            """,
        )
        if hist.empty:
            st.info("Ainda não há movimentações registradas.")
        else:
            st.dataframe(_display_df(hist), use_container_width=True, hide_index=True)
            st.markdown("#### Anexos cadastrados")
            shown_movements = 0
            for _, movement in hist.iterrows():
                attachment_rows = list_attachments(
                    conn,
                    entity_type="supply_movement",
                    entity_id=int(movement["id"]),
                    attachment_role="movement_document",
                )
                legacy_path = movement.get("document_path")
                if not attachment_rows and is_blank(legacy_path):
                    continue
                shown_movements += 1
                with st.expander(f"Movimentação #{int(movement['id'])} · {clean_value(movement.get('supply_name'))}", expanded=False):
                    render_attachment_list(
                        conn,
                        entity_type="supply_movement",
                        entity_id=int(movement["id"]),
                        attachment_role="movement_document",
                        legacy_path=legacy_path,
                        key_prefix=f"supply_movement_{int(movement['id'])}",
                        title="Documento/anexo",
                        empty_message="Nenhum documento/anexo cadastrado.",
                    )
            if shown_movements == 0:
                st.caption("Nenhum anexo cadastrado.")
            st.download_button(
                "Baixar histórico em CSV",
                data=_display_df(hist).to_csv(index=False).encode("utf-8-sig"),
                file_name="labcim_insumos_movimentacoes.csv",
                mime="text/csv",
            )


def page_manutencao(conn):
    hero()
    st.subheader("Manutenção e suporte")
    st.caption("Controle preventivo/calibração e abertura de tickets corretivos. Esta etapa ainda não envia notificações automaticamente; os campos já ficam preparados para essa integração.")
    equipment, users, _, _ = load_reference_data(conn)
    if equipment.empty:
        st.warning("Cadastre/importe equipamentos antes de registrar manutenções.")
        return

    tab_prev, tab_corr, tab_dash = st.tabs([
        "Preventiva e calibração",
        "Corretiva e suporte",
        "Indicadores e histórico",
    ])

    with tab_prev:
        st.markdown("### Manutenção preventiva e calibração")
        st.write("Registro de atividades planejadas, periódicas e obrigatórias: preventiva, calibração interna/externa e inspeções.")

        with st.container(border=True):
            c1, c2, c3 = st.columns([1.2, 1, 1])
            with c1:
                eq_label = st.selectbox("Equipamento", _equipment_options(equipment), key="prev_eq")
                equipment_id = _equipment_id_from_label(equipment, eq_label)
                selected = equipment[equipment["id"] == equipment_id].iloc[0]
                st.info(f"**Local:** {clean_value(selected.get('location'))}  \n**Responsável:** {clean_value(selected.get('responsible_name'))}")
                activity_type = st.selectbox(
                    "Tipo da atividade",
                    ["Preventiva", "Calibração interna", "Calibração externa", "Inspeção periódica"],
                    key="prev_activity_type",
                )
                status = st.selectbox("Status", ["pendente", "realizado", "reprovado", "reagendado"], key="prev_status")
            with c2:
                description = st.text_area(
                    "Descrição da atividade",
                    placeholder="Ex.: troca de filtros, lubrificação, verificação de alinhamento, calibração de sensores...",
                    key="prev_desc",
                )
                periodicity = st.selectbox("Periodicidade", ["mensal", "trimestral", "semestral", "anual", "por horas de uso", "sob demanda"], key="prev_periodicity")
                planned_date = st.date_input("Data inicial prevista", value=date.today(), key="prev_planned")
                planned_end_date = st.date_input("Data final prevista", value=date.today(), key="prev_planned_end")
                performed_date = st.date_input("Data realizada", value=None, key="prev_done")
                execution_time = st.text_input("Tempo de execução", placeholder="Ex.: 2 h, 1 dia, 30 min", key="prev_execution_time")
            with c3:
                internal_responsible = st.text_input("Responsável interno", value=clean_input(selected.get("responsible_name")), key="prev_internal_responsible")
                external_supplier = st.text_input("Fornecedor externo", placeholder="Se houver", key="prev_external_supplier")
                supplier_contact = st.text_input("Contato do fornecedor", placeholder="Telefone/e-mail", key="prev_supplier_contact")
                service_order = st.text_input("OS / protocolo externo", key="prev_service_order")
                next_date = st.date_input("Próxima data", value=None, key="prev_next")

            c4, c5 = st.columns(2)
            with c4:
                checklist = st.file_uploader("Checklist anexado (PDF/imagem/formulário)", type=["pdf", "png", "jpg", "jpeg"], key="prev_check")
            with c5:
                certificate = st.file_uploader("Certificado de calibração", type=["pdf", "png", "jpg", "jpeg"], key="prev_cert")

            observations = st.text_area("Observações", key="prev_obs")
            blocks_booking = st.checkbox(
                "Bloquear novas reservas neste período",
                value=True,
                key="prev_blocks_booking",
                help="Use para manutenção, calibração ou inspeção que impeça uso do equipamento. Desmarque quando for apenas registro documental.",
            )
            st.markdown("#### Notificações futuras")
            n1, n2, n3, n4 = st.columns(4)
            notify_internal = n1.checkbox("Responsável interno", value=True, key="prev_notify_internal")
            notify_manager = n2.checkbox("Gestor do laboratório", value=True, key="prev_notify_manager")
            notify_supplier = n3.checkbox("Fornecedor", value=False, key="prev_notify_supplier")
            notify_users = n4.checkbox("Usuários do equipamento", value=False, key="prev_notify_users")

            if st.button("Registrar preventiva/calibração", type="primary"):
                if not description.strip():
                    st.error("Informe a descrição da atividade.")
                elif planned_end_date and planned_date and planned_end_date < planned_date:
                    st.error("A data final prevista não pode ser anterior à data inicial.")
                elif not _ensure_storage_ready_for_upload(checklist, certificate):
                    pass
                else:
                    preventive_id = create_preventive_activity(
                        conn,
                        equipment_id=equipment_id,
                        activity_type=activity_type,
                        description=description.strip(),
                        periodicity=periodicity,
                        planned_date=planned_date.isoformat() if planned_date else None,
                        planned_end_date=planned_end_date.isoformat() if planned_end_date else None,
                        performed_date=performed_date.isoformat() if performed_date else None,
                        execution_time=execution_time.strip() or None,
                        checklist_path=None,
                        internal_responsible=internal_responsible.strip() or None,
                        external_supplier=external_supplier.strip() or None,
                        supplier_contact=supplier_contact.strip() or None,
                        service_order=service_order.strip() or None,
                        status=status,
                        certificate_path=None,
                        observations=observations.strip() or None,
                        next_date=next_date.isoformat() if next_date else None,
                        blocks_booking=int(blocks_booking),
                        notify_internal=int(notify_internal),
                        notify_manager=int(notify_manager),
                        notify_supplier=int(notify_supplier),
                        notify_users=int(notify_users),
                    )
                    if checklist is not None:
                        checklist_ref = _save_upload(
                            conn,
                            checklist,
                            entity_type="maintenance_preventive",
                            entity_id=preventive_id,
                            attachment_role="preventive_checklist",
                        )
                        update_legacy_attachment_path(
                            conn,
                            table="maintenance_preventive",
                            row_id=preventive_id,
                            column="checklist_path",
                            value=checklist_ref,
                        )
                    if certificate is not None:
                        cert_ref = _save_upload(
                            conn,
                            certificate,
                            entity_type="maintenance_preventive",
                            entity_id=preventive_id,
                            attachment_role="preventive_certificate",
                        )
                        update_legacy_attachment_path(
                            conn,
                            table="maintenance_preventive",
                            row_id=preventive_id,
                            column="certificate_path",
                            value=cert_ref,
                        )
                    if blocks_booking and status not in {"realizado", "cancelado"}:
                        sent, total = notify_equipment_maintenance(
                            conn,
                            equipment_id=equipment_id,
                            title="manutenção/calibração agendada",
                            message=(
                                f"Foi registrada uma atividade bloqueante no equipamento.\n"
                                f"Tipo: {activity_type}\n"
                                f"Período: {planned_date.strftime('%d/%m/%Y')} a {planned_end_date.strftime('%d/%m/%Y')}\n"
                                f"Descrição: {description.strip()}"
                            ),
                            related_table="maintenance_preventive",
                            related_id=preventive_id,
                            include_future_users=bool(notify_users),
                        )
                        if total:
                            st.info(f"Notificação de manutenção registrada para {total} destinatário(s). Enviadas: {sent}.")
                    st.success("Atividade preventiva/calibração registrada.")
                    st.rerun()

        st.markdown("### Próximas preventivas/calibrações")
        prev_df = query_df(
            conn,
            """
            SELECT mp.id, e.equipment_code, e.equipment_name, e.location, mp.activity_type,
                   mp.periodicity, mp.planned_date, mp.performed_date, mp.status,
                   mp.planned_end_date, mp.blocks_booking,
                   mp.internal_responsible, mp.external_supplier, mp.service_order, mp.next_date,
                   mp.observations, mp.checklist_path, mp.certificate_path
            FROM maintenance_preventive mp
            JOIN equipment e ON e.id = mp.equipment_id
            ORDER BY COALESCE(mp.planned_date, mp.created_at) DESC
            """,
        )
        if prev_df.empty:
            st.info("Ainda não há registros preventivos/calibrações.")
        else:
            st.dataframe(prev_df, use_container_width=True, hide_index=True)
            st.markdown("#### Anexos cadastrados")
            shown_preventive = 0
            for _, preventive in prev_df.iterrows():
                checklist_rows = list_attachments(
                    conn,
                    entity_type="maintenance_preventive",
                    entity_id=int(preventive["id"]),
                    attachment_role="preventive_checklist",
                )
                certificate_rows = list_attachments(
                    conn,
                    entity_type="maintenance_preventive",
                    entity_id=int(preventive["id"]),
                    attachment_role="preventive_certificate",
                )
                has_checklist = checklist_rows or not is_blank(preventive.get("checklist_path"))
                has_certificate = certificate_rows or not is_blank(preventive.get("certificate_path"))
                if not has_checklist and not has_certificate:
                    continue
                shown_preventive += 1
                title = f"Preventiva #{int(preventive['id'])} · {clean_value(preventive.get('equipment_code'))} · {clean_value(preventive.get('activity_type'))}"
                with st.expander(title, expanded=False):
                    p1, p2 = st.columns(2)
                    with p1:
                        render_attachment_list(
                            conn,
                            entity_type="maintenance_preventive",
                            entity_id=int(preventive["id"]),
                            attachment_role="preventive_checklist",
                            legacy_path=preventive.get("checklist_path"),
                            key_prefix=f"preventive_{int(preventive['id'])}_checklist",
                            title="Checklist",
                            empty_message="Nenhum checklist cadastrado.",
                        )
                    with p2:
                        render_attachment_list(
                            conn,
                            entity_type="maintenance_preventive",
                            entity_id=int(preventive["id"]),
                            attachment_role="preventive_certificate",
                            legacy_path=preventive.get("certificate_path"),
                            key_prefix=f"preventive_{int(preventive['id'])}_certificate",
                            title="Certificado",
                            empty_message="Nenhum certificado cadastrado.",
                        )
            if shown_preventive == 0:
                st.caption("Nenhum anexo cadastrado.")

    with tab_corr:
        st.markdown("### Manutenção corretiva e suporte")
        st.write("Tickets abertos por usuários quando há falha, quebra, ruído, anomalia operacional ou necessidade de suporte.")

        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1:
                eq_label = st.selectbox("Equipamento", _equipment_options(equipment), key="corr_eq")
                equipment_id = _equipment_id_from_label(equipment, eq_label)
                selected = equipment[equipment["id"] == equipment_id].iloc[0]
                st.info(f"**Local:** {clean_value(selected.get('location'))}  \n**Patrimônio/código:** {clean_value(selected.get('equipment_code'))}")
                reporter_id = None
                if not users.empty:
                    user_labels = ["Não informado"] + users.apply(lambda r: f"{clean_value(r.get('full_name'))} ({clean_value(r.get('role'), 'member')})", axis=1).tolist()
                    reporter_label = st.selectbox("Usuário que abriu o ticket", user_labels, key="corr_reporter")
                    if reporter_label != "Não informado":
                        reporter_id = int(users.iloc[user_labels.index(reporter_label) - 1]["id"])
                title = st.text_input("Título do ticket", placeholder="Ex.: Microscópio não liga", key="corr_title")
                occurrence_date = st.date_input("Data da ocorrência", value=date.today(), key="corr_occurrence_date")
                occurrence_time = st.time_input("Hora da ocorrência", value=datetime.now().time().replace(second=0, microsecond=0), step=timedelta(minutes=15), key="corr_occurrence_time")
            with c2:
                description = st.text_area("Descrição detalhada", placeholder="Explique a falha, mensagem de erro, contexto de uso, sintomas observados...", key="corr_desc")
                impact = st.selectbox("Impacto", ["crítico", "moderado", "baixo"], index=2, key="corr_impact")
                priority = st.selectbox("Prioridade sugerida", ["alta", "média", "baixa"], index=2, key="corr_priority")
                attachment = st.file_uploader("Anexos (foto, vídeo, print)", type=["png", "jpg", "jpeg", "pdf", "mp4", "mov"], key="corr_attach")

            st.markdown("#### Diagnóstico e ações")
            d1, d2, d3 = st.columns(3)
            with d1:
                assigned_to = st.text_input("Responsável pelo atendimento", value=clean_input(selected.get("responsible_name")), key="corr_assigned_to")
                operator_trained = st.selectbox("Operador era treinado?", ["não informado", "sim", "não"], key="corr_operator_trained")
                external_supplier_needed = st.checkbox("Necessita fornecedor externo", value=False, key="corr_external_supplier_needed")
            with d2:
                initial_diagnosis = st.text_area("Diagnóstico inicial", key="diag")
                probable_cause = st.text_area("Causa provável", key="cause")
            with d3:
                corrective_action = st.text_area("Ação corretiva realizada", key="action")
                replaced_parts = st.text_input("Peças substituídas", key="corr_replaced_parts")
                costs = st.number_input("Custos envolvidos (R$)", min_value=0.0, value=0.0, step=50.0, key="corr_costs")
                downtime_hours = st.number_input("Downtime (h)", min_value=0.0, value=0.0, step=0.5, key="corr_downtime_hours")

            status = st.selectbox("Status do ticket", ["aberto", "em análise", "aguardando peça", "enviado para fornecedor", "concluído", "cancelado"], key="corr_status")
            conclusion_date = st.date_input("Data de conclusão", value=None, key="corr_conclusion")

            st.markdown("#### Notificações futuras")
            n1, n2, n3, n4 = st.columns(4)
            notify_technical = n1.checkbox("Responsável técnico", value=True, key="corr_notify_technical")
            notify_manager = n2.checkbox("Gestor do laboratório", value=True, key="corr_notify_manager")
            notify_supplier = n3.checkbox("Fornecedor", value=False, key="corr_notify_supplier")
            notify_reporter = n4.checkbox("Usuário que abriu", value=True, key="corr_notify_reporter")

            if st.button("Abrir ticket corretivo", type="primary"):
                if not title.strip() or not description.strip():
                    st.error("Informe o título e a descrição do ticket.")
                elif not _ensure_storage_ready_for_upload(attachment):
                    pass
                else:
                    occurrence_dt = datetime.combine(occurrence_date, occurrence_time).isoformat(timespec="minutes")
                    ticket_id = create_corrective_ticket(
                        conn,
                        equipment_id=equipment_id,
                        reporter_id=reporter_id,
                        title=title.strip(),
                        description=description.strip(),
                        occurrence_datetime=occurrence_dt,
                        impact=impact,
                        priority=priority,
                        attachment_path=None,
                        assigned_to=assigned_to.strip() or None,
                        initial_diagnosis=initial_diagnosis.strip() or None,
                        probable_cause=probable_cause.strip() or None,
                        operator_trained=operator_trained,
                        external_supplier_needed=int(external_supplier_needed),
                        corrective_action=corrective_action.strip() or None,
                        replaced_parts=replaced_parts.strip() or None,
                        costs=float(costs) if costs else None,
                        downtime_hours=float(downtime_hours) if downtime_hours else None,
                        conclusion_date=conclusion_date.isoformat() if conclusion_date else None,
                        status=status,
                        notify_technical=int(notify_technical),
                        notify_manager=int(notify_manager),
                        notify_supplier=int(notify_supplier),
                        notify_reporter=int(notify_reporter),
                    )
                    if attachment is not None:
                        attachment_ref = _save_upload(
                            conn,
                            attachment,
                            entity_type="maintenance_corrective",
                            entity_id=ticket_id,
                            attachment_role="corrective_attachment",
                        )
                        update_legacy_attachment_path(
                            conn,
                            table="maintenance_corrective",
                            row_id=ticket_id,
                            column="attachment_path",
                            value=attachment_ref,
                        )
                    st.success("Ticket corretivo registrado.")
                    st.rerun()

        st.markdown("### Tickets corretivos")
        corr_df = query_df(
            conn,
            """
            SELECT mc.id, e.equipment_code, e.equipment_name, e.location,
                   u.full_name AS reporter, mc.title, mc.impact, mc.priority,
                   mc.status, mc.occurrence_datetime, mc.assigned_to,
                   mc.downtime_hours, mc.costs, mc.created_at, mc.attachment_path
            FROM maintenance_corrective mc
            JOIN equipment e ON e.id = mc.equipment_id
            LEFT JOIN users u ON u.id = mc.reporter_id
            ORDER BY CASE mc.status WHEN 'aberto' THEN 0 WHEN 'em análise' THEN 1 WHEN 'aguardando peça' THEN 2 ELSE 3 END,
                     mc.created_at DESC
            """,
        )
        if corr_df.empty:
            st.info("Nenhum ticket corretivo registrado.")
        else:
            st.dataframe(corr_df, use_container_width=True, hide_index=True)
            st.markdown("#### Anexos cadastrados")
            shown_corrective = 0
            for _, ticket in corr_df.iterrows():
                attachment_rows = list_attachments(
                    conn,
                    entity_type="maintenance_corrective",
                    entity_id=int(ticket["id"]),
                    attachment_role="corrective_attachment",
                )
                legacy_path = ticket.get("attachment_path")
                if not attachment_rows and is_blank(legacy_path):
                    continue
                shown_corrective += 1
                title = f"Ticket #{int(ticket['id'])} · {clean_value(ticket.get('equipment_code'))} · {clean_value(ticket.get('title'))}"
                with st.expander(title, expanded=False):
                    render_attachment_list(
                        conn,
                        entity_type="maintenance_corrective",
                        entity_id=int(ticket["id"]),
                        attachment_role="corrective_attachment",
                        legacy_path=legacy_path,
                        key_prefix=f"corrective_{int(ticket['id'])}",
                        title="Anexo",
                        empty_message="Nenhum anexo cadastrado.",
                    )
            if shown_corrective == 0:
                st.caption("Nenhum anexo cadastrado.")
            active_ids = corr_df[~corr_df["status"].isin(["concluído", "cancelado"])] ["id"].tolist()
            if active_ids:
                c1, c2 = st.columns([1, 1])
                with c1:
                    ticket_id = st.selectbox("Atualizar status do ticket", active_ids, format_func=lambda x: f"Ticket #{x}", key="corr_update_ticket_id")
                with c2:
                    new_status = st.selectbox("Novo status", ["em análise", "aguardando peça", "enviado para fornecedor", "concluído", "cancelado"], key="corr_update_new_status")
                if st.button("Atualizar status"):
                    update_corrective_status(conn, int(ticket_id), new_status)
                    st.rerun()

    with tab_dash:
        st.markdown("### Indicadores de manutenção")
        corr = query_df(conn, "SELECT * FROM maintenance_corrective")
        prev = query_df(conn, "SELECT * FROM maintenance_preventive")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Preventivas/calibrações", len(prev))
        k2.metric("Tickets corretivos", len(corr))
        if not corr.empty and "downtime_hours" in corr.columns:
            k3.metric("Downtime total (h)", f"{corr['downtime_hours'].fillna(0).sum():.1f}")
            k4.metric("MTTR preliminar (h)", f"{corr['downtime_hours'].fillna(0).mean():.1f}")
        else:
            k3.metric("Downtime total (h)", "0")
            k4.metric("MTTR preliminar (h)", "0")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Tickets por status")
            if not corr.empty:
                status_df = corr.groupby("status", dropna=False).size().reset_index(name="total")
                fig = px.bar(status_df, x="status", y="total", color="status", color_discrete_sequence=[LAB_BLUE, LAB_CYAN, "#6BAED6", "#9ECAE1"])
                fig.update_layout(height=330, margin=dict(l=20, r=20, t=20, b=20), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem tickets corretivos para calcular indicadores.")
        with c2:
            st.markdown("#### Preventivas por status")
            if not prev.empty:
                status_df = prev.groupby("status", dropna=False).size().reset_index(name="total")
                fig = px.bar(status_df, x="status", y="total", color="status", color_discrete_sequence=[LAB_BLUE, LAB_CYAN, "#6BAED6", "#9ECAE1"])
                fig.update_layout(height=330, margin=dict(l=20, r=20, t=20, b=20), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem preventivas/calibrações para calcular indicadores.")


def _semester_bounds(year: int, semester: int) -> tuple[date, date]:
    if semester == 1:
        return date(year, 1, 1), date(year, 6, 30)
    return date(year, 7, 1), date(year, 12, 31)


def _previous_semester_bounds(today: date) -> tuple[date, date]:
    if today.month <= 6:
        return _semester_bounds(today.year - 1, 2)
    return _semester_bounds(today.year, 1)


def _period_label(start_date: date, end_date: date) -> str:
    return f"{start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"


def _filtered_reports_data(conn, start_date: date, end_date: date) -> dict[str, pd.DataFrame]:
    bookings = query_df(
        conn,
        """
        SELECT b.id, e.equipment_code, e.equipment_name, e.lab_unit, e.location,
               u.full_name AS solicitante, u.department AS departamento,
               p.project_name, p.funding_source,
               op.full_name AS operador, perf.full_name AS executante,
               COALESCE(perf.full_name, op.full_name, u.full_name) AS responsavel_execucao,
               b.start_datetime, b.end_datetime, b.sample_count, b.purpose, b.status,
               b.created_at, b.updated_at
        FROM bookings b
        JOIN equipment e ON e.id=b.equipment_id
        JOIN users u ON u.id=b.user_id
        LEFT JOIN users op ON op.id=b.operator_id
        LEFT JOIN users perf ON perf.id=b.performed_by_id
        LEFT JOIN projects p ON p.id=b.project_id
        WHERE SUBSTR(b.start_datetime, 1, 10) BETWEEN ? AND ?
        ORDER BY b.start_datetime
        """,
        [start_date.isoformat(), end_date.isoformat()],
    )

    preventive = query_df(
        conn,
        """
        SELECT mp.id, e.equipment_code, e.equipment_name, e.lab_unit, e.location,
               mp.activity_type, mp.description, mp.periodicity, mp.planned_date,
               mp.planned_end_date, mp.performed_date, mp.execution_time,
               mp.internal_responsible, mp.external_supplier, mp.service_order,
               mp.status, mp.next_date, mp.blocks_booking, mp.observations,
               mp.created_at, mp.updated_at
        FROM maintenance_preventive mp
        JOIN equipment e ON e.id=mp.equipment_id
        WHERE SUBSTR(COALESCE(mp.performed_date, mp.planned_date, mp.created_at), 1, 10) BETWEEN ? AND ?
        ORDER BY COALESCE(mp.performed_date, mp.planned_date, mp.created_at)
        """,
        [start_date.isoformat(), end_date.isoformat()],
    )

    corrective = query_df(
        conn,
        """
        SELECT mc.id, e.equipment_code, e.equipment_name, e.lab_unit, e.location,
               u.full_name AS reporter, mc.title, mc.description, mc.occurrence_datetime,
               mc.impact, mc.priority, mc.assigned_to, mc.initial_diagnosis,
               mc.probable_cause, mc.operator_trained, mc.external_supplier_needed,
               mc.corrective_action, mc.replaced_parts, mc.costs, mc.downtime_hours,
               mc.conclusion_date, mc.status, mc.created_at, mc.updated_at
        FROM maintenance_corrective mc
        JOIN equipment e ON e.id=mc.equipment_id
        LEFT JOIN users u ON u.id=mc.reporter_id
        WHERE SUBSTR(COALESCE(mc.conclusion_date, mc.occurrence_datetime, mc.created_at), 1, 10) BETWEEN ? AND ?
        ORDER BY COALESCE(mc.conclusion_date, mc.occurrence_datetime, mc.created_at)
        """,
        [start_date.isoformat(), end_date.isoformat()],
    )

    supply_movements = query_df(
        conn,
        """
        SELECT sm.id, s.supply_name, s.commercial_name, s.manufacturer, s.category,
               s.physical_state, sm.movement_type, sm.movement_date, sm.quantity,
               COALESCE(sm.unit, s.unit) AS unit, u.full_name AS responsavel,
               p.project_name, sm.purpose, sm.document_path, sm.created_at
        FROM supply_movements sm
        JOIN supplies s ON s.id=sm.supply_id
        LEFT JOIN users u ON u.id=sm.user_id
        LEFT JOIN projects p ON p.id=sm.project_id
        WHERE SUBSTR(sm.movement_date, 1, 10) BETWEEN ? AND ?
        ORDER BY sm.movement_date
        """,
        [start_date.isoformat(), end_date.isoformat()],
    )

    supplies = query_df(
        conn,
        """
        SELECT supply_name, commercial_name, manufacturer, category, physical_state,
               application_function, addition_mode, current_quantity, minimum_quantity,
               unit, lot, expiration_date, location, responsible_name, active,
               safety_doc_path, technical_doc_path, notes
        FROM supplies
        ORDER BY active DESC, supply_name
        """,
    )
    if not supplies.empty:
        supplies["alerta"] = supplies.apply(_supply_alert_status, axis=1)

    equipment = query_df(
        conn,
        """
        SELECT equipment_code, equipment_name, lab_unit, location, operational_status,
               unavailable_functions, max_sample_capacity, capacity_unit,
               technical_manager, responsible_name, pop_title, pop_version, active
        FROM equipment
        ORDER BY active DESC, equipment_code
        """,
    )

    return {
        "bookings": bookings,
        "preventive": preventive,
        "corrective": corrective,
        "supply_movements": supply_movements,
        "supplies": supplies,
        "equipment": equipment,
    }


def _with_booking_duration(bookings: pd.DataFrame) -> pd.DataFrame:
    out = bookings.copy()
    if out.empty:
        return out
    start = pd.to_datetime(out["start_datetime"], errors="coerce")
    end = pd.to_datetime(out["end_datetime"], errors="coerce")
    out["duracao_h"] = ((end - start).dt.total_seconds() / 3600).fillna(0).clip(lower=0)
    out["mes"] = start.dt.to_period("M").astype(str)
    out["status_legivel"] = out["status"].map(STATUS_LABELS).fillna(out["status"])
    return out


def _report_summary(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    bookings = _with_booking_duration(data["bookings"])
    corrective = data["corrective"]
    preventive = data["preventive"]
    supply_movements = data["supply_movements"]
    supplies = data["supplies"]

    total_bookings = len(bookings)
    completed = int((bookings["status"] == "done").sum()) if not bookings.empty else 0
    cancelled = int((bookings["status"] == "cancelled").sum()) if not bookings.empty else 0
    total_samples = int(bookings["sample_count"].fillna(0).sum()) if not bookings.empty and "sample_count" in bookings else 0
    total_hours = float(bookings["duracao_h"].sum()) if not bookings.empty else 0.0
    unique_equipment = int(bookings["equipment_code"].nunique()) if not bookings.empty else 0
    unique_users = int(bookings["solicitante"].nunique()) if not bookings.empty else 0
    downtime = float(corrective["downtime_hours"].fillna(0).sum()) if not corrective.empty and "downtime_hours" in corrective else 0.0
    low_stock = int(supplies["alerta"].isin(["Estoque baixo", "Vencido", "Vence em até 60 dias"]).sum()) if not supplies.empty else 0
    outputs = supply_movements[supply_movements["movement_type"].isin(["saída", "descarte", "ajuste negativo"])] if not supply_movements.empty else supply_movements

    rows = [
        ("Reservas registradas", total_bookings),
        ("Reservas concluídas", completed),
        ("Reservas canceladas", cancelled),
        ("Amostras previstas/registradas", total_samples),
        ("Horas reservadas", round(total_hours, 1)),
        ("Equipamentos utilizados", unique_equipment),
        ("Usuários solicitantes", unique_users),
        ("Preventivas/calibrações", len(preventive)),
        ("Tickets corretivos", len(corrective)),
        ("Downtime corretivo (h)", round(downtime, 1)),
        ("Movimentações de insumos", len(supply_movements)),
        ("Saídas/consumo de insumos", len(outputs)),
        ("Insumos em alerta", low_stock),
    ]
    return pd.DataFrame(rows, columns=["Indicador", "Valor"])


def _top_counts(df: pd.DataFrame, group_col: str, value_col: str = "total", limit: int = 10) -> pd.DataFrame:
    if df.empty or group_col not in df.columns:
        return pd.DataFrame(columns=[group_col, value_col])
    return (
        df[group_col]
        .fillna("Não informado")
        .replace("", "Não informado")
        .value_counts()
        .head(limit)
        .reset_index()
        .rename(columns={group_col: value_col, "index": group_col})
    )


def _reports_excel_bytes(period_text: str, data: dict[str, pd.DataFrame]) -> bytes:
    output = BytesIO()
    summary = _report_summary(data)
    bookings = _with_booking_duration(data["bookings"])
    sheets = {
        "Resumo": summary,
        "Reservas": _display_df(bookings),
        "Preventivas": _display_df(data["preventive"]),
        "Corretivas": _display_df(data["corrective"]),
        "Movimentos insumos": _display_df(data["supply_movements"]),
        "Estoque atual": _display_df(data["supplies"]),
        "Equipamentos": _display_df(data["equipment"]),
    }
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame({"Relatório": ["LabCim Manager"], "Período": [period_text], "Gerado em": [datetime.now().strftime("%d/%m/%Y %H:%M")]}).to_excel(
            writer,
            sheet_name="Capa",
            index=False,
        )
        for sheet_name, df in sheets.items():
            safe_name = sheet_name[:31]
            df.to_excel(writer, sheet_name=safe_name, index=False)
            worksheet = writer.sheets[safe_name]
            for column_cells in worksheet.columns:
                max_len = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
                worksheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_len + 2, 12), 55)
    return output.getvalue()


def _download_table_button(df: pd.DataFrame, file_name: str, label: str) -> None:
    if df.empty:
        st.caption("Sem dados para exportar nesta tabela.")
        return
    st.download_button(
        label,
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name=file_name,
        mime="text/csv",
        key=f"download_{file_name}",
    )


def page_relatorios(conn):
    hero()
    st.subheader("Relatórios semestrais e anuais")
    st.caption("Consolide uso de equipamentos, responsáveis, manutenções e insumos para acompanhamento interno, reuniões e registros da qualidade.")

    today = date.today()
    current_year = today.year
    min_year = 2024
    max_year = current_year + 1

    with st.container(border=True):
        c1, c2, c3 = st.columns([1.4, 1, 1])
        with c1:
            period_mode = st.selectbox(
                "Tipo de relatório",
                ["Semestre atual", "Semestre anterior", "Ano atual", "Ano anterior", "Semestre específico", "Ano específico", "Intervalo personalizado"],
                key="report_period_mode",
            )
        with c2:
            selected_year = st.number_input("Ano", min_value=min_year, max_value=max_year, value=current_year, step=1, key="report_year")
        with c3:
            selected_semester = st.selectbox("Semestre", ["1º semestre", "2º semestre"], key="report_semester")

        if period_mode == "Semestre atual":
            start_date, end_date = _semester_bounds(today.year, 1 if today.month <= 6 else 2)
        elif period_mode == "Semestre anterior":
            start_date, end_date = _previous_semester_bounds(today)
        elif period_mode == "Ano atual":
            start_date, end_date = date(today.year, 1, 1), date(today.year, 12, 31)
        elif period_mode == "Ano anterior":
            start_date, end_date = date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)
        elif period_mode == "Semestre específico":
            start_date, end_date = _semester_bounds(int(selected_year), 1 if selected_semester.startswith("1") else 2)
        elif period_mode == "Ano específico":
            start_date, end_date = date(int(selected_year), 1, 1), date(int(selected_year), 12, 31)
        else:
            d1, d2 = st.columns(2)
            start_date = d1.date_input("Data inicial", value=date(today.year, 1, 1), key="report_custom_start")
            end_date = d2.date_input("Data final", value=today, key="report_custom_end")

        if start_date > end_date:
            st.error("A data inicial não pode ser posterior à data final.")
            return

    period_text = _period_label(start_date, end_date)
    data = _filtered_reports_data(conn, start_date, end_date)
    bookings = _with_booking_duration(data["bookings"])
    preventive = data["preventive"]
    corrective = data["corrective"]
    supply_movements = data["supply_movements"]
    supplies = data["supplies"]
    summary = _report_summary(data)

    st.markdown(f"#### Período analisado: {period_text}")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Reservas", len(bookings))
    k2.metric("Concluídas", int((bookings["status"] == "done").sum()) if not bookings.empty else 0)
    k3.metric("Amostras", int(bookings["sample_count"].fillna(0).sum()) if not bookings.empty and "sample_count" in bookings else 0)
    k4.metric("Manutenções", len(preventive) + len(corrective))
    k5.metric("Mov. insumos", len(supply_movements))

    excel_bytes = _reports_excel_bytes(period_text, data)
    st.download_button(
        "📥 Baixar relatório completo em Excel",
        data=excel_bytes,
        file_name=f"LabCim_Relatorio_{start_date.isoformat()}_{end_date.isoformat()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_full_report_xlsx",
        type="primary",
    )

    tab_overview, tab_bookings, tab_maintenance, tab_supplies, tab_tables = st.tabs(
        ["Resumo executivo", "Reservas e uso", "Manutenção", "Insumos", "Tabelas auditáveis"]
    )

    with tab_overview:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("### Indicadores consolidados")
            st.dataframe(summary, use_container_width=True, hide_index=True)
        with c2:
            st.markdown("### Leitura rápida")
            if bookings.empty and preventive.empty and corrective.empty and supply_movements.empty:
                st.info("Não há registros operacionais no período selecionado.")
            else:
                top_equipment = clean_value(bookings["equipment_name"].value_counts().idxmax()) if not bookings.empty else "-"
                top_user = clean_value(bookings["responsavel_execucao"].value_counts().idxmax()) if not bookings.empty else "-"
                st.markdown(
                    f"""
                    <div class="soft-card">
                    <b>Equipamento mais demandado:</b> {top_equipment}<br>
                    <b>Responsável/executante mais frequente:</b> {top_user}<br>
                    <b>Registros de manutenção:</b> {len(preventive) + len(corrective)}<br>
                    <b>Insumos em alerta:</b> {int(supplies["alerta"].isin(["Estoque baixo", "Vencido", "Vence em até 60 dias"]).sum()) if not supplies.empty else 0}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        if not bookings.empty:
            st.markdown("### Reservas por mês")
            monthly = bookings.groupby("mes", dropna=False).size().reset_index(name="Reservas")
            fig = px.bar(monthly, x="mes", y="Reservas", color_discrete_sequence=[LAB_BLUE])
            fig.update_layout(height=320, margin=dict(l=20, r=20, t=20, b=20), xaxis_title="Mês", yaxis_title="Reservas")
            st.plotly_chart(fig, use_container_width=True)

    with tab_bookings:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Equipamentos mais utilizados")
            if not bookings.empty:
                top_eq = bookings.groupby(["equipment_code", "equipment_name"], dropna=False).size().reset_index(name="reservas").sort_values("reservas", ascending=False).head(10)
                top_eq["equipamento"] = top_eq["equipment_code"].astype(str) + " — " + top_eq["equipment_name"].astype(str)
                fig = px.bar(top_eq, y="equipamento", x="reservas", orientation="h", color_discrete_sequence=[LAB_BLUE])
                fig.update_layout(height=390, margin=dict(l=20, r=20, t=20, b=20), yaxis_title="", xaxis_title="Reservas")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem reservas no período.")
        with c2:
            st.markdown("### Reservas por status")
            if not bookings.empty:
                status_df = bookings.groupby("status_legivel", dropna=False).size().reset_index(name="reservas")
                fig = px.bar(status_df, x="status_legivel", y="reservas", color="status_legivel", color_discrete_sequence=[LAB_BLUE, LAB_CYAN, "#94A3B8", "#F97316"])
                fig.update_layout(height=390, margin=dict(l=20, r=20, t=20, b=20), showlegend=False, xaxis_title="Status", yaxis_title="Reservas")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem reservas no período.")

        st.markdown("### Responsáveis/executantes")
        if not bookings.empty:
            performers = bookings.groupby("responsavel_execucao", dropna=False).agg(
                reservas=("id", "count"),
                amostras=("sample_count", "sum"),
                horas=("duracao_h", "sum"),
            ).reset_index().sort_values("reservas", ascending=False)
            performers["horas"] = performers["horas"].round(1)
            st.dataframe(performers.rename(columns={"responsavel_execucao": "Responsável/executante", "reservas": "Reservas", "amostras": "Amostras", "horas": "Horas"}), use_container_width=True, hide_index=True)
        else:
            st.info("Sem executantes para listar.")

    with tab_maintenance:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Preventivas/calibrações")
            if preventive.empty:
                st.info("Sem preventivas/calibrações no período.")
            else:
                prev_status = preventive.groupby("status", dropna=False).size().reset_index(name="total")
                fig = px.bar(prev_status, x="status", y="total", color="status", color_discrete_sequence=[LAB_BLUE, LAB_CYAN, "#94A3B8"])
                fig.update_layout(height=330, margin=dict(l=20, r=20, t=20, b=20), showlegend=False, xaxis_title="Status", yaxis_title="Total")
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown("### Corretivas")
            if corrective.empty:
                st.info("Sem tickets corretivos no período.")
            else:
                corr_status = corrective.groupby("status", dropna=False).agg(
                    tickets=("id", "count"),
                    downtime_h=("downtime_hours", "sum"),
                    custos=("costs", "sum"),
                ).reset_index()
                corr_status["downtime_h"] = corr_status["downtime_h"].fillna(0).round(1)
                corr_status["custos"] = corr_status["custos"].fillna(0).round(2)
                st.dataframe(corr_status.rename(columns={"status": "Status", "tickets": "Tickets", "downtime_h": "Downtime (h)", "custos": "Custos (R$)"}), use_container_width=True, hide_index=True)

        if not corrective.empty:
            st.markdown("### Equipamentos com tickets corretivos")
            corr_eq = corrective.groupby(["equipment_code", "equipment_name"], dropna=False).agg(
                tickets=("id", "count"),
                downtime_h=("downtime_hours", "sum"),
            ).reset_index().sort_values("tickets", ascending=False)
            corr_eq["downtime_h"] = corr_eq["downtime_h"].fillna(0).round(1)
            st.dataframe(corr_eq.rename(columns={"equipment_code": "Código", "equipment_name": "Equipamento", "tickets": "Tickets", "downtime_h": "Downtime (h)"}), use_container_width=True, hide_index=True)

    with tab_supplies:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Movimentações por tipo")
            if supply_movements.empty:
                st.info("Sem movimentações de insumos no período.")
            else:
                move_type = supply_movements.groupby("movement_type", dropna=False).size().reset_index(name="total")
                fig = px.bar(move_type, x="movement_type", y="total", color="movement_type", color_discrete_sequence=[LAB_BLUE, LAB_CYAN, "#F97316", "#94A3B8"])
                fig.update_layout(height=330, margin=dict(l=20, r=20, t=20, b=20), showlegend=False, xaxis_title="Tipo", yaxis_title="Movimentações")
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown("### Alertas de estoque")
            if supplies.empty:
                st.info("Nenhum insumo cadastrado.")
            else:
                alert_df = supplies[supplies["alerta"].isin(["Estoque baixo", "Vencido", "Vence em até 60 dias"])]
                if alert_df.empty:
                    st.success("Sem alertas críticos de estoque/validade no momento.")
                else:
                    st.dataframe(_display_df(alert_df[["alerta", "supply_name", "current_quantity", "unit", "minimum_quantity", "expiration_date", "location", "responsible_name"]]), use_container_width=True, hide_index=True)

        if not supply_movements.empty:
            st.markdown("### Consumo/saídas por insumo")
            consumed = supply_movements[supply_movements["movement_type"].isin(["saída", "descarte", "ajuste negativo"])].copy()
            if consumed.empty:
                st.info("Não houve saídas, descartes ou ajustes negativos no período.")
            else:
                consumed_summary = consumed.groupby(["supply_name", "unit"], dropna=False)["quantity"].sum().reset_index().sort_values("quantity", ascending=False)
                st.dataframe(consumed_summary.rename(columns={"supply_name": "Insumo", "unit": "Unidade", "quantity": "Quantidade"}), use_container_width=True, hide_index=True)

    with tab_tables:
        st.markdown("### Tabelas auditáveis")
        table_choice = st.selectbox(
            "Tabela",
            ["Reservas", "Preventivas/calibrações", "Corretivas", "Movimentações de insumos", "Estoque atual", "Equipamentos"],
            key="report_table_choice",
        )
        table_map = {
            "Reservas": bookings,
            "Preventivas/calibrações": preventive,
            "Corretivas": corrective,
            "Movimentações de insumos": supply_movements,
            "Estoque atual": supplies,
            "Equipamentos": data["equipment"],
        }
        selected_df = table_map[table_choice]
        if selected_df.empty:
            st.info("Sem registros para a tabela selecionada.")
        else:
            st.dataframe(_display_df(selected_df), use_container_width=True, hide_index=True)
            safe = re.sub(r"[^A-Za-z0-9_-]+", "_", table_choice.lower())
            _download_table_button(selected_df, f"LabCim_{safe}_{start_date.isoformat()}_{end_date.isoformat()}.csv", "Baixar esta tabela em CSV")


def _make_qr_png(url: str) -> bytes:
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def page_qrcodes(conn):
    hero()
    st.subheader("QR Codes físicos")
    st.caption("Gere QR Codes para fixar em equipamentos, embalagens, prateleiras ou armários. A ideia é reduzir atrito: escaneou, achou a ação certa.")
    equipment = query_df(conn, "SELECT * FROM equipment WHERE active=1 ORDER BY equipment_code")
    supplies = query_df(conn, "SELECT * FROM supplies WHERE active=1 ORDER BY supply_name")
    base_url = st.text_input("URL pública do aplicativo", value="https://labcim-manager.streamlit.app", key="qr_base_url")
    base_url = base_url.rstrip("/")

    tab_eq, tab_sup = st.tabs(["Equipamentos", "Insumos"])

    with tab_eq:
        st.markdown("### QR Codes por equipamento")
        if equipment.empty:
            st.info("Nenhum equipamento ativo encontrado.")
        else:
            eq = st.selectbox("Equipamento", equipment["equipment_code"].tolist(), key="qr_equipment")
            selected = equipment[equipment["equipment_code"] == eq].iloc[0]
            st.markdown(
                f"""
                <div class="soft-card">
                <b>{clean_value(selected.get('equipment_code'))} — {clean_value(selected.get('equipment_name'))}</b><br>
                Local: {clean_value(selected.get('location'))} · Responsável: {clean_value(selected.get('responsible_name'))}<br>
                POP: {clean_value(selected.get('pop_title'), 'não cadastrado')}
                </div>
                """,
                unsafe_allow_html=True,
            )

            cards = [
                ("Reservar / Ver agenda", "reserva", "Aponte a câmera para reservar ou consultar a agenda deste equipamento."),
                ("Reportar problema / Manutenção", "manutencao", "Aponte a câmera para abrir um ticket de suporte/manutenção."),
            ]
            if not is_blank(selected.get("pop_path")):
                cards.append(("Consultar POP / Documentação", "pop", "Aponte a câmera para consultar ou baixar o POP/documentação operacional."))

            cols = st.columns(len(cards))
            for (label, suffix, instruction), col in zip(cards, cols):
                url = f"{base_url}?eq={eq}&view={suffix}"
                png = _make_qr_png(url)
                with col:
                    st.markdown(f"#### {label}")
                    st.image(png, width=230)
                    st.caption(instruction)
                    st.code(url)
                    st.download_button(
                        f"Baixar QR - {label}",
                        data=png,
                        file_name=f"{eq}_{suffix}.png",
                        mime="image/png",
                        key=f"download_{eq}_{suffix}",
                    )

            st.markdown("### Baixar todos os QR Codes de equipamentos")
            st.caption("Gera um pacote ZIP com QR Codes de reserva, manutenção e POP quando houver documentação cadastrada.")
            zip_buf = BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for _, r in equipment.iterrows():
                    code = r["equipment_code"]
                    suffixes = ["reserva", "manutencao"]
                    if not is_blank(r.get("pop_path")):
                        suffixes.append("pop")
                    for suffix in suffixes:
                        url = f"{base_url}?eq={code}&view={suffix}"
                        zf.writestr(f"equipamentos/{code}_{suffix}.png", _make_qr_png(url))
            st.download_button(
                "Baixar ZIP - QR Codes de equipamentos",
                data=zip_buf.getvalue(),
                file_name="LabCim_QRCodes_Equipamentos.zip",
                mime="application/zip",
                key="download_all_equipment_qr",
            )

    with tab_sup:
        st.markdown("### QR Codes por insumo")
        if supplies.empty:
            st.info("Nenhum insumo ativo cadastrado. Cadastre insumos antes de gerar QR Codes do almoxarifado.")
        else:
            supply_label = st.selectbox("Insumo", _supply_options(supplies), key="qr_supply")
            supply_id = _supply_id_from_label(supplies, supply_label)
            selected_supply = supplies[supplies["id"] == supply_id].iloc[0]
            render_supply_quick_card(conn, selected_supply)

            url = f"{base_url}?view=insumo&sid={supply_id}"
            png = _make_qr_png(url)
            c1, c2 = st.columns([1, 2])
            with c1:
                st.image(png, width=260)
                st.download_button(
                    "Baixar QR do insumo",
                    data=png,
                    file_name=f"INSUMO_{supply_id}_{re.sub(r'[^A-Za-z0-9_-]+', '_', clean_value(selected_supply.get('supply_name')))}.png",
                    mime="image/png",
                    key=f"download_supply_qr_{supply_id}",
                )
            with c2:
                st.markdown("#### Ficha rápida / movimentação")
                st.caption("Cole este QR Code na embalagem, prateleira ou armário. Ao escanear, o usuário verá saldo, lote, validade, localização, responsável e documentos do insumo.")
                st.code(url)

            st.markdown("### Baixar todos os QR Codes de insumos")
            zip_buf = BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for _, r in supplies.iterrows():
                    sid = int(r["id"])
                    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", clean_value(r.get("supply_name")))
                    url = f"{base_url}?view=insumo&sid={sid}"
                    zf.writestr(f"insumos/INSUMO_{sid}_{safe_name}.png", _make_qr_png(url))
            st.download_button(
                "Baixar ZIP - QR Codes de insumos",
                data=zip_buf.getvalue(),
                file_name="LabCim_QRCodes_Insumos.zip",
                mime="application/zip",
                key="download_all_supply_qr",
            )


def page_importar(conn):
    hero()
    st.subheader("Importar base inicial")
    st.write("Use esta página para atualizar a base a partir do arquivo `LabCim_Base.xlsx`.")
    uploaded = st.file_uploader("Enviar arquivo Excel", type=["xlsx"])
    if uploaded is not None:
        tmp = Path("data/_uploaded_base.xlsx")
        tmp.write_bytes(uploaded.getvalue())
        if st.button("Importar arquivo enviado", type="primary"):
            try:
                counts = import_base_xlsx(conn, tmp)
                st.success(f"Importação concluída: {counts}")
                st.rerun()
            except Exception as exc:
                st.error(f"Erro na importação: {exc}")

    if BASE_XLSX.exists():
        if st.button("Reimportar arquivo local data/LabCim_Base.xlsx"):
            counts = import_base_xlsx(conn, BASE_XLSX)
            st.success(f"Importação concluída: {counts}")
            st.rerun()

    st.markdown("### Contagem atual")
    st.json(table_counts(conn))


def apply_url_params_hint():
    params = st.query_params
    if "eq" in params:
        st.sidebar.success(f"Equipamento via QR: {params.get('eq')}")
    if params.get("view") == "manutencao":
        st.sidebar.info("QR de manutenção detectado. Use a aba Manutenção.")
    if params.get("view") == "pop":
        st.sidebar.info("QR de POP/documentação detectado.")
    if params.get("view") == "insumo":
        st.sidebar.success(f"Insumo via QR: {params.get('sid', '-')}")


def main():
    setup_page()
    conn = get_conn()
    if not is_authenticated():
        page_login(conn)
        return
    apply_url_params_hint()
    page = sidebar()
    if page == "Painel inicial":
        page_dashboard(conn)
    elif page == "Reservas":
        page_reservas(conn)
    elif page == "Equipamentos":
        page_equipamentos(conn)
    elif page == "Insumos":
        page_insumos(conn)
    elif page == "Usuários":
        page_usuarios(conn)
    elif page == "Projetos":
        page_projetos(conn)
    elif page == "Manutenção":
        page_manutencao(conn)
    elif page == "QR Codes":
        page_qrcodes(conn)
    elif page == "Relatórios":
        page_relatorios(conn)
    elif page == "Importar base":
        page_importar(conn)


if __name__ == "__main__":
    main()
