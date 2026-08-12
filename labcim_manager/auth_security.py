from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import hmac
import logging
import os
import secrets
from typing import Mapping, MutableMapping

from labcim_manager.config import ConfigurationError


logger = logging.getLogger("labcim_manager.security")
NEUTRAL_OTP_REQUEST_MESSAGE = (
    "Se o endereço estiver elegível, um código de acesso será enviado."
)
INVALID_OTP_MESSAGE = (
    "Código inválido ou expirado. Solicite um novo código para tentar novamente."
)


@dataclass(frozen=True)
class AuthSecurityConfig:
    otp_ttl_seconds: int = 600
    max_verify_attempts: int = 5
    request_window_seconds: int = 900
    max_requests_per_identity: int = 3
    max_requests_per_origin: int = 20
    global_max_requests: int = 100


_SETTING_BOUNDS = {
    "LABCIM_OTP_TTL_SECONDS": (600, 60, 1800),
    "LABCIM_OTP_MAX_VERIFY_ATTEMPTS": (5, 3, 10),
    "LABCIM_OTP_REQUEST_WINDOW_SECONDS": (900, 60, 86400),
    "LABCIM_OTP_MAX_REQUESTS_PER_WINDOW": (3, 1, 20),
    "LABCIM_OTP_MAX_REQUESTS_PER_ORIGIN": (20, 1, 200),
    "LABCIM_OTP_GLOBAL_MAX_REQUESTS": (100, 10, 2000),
}


def _bounded_int(values: Mapping[str, str], key: str) -> int:
    default, minimum, maximum = _SETTING_BOUNDS[key]
    raw = str(values.get(key, default)).strip()
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{key} deve ser um número inteiro.") from exc
    if not minimum <= parsed <= maximum:
        raise ConfigurationError(f"{key} deve estar entre {minimum} e {maximum}.")
    return parsed


def load_auth_security_config(
    environ: Mapping[str, str] | None = None,
) -> AuthSecurityConfig:
    values = os.environ if environ is None else environ
    return AuthSecurityConfig(
        otp_ttl_seconds=_bounded_int(values, "LABCIM_OTP_TTL_SECONDS"),
        max_verify_attempts=_bounded_int(values, "LABCIM_OTP_MAX_VERIFY_ATTEMPTS"),
        request_window_seconds=_bounded_int(values, "LABCIM_OTP_REQUEST_WINDOW_SECONDS"),
        max_requests_per_identity=_bounded_int(values, "LABCIM_OTP_MAX_REQUESTS_PER_WINDOW"),
        max_requests_per_origin=_bounded_int(values, "LABCIM_OTP_MAX_REQUESTS_PER_ORIGIN"),
        global_max_requests=_bounded_int(values, "LABCIM_OTP_GLOBAL_MAX_REQUESTS"),
    )


def normalize_email_identity(value: object) -> str:
    return str(value or "").strip().lower()


def identity_hash(value: object) -> str:
    normalized = normalize_email_identity(value)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def origin_hash(value: object | None) -> str | None:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def identity_reference(value: object) -> str:
    return identity_hash(value)[:12]


def hash_otp_code(code: str, normalized_email: str, secret: str) -> str:
    if not secret:
        raise ConfigurationError("Um segredo de hash de OTP é obrigatório.")
    payload = f"labcim-otp-v1\0{normalize_email_identity(normalized_email)}\0{code}"
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def otp_hash_secret(environ: Mapping[str, str] | None = None) -> str:
    values = os.environ if environ is None else environ
    explicit = str(values.get("LABCIM_OTP_HASH_SECRET") or "").strip()
    if explicit:
        if len(explicit) < 32:
            raise ConfigurationError("LABCIM_OTP_HASH_SECRET deve ter pelo menos 32 caracteres.")
        return explicit
    cookie_secret = str(values.get("STREAMLIT_SERVER_COOKIE_SECRET") or "").strip()
    environment = str(values.get("APP_ENV") or "development").strip().lower()
    if cookie_secret:
        if len(cookie_secret) < 32:
            raise ConfigurationError(
                "STREAMLIT_SERVER_COOKIE_SECRET deve ter pelo menos 32 caracteres."
            )
        return cookie_secret
    if environment in {"staging", "production"}:
        raise ConfigurationError(
            "LABCIM_OTP_HASH_SECRET ou STREAMLIT_SERVER_COOKIE_SECRET é obrigatório."
        )
    return "labcim-development-only-otp-secret"


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def log_security_event(
    event_type: str,
    *,
    identity: object = "",
    result: str,
    reason: str,
    origin: object | None = None,
) -> str:
    event_id = secrets.token_hex(6)
    logger.info(
        "security_event reference=%s event=%s identity_ref=%s origin_ref=%s result=%s reason=%s",
        event_id,
        event_type,
        identity_reference(identity),
        (origin_hash(origin) or "unavailable")[:12],
        result,
        reason,
    )
    return event_id


