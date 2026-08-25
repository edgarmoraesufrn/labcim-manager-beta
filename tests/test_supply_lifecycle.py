from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from labcim_manager.db import (
    connect,
    create_supply,
    create_supply_lot,
    delete_supply_if_unused,
    get_supply_usage_summary,
    inactivate_supply,
    reactivate_supply,
)
from labcim_manager.schema import initialize_schema


def create_test_supply(conn, *, name: str, current_quantity: float = 0.0) -> int:
    return create_supply(
        conn,
        supply_type="Insumo",
        supply_name=name,
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
        current_quantity=current_quantity,
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


class SupplyLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tempdir.name) / "lifecycle.db"
        self.conn = connect(self.path)
        initialize_schema(self.conn)

    def tearDown(self) -> None:
        self.conn.close()
        self.tempdir.cleanup()

    def test_inactivate_reactivate_preserves_last_inactivation_audit(self) -> None:
        supply_id = create_test_supply(self.conn, name="Lifecycle audit")

        ok, message = inactivate_supply(
            self.conn,
            supply_id,
            inactive_reason="Cadastro substituído",
            inactive_by_id=None,
        )
        self.assertTrue(ok, message)

        row = self.conn.execute(
            """
            SELECT active, inactive_reason, inactive_by_id, inactive_at
            FROM supplies
            WHERE id = ?
            """,
            [supply_id],
        ).fetchone()
        self.assertEqual(int(row["active"]), 0)
        self.assertEqual(row["inactive_reason"], "Cadastro substituído")
        self.assertIsNone(row["inactive_by_id"])
        self.assertTrue(str(row["inactive_at"] or "").strip())

        ok, message = reactivate_supply(self.conn, supply_id)
        self.assertTrue(ok, message)

        row = self.conn.execute(
            """
            SELECT active, inactive_reason, inactive_at
            FROM supplies
            WHERE id = ?
            """,
            [supply_id],
        ).fetchone()
        self.assertEqual(int(row["active"]), 1)
        self.assertEqual(row["inactive_reason"], "Cadastro substituído")
        self.assertTrue(str(row["inactive_at"] or "").strip())

    def test_inactivation_requires_reason_and_zero_stock(self) -> None:
        supply_id = create_test_supply(
            self.conn,
            name="Com estoque",
            current_quantity=2.0,
        )

        ok, message = inactivate_supply(
            self.conn,
            supply_id,
            inactive_reason="",
        )
        self.assertFalse(ok)
        self.assertIn("motivo", message.lower())

        ok, message = inactivate_supply(
            self.conn,
            supply_id,
            inactive_reason="Descontinuado",
        )
        self.assertFalse(ok)
        self.assertIn("saldo", message.lower())

        active = self.conn.execute(
            "SELECT active FROM supplies WHERE id = ?",
            [supply_id],
        ).fetchone()["active"]
        self.assertEqual(int(active), 1)

    def test_delete_is_allowed_only_for_virgin_record(self) -> None:
        virgin_id = create_test_supply(self.conn, name="Virgem")
        usage = get_supply_usage_summary(self.conn, virgin_id)
        self.assertIsNotNone(usage)
        self.assertEqual(usage["movements"], 0)
        self.assertEqual(usage["lots"], 0)

        ok, message = delete_supply_if_unused(self.conn, virgin_id)
        self.assertTrue(ok, message)
        self.assertIsNone(
            self.conn.execute(
                "SELECT id FROM supplies WHERE id = ?",
                [virgin_id],
            ).fetchone()
        )

        used_id = create_test_supply(self.conn, name="Com lote")
        create_supply_lot(
            self.conn,
            supply_id=used_id,
            lot_code="LOT-001",
            initial_quantity=0,
            current_quantity=0,
        )

        ok, message = delete_supply_if_unused(self.conn, used_id)
        self.assertFalse(ok)
        self.assertIn("lotes", message.lower())
        self.assertIsNotNone(
            self.conn.execute(
                "SELECT id FROM supplies WHERE id = ?",
                [used_id],
            ).fetchone()
        )


if __name__ == "__main__":
    unittest.main()
