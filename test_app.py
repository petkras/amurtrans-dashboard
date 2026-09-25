"""Run with: python -m unittest -v test_app.py"""
import io
import unittest

import app


class DashboardTests(unittest.TestCase):
    def test_demo_rows_and_columns(self):
        self.assertEqual(len(app.INITIAL), 120)
        self.assertTrue(app.REQUIRED.issubset(app.INITIAL.columns))

    def test_missing_columns_rejected(self):
        with self.assertRaisesRegex(ValueError, "Нет столбцов"):
            app.parse_csv(b"order_id,created_at\n1,2026-01-01\n")

    def test_invalid_rows_rejected(self):
        header = ",".join(sorted(app.REQUIRED))
        with self.assertRaisesRegex(ValueError, "нет корректных заказов"):
            app.parse_csv((header + "\n" + ",".join(["bad"] * len(app.REQUIRED))).encode())

    def test_filters_apply_to_all_outputs(self):
        rows = app.INITIAL.to_dict("records")
        carrier = rows[0]["carrier"]
        outputs = app.update_view(rows, "2026-01-01", "2026-12-31", ["Закрыт"], carrier)
        table = outputs[-1]
        self.assertTrue(all(row["status"] == "Закрыт" and row["carrier"] == carrier for row in table))
        self.assertEqual(int(outputs[0][0].children[1].children), len(table))

    def test_http_home(self):
        self.assertEqual(app.server.test_client().get("/").status_code, 200)


if __name__ == "__main__":
    unittest.main()