def lookup_auth_identity(conn, email: object):
    normalized = normalize_email_identity(email)
    if not normalized:
        return "invalid", None
    rows = conn.execute(
        """
        SELECT *
        FROM users
        WHERE active = 1
          AND email IS NOT NULL
          AND LOWER(TRIM(email)) = ?
        ORDER BY id
        LIMIT 2
        """,
        [normalized],
    ).fetchall()
    if not rows:
        return "unknown_or_inactive", None
    if len(rows) > 1:
        return "ambiguous", None
    return "eligible", rows[0]


def normalized_email_conflicts(conn) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT LOWER(TRIM(email)) AS normalized_email,
               COUNT(*) AS user_count,
               SUM(CASE WHEN active = 1 THEN 1 ELSE 0 END) AS active_count
        FROM users
        WHERE email IS NOT NULL AND TRIM(email) <> ''
        GROUP BY LOWER(TRIM(email))
        HAVING COUNT(*) > 1
        ORDER BY LOWER(TRIM(email))
        """
    ).fetchall()
    return [dict(row) for row in rows]


def email_identity_available(conn, email: object, *, exclude_user_id: int | None = None) -> bool:
    normalized = normalize_email_identity(email)
    if not normalized:
        return True
    sql = "SELECT 1 FROM users WHERE LOWER(TRIM(email)) = ?"
    params: list[object] = [normalized]
    if exclude_user_id is not None:
        sql += " AND id <> ?"
        params.append(int(exclude_user_id))
    sql += " LIMIT 1"
    return conn.execute(sql, params).fetchone() is None


def register_otp_request(
    conn,
    email: object,
    *,
    origin: object | None,
    config: AuthSecurityConfig,
    now: datetime | None = None,
) -> tuple[bool, str]:
    now = now or datetime.now()
    occurred_at = now.isoformat(timespec="seconds")
    cutoff = (now - timedelta(seconds=config.request_window_seconds)).isoformat(
        timespec="seconds"
    )
    email_hash = identity_hash(email)
    request_origin_hash = origin_hash(origin)
    retention_cutoff = (now - timedelta(days=7)).isoformat(timespec="seconds")
    conn.execute(
        "DELETE FROM auth_rate_limit_events WHERE occurred_at < ?",
        [retention_cutoff],
    )
    row = conn.execute(
        """
        INSERT INTO auth_rate_limit_events (
            identity_hash, origin_hash, event_type, outcome, occurred_at
        ) VALUES (?, ?, 'otp_request', 'pending', ?)
        RETURNING id
        """,
        [email_hash, request_origin_hash, occurred_at],
    ).fetchone()
    conn.commit()
    event_id = int(row["id"])

    identity_count = int(
        conn.execute(
            """
            SELECT COUNT(*) AS n FROM auth_rate_limit_events
            WHERE event_type = 'otp_request' AND identity_hash = ? AND occurred_at >= ?
            """,
            [email_hash, cutoff],
        ).fetchone()["n"]
    )
    global_count = int(
        conn.execute(
            """
            SELECT COUNT(*) AS n FROM auth_rate_limit_events
            WHERE event_type = 'otp_request' AND occurred_at >= ?
            """,
            [cutoff],
        ).fetchone()["n"]
    )
    origin_count = 0
    if request_origin_hash:
        origin_count = int(
            conn.execute(
                """
                SELECT COUNT(*) AS n FROM auth_rate_limit_events
                WHERE event_type = 'otp_request' AND origin_hash = ? AND occurred_at >= ?
                """,
                [request_origin_hash, cutoff],
            ).fetchone()["n"]
        )

    reason = "accepted"
    if identity_count > config.max_requests_per_identity:
        reason = "identity_limit"
    elif request_origin_hash and origin_count > config.max_requests_per_origin:
        reason = "origin_limit"
    elif global_count > config.global_max_requests:
        reason = "global_limit"
    allowed = reason == "accepted"
    conn.execute(
        "UPDATE auth_rate_limit_events SET outcome = ? WHERE id = ?",
        [reason, event_id],
    )
    conn.commit()
    return allowed, reason


def clear_auth_session(state: MutableMapping[str, object]) -> None:
    for key in (
        "auth_user",
        "access_role",
        "pending_login_email",
        "last_access_code",
        "verify_code",
        "login_email",
    ):
        state.pop(key, None)
