from __future__ import annotations

from datetime import datetime, timedelta
from contextlib import redirect_stdout
from io import StringIO
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import app

from labcim_manager.auth_security import (
    AuthSecurityConfig,
    NEUTRAL_OTP_REQUEST_MESSAGE,
    clear_auth_session,
    email_identity_available,
    hash_otp_code,
    load_auth_security_config,
    lookup_auth_identity,
    normalize_email_identity,
    normalized_email_conflicts,
    register_otp_request,
)
from labcim_manager.config import ConfigurationError
from labcim_manager.db import (
    connect,
    create_access_code_record,
    create_user,
    update_user,
    verify_access_code_record,
)
from labcim_manager.db_migrate import run as run_migration_cli
from labcim_manager.schema import initialize_schema


SECRET = "test-only-otp-hmac-secret"


class AuthenticationSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary_directory.name) / "auth.db"
        self.conn = connect(self.path)
        initialize_schema(self.conn)

    def tearDown(self) -> None:
        self.conn.close()
        self.temporary_directory.cleanup()

    def add_user(
        self,
        email: str,
        *,
        full_name: str = "Pessoa Teste",
        role: str = "member",
        active: int = 1,
    ) -> int:
        cursor = self.conn.execute(
            "INSERT INTO users (full_name, email, role, active) VALUES (?, ?, ?, ?)",
            [full_name, email, role, active],
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def issue(self, user_id: int, email: str, code: str, expires_at: datetime) -> str:
        normalized = normalize_email_identity(email)
        digest = hash_otp_code(code, normalized, SECRET)
        create_access_code_record(
            self.conn,
            user_id=user_id,
            email=email,
            code_hash=digest,
            expires_at=expires_at.isoformat(timespec="seconds"),
        )
        return digest

    def test_normalization_and_ambiguous_identity_detection(self) -> None:
        self.assertEqual(normalize_email_identity("  Pessoa@UFRN.BR  "), "pessoa@ufrn.br")
        first_id = self.add_user("Pessoa@UFRN.BR")
        self.assertFalse(email_identity_available(self.conn, " pessoa@ufrn.br "))
        self.add_user(" pessoa@ufrn.br ", full_name="Outra pessoa")

        state, row = lookup_auth_identity(self.conn, "PESSOA@UFRN.BR")
        self.assertEqual(state, "ambiguous")
        self.assertIsNone(row)
        conflicts = normalized_email_conflicts(self.conn)
        self.assertEqual(conflicts[0]["normalized_email"], "pessoa@ufrn.br")
        self.assertEqual(int(conflicts[0]["user_count"]), 2)

        self.assertFalse(email_identity_available(self.conn, "pessoa@ufrn.br", exclude_user_id=first_id))

        output = StringIO()
        with redirect_stdout(output):
            result = run_migration_cli(
                ["--sqlite-path", str(self.path), "diagnose-email-identities"]
            )
        self.assertEqual(result, 1)
        self.assertIn("normalized_email_conflicts=1", output.getvalue())
        self.assertIn("identity_ref:", output.getvalue())
        self.assertNotIn("pessoa@ufrn.br", output.getvalue())

    def test_create_and_update_prevent_normalized_duplicate_identity(self) -> None:
        first_id = self.add_user("first@ufrn.br")
        second_id = self.add_user("second@ufrn.br")
        common = dict(
            phone_e164=None,
            role="member",
            lab_unit=None,
            department=None,
            advisor_name=None,
            training_completed=0,
            active=1,
            notes=None,
        )
        ok, message = create_user(
            self.conn,
            full_name="Duplicada",
            email=" FIRST@UFRN.BR ",
            **common,
        )
        self.assertFalse(ok)
        self.assertIn("e-mail", message)
        ok, message = update_user(
            self.conn,
            second_id,
            full_name="Segunda",
            email=" First@Ufrn.Br ",
            **common,
        )
        self.assertFalse(ok)
        self.assertIn("e-mail", message)
        self.assertTrue(email_identity_available(self.conn, "first@ufrn.br", exclude_user_id=first_id))

    def test_request_response_is_neutral_for_known_and_unknown_email(self) -> None:
        self.add_user("known@ufrn.br")
        session: dict[str, object] = {}
        config = AuthSecurityConfig(max_requests_per_origin=10, global_max_requests=20)
        with (
            patch.object(app.st, "session_state", session),
            patch.object(app, "_request_origin", return_value="192.0.2.10"),
            patch.object(app, "load_auth_security_config", return_value=config),
            patch.object(app, "otp_hash_secret", return_value=SECRET),
            patch.object(app, "generate_otp_code", return_value="314159"),
            patch.object(app, "send_email", return_value=(True, "sent")) as send,
        ):
            known = app.request_access_code(self.conn, " Known@UFRN.BR ")
            known_pending = session["pending_login_email"]
            unknown = app.request_access_code(self.conn, "unknown@ufrn.br")
            unknown_pending = session["pending_login_email"]

        self.assertEqual(known, (True, NEUTRAL_OTP_REQUEST_MESSAGE))
        self.assertEqual(unknown, known)
        self.assertEqual(known_pending, "known@ufrn.br")
        self.assertEqual(unknown_pending, "unknown@ufrn.br")
        self.assertEqual(send.call_count, 1)

    def test_request_rate_limit_normalizes_identity_and_persists_events(self) -> None:
        config = AuthSecurityConfig(
            request_window_seconds=900,
            max_requests_per_identity=2,
            max_requests_per_origin=20,
            global_max_requests=100,
        )
        now = datetime(2026, 8, 12, 12, 0, 0)
        results = [
            register_otp_request(
                self.conn,
                value,
                origin="192.0.2.20",
                config=config,
                now=now + timedelta(seconds=index),
            )
            for index, value in enumerate(
                ("Person@UFRN.BR", " person@ufrn.br ", "PERSON@ufrn.br")
            )
        ]
        self.assertEqual([allowed for allowed, _ in results], [True, True, False])
        events = self.conn.execute(
            "SELECT identity_hash, origin_hash, outcome FROM auth_rate_limit_events ORDER BY id"
        ).fetchall()
        self.assertEqual(len({row["identity_hash"] for row in events}), 1)
        self.assertTrue(all("person@" not in str(dict(row)) for row in events))
        self.assertEqual(events[-1]["outcome"], "identity_limit")

    def test_request_rate_limit_enforces_origin_and_global_ceilings(self) -> None:
        now = datetime(2026, 8, 12, 12, 0, 0)
        origin_config = AuthSecurityConfig(
            max_requests_per_identity=20,
            max_requests_per_origin=2,
            global_max_requests=100,
        )
        results = [
            register_otp_request(
                self.conn,
                f"person-{index}@ufrn.br",
                origin="198.51.100.7",
                config=origin_config,
                now=now + timedelta(seconds=index),
            )
            for index in range(3)
        ]
        self.assertEqual([result[1] for result in results], ["accepted", "accepted", "origin_limit"])

        global_config = AuthSecurityConfig(
            max_requests_per_identity=20,
            max_requests_per_origin=20,
            global_max_requests=2,
        )
        later = now + timedelta(hours=1)
        results = [
            register_otp_request(
                self.conn,
                f"global-{index}@ufrn.br",
                origin=None,
                config=global_config,
                now=later + timedelta(seconds=index),
            )
            for index in range(3)
        ]
        self.assertEqual([result[1] for result in results], ["accepted", "accepted", "global_limit"])

    def test_expiration_one_time_use_and_new_code_invalidation(self) -> None:
        user_id = self.add_user("otp@ufrn.br")
        expired_hash = self.issue(
            user_id,
            "otp@ufrn.br",
            "111111",
            datetime.now() - timedelta(seconds=1),
        )
        ok, _, _ = verify_access_code_record(
            self.conn,
            email=" OTP@UFRN.BR ",
            code_hash=expired_hash,
        )
        self.assertFalse(ok)

        first_hash = self.issue(
            user_id,
            "otp@ufrn.br",
            "222222",
            datetime.now() + timedelta(minutes=10),
        )
        second_hash = self.issue(
            user_id,
            "otp@ufrn.br",
            "333333",
            datetime.now() + timedelta(minutes=10),
        )
        ok, _, _ = verify_access_code_record(
            self.conn,
            email="otp@ufrn.br",
            code_hash=first_hash,
        )
        self.assertFalse(ok)
        ok, _, row = verify_access_code_record(
            self.conn,
            email="otp@ufrn.br",
            code_hash=second_hash,
        )
        self.assertTrue(ok)
        self.assertIsNotNone(row)
        ok, _, _ = verify_access_code_record(
            self.conn,
            email="otp@ufrn.br",
            code_hash=second_hash,
        )
        self.assertFalse(ok)

    def test_wrong_code_attempt_ceiling_consumes_challenge(self) -> None:
        user_id = self.add_user("attempts@ufrn.br")
        correct_hash = self.issue(
            user_id,
            "attempts@ufrn.br",
            "444444",
            datetime.now() + timedelta(minutes=10),
        )
        wrong_hash = hash_otp_code("000000", "attempts@ufrn.br", SECRET)
        for _ in range(5):
            ok, _, _ = verify_access_code_record(
                self.conn,
                email="attempts@ufrn.br",
                code_hash=wrong_hash,
                max_attempts=5,
            )
            self.assertFalse(ok)
        challenge = self.conn.execute(
            "SELECT attempts, used_at FROM access_codes ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.assertEqual(int(challenge["attempts"]), 5)
        self.assertIsNotNone(challenge["used_at"])
        ok, _, _ = verify_access_code_record(
            self.conn,
            email="attempts@ufrn.br",
            code_hash=correct_hash,
            max_attempts=5,
        )
        self.assertFalse(ok)

    def test_smtp_failure_invalidates_challenge_and_never_logs_plaintext_otp(self) -> None:
        self.add_user("smtp@ufrn.br")
        session: dict[str, object] = {}
        sentinel_code = "731942"
        with (
            patch.object(app.st, "session_state", session),
            patch.object(app, "_request_origin", return_value="192.0.2.30"),
            patch.object(app, "otp_hash_secret", return_value=SECRET),
            patch.object(app, "generate_otp_code", return_value=sentinel_code),
            patch.object(app, "send_email", return_value=(False, "opaque-reference")),
            self.assertLogs("labcim_manager.security", level=logging.INFO) as captured,
        ):
            result = app.request_access_code(self.conn, "smtp@ufrn.br")

        self.assertEqual(result, (True, NEUTRAL_OTP_REQUEST_MESSAGE))
        self.assertNotIn(sentinel_code, "\n".join(captured.output))
        challenge = self.conn.execute(
            "SELECT used_at FROM access_codes ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.assertIsNotNone(challenge["used_at"])
        notification = self.conn.execute(
            "SELECT body, error_message FROM notification_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.assertNotIn(sentinel_code, str(dict(notification)))

    def test_public_request_stays_neutral_when_rate_limit_storage_fails(self) -> None:
        session: dict[str, object] = {}
        with (
            patch.object(app.st, "session_state", session),
            patch.object(app, "_request_origin", return_value=None),
            patch.object(
                app,
                "register_otp_request",
                side_effect=RuntimeError("database unavailable"),
            ),
            patch.object(app, "safe_exception_message", return_value="opaque"),
        ):
            result = app.request_access_code(self.conn, "someone@ufrn.br")
        self.assertEqual(result, (True, NEUTRAL_OTP_REQUEST_MESSAGE))

    def test_logout_clear_and_role_revalidation_use_authoritative_user(self) -> None:
        user_id = self.add_user("role@ufrn.br", role="member")
        state: dict[str, object] = {
            "auth_user": {"id": user_id, "email": "role@ufrn.br", "role": "admin"},
            "access_role": "admin",
            "pending_login_email": "role@ufrn.br",
            "verify_code": "123456",
            "unrelated": "preserved",
        }
        with patch.object(app.st, "session_state", state):
            user = app.revalidate_authenticated_user(self.conn)
            self.assertEqual(user["role"], "member")
            app.logout()
        self.assertNotIn("auth_user", state)
        self.assertNotIn("access_role", state)
        self.assertNotIn("verify_code", state)
        self.assertEqual(state["unrelated"], "preserved")

    def test_security_configuration_rejects_invalid_values_and_missing_production_secret(self) -> None:
        with self.assertRaises(ConfigurationError):
            load_auth_security_config({"LABCIM_OTP_MAX_VERIFY_ATTEMPTS": "2"})
        with self.assertRaises(ConfigurationError):
            app.otp_hash_secret({"APP_ENV": "production"})
        with self.assertRaises(ConfigurationError):
            app.otp_hash_secret(
                {"APP_ENV": "production", "LABCIM_OTP_HASH_SECRET": "too-short"}
            )

    def test_legacy_local_document_resolution_is_limited_to_document_roots(self) -> None:
        self.assertIsNone(app._resolve_local_doc("app.py"))
        self.assertIsNone(app._resolve_local_doc("data/labcim_manager.db"))
        pop_files = [path for path in app.POP_DIR.glob("*") if path.is_file()]
        if pop_files:
            self.assertEqual(app._resolve_local_doc(pop_files[0]), pop_files[0].resolve())


if __name__ == "__main__":
    unittest.main()
