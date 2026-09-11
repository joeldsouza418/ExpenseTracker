import os
import unittest
import tempfile
import database
import app as flask_app


class ExpenseTrackerTestCase(unittest.TestCase):
    def setUp(self):
        # Create a temporary SQLite database
        self.db_fd, self.temp_db_path = tempfile.mkstemp()
        flask_app.app.config["TESTING"] = True
        flask_app.app.config["WTF_CSRF_ENABLED"] = False
        self.client = flask_app.app.test_client()

        # Point database module to temp db
        database.init_db(self.temp_db_path)
        database.DB_PATH = self.temp_db_path

    def tearDown(self):
        os.close(self.db_fd)
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    def test_database_init(self):
        """Test database table is created with proper columns."""
        summary = database.get_financial_summary(self.temp_db_path)
        self.assertEqual(summary["total_income"], 0.0)
        self.assertEqual(summary["total_expense"], 0.0)
        self.assertEqual(summary["balance"], 0.0)
        self.assertEqual(summary["transaction_count"], 0)

    def test_add_and_summary_calculation(self):
        """Test adding transactions properly computes financial summary."""
        database.add_transaction(
            "Income", "Salary", 5000.00, "2026-09-01", "Monthly pay", self.temp_db_path
        )
        database.add_transaction(
            "Income", "Freelance", 1200.50, "2026-09-05", "Side project", self.temp_db_path
        )
        database.add_transaction(
            "Expense", "Rent", 1800.00, "2026-09-02", "Apartment", self.temp_db_path
        )
        database.add_transaction(
            "Expense", "Groceries", 250.25, "2026-09-03", "Supermarket", self.temp_db_path
        )

        summary = database.get_financial_summary(self.temp_db_path)
        self.assertAlmostEqual(summary["total_income"], 6200.50)
        self.assertAlmostEqual(summary["total_expense"], 2050.25)
        self.assertAlmostEqual(summary["balance"], 4150.25)
        self.assertEqual(summary["transaction_count"], 4)

        # Verify transaction retrieval
        txs = database.get_all_transactions(self.temp_db_path)
        self.assertEqual(len(txs), 4)

    def test_delete_transaction(self):
        """Test deleting a transaction properly updates the summary."""
        tx_id = database.add_transaction(
            "Income", "Gift", 100.00, "2026-09-01", "", self.temp_db_path
        )
        summary = database.get_financial_summary(self.temp_db_path)
        self.assertEqual(summary["total_income"], 100.00)

        deleted = database.delete_transaction(tx_id, self.temp_db_path)
        self.assertTrue(deleted)

        summary_after = database.get_financial_summary(self.temp_db_path)
        self.assertEqual(summary_after["total_income"], 0.00)
        self.assertEqual(summary_after["balance"], 0.00)

    def test_add_transaction_route_success(self):
        """Test Flask route POST /add with valid input."""
        response = self.client.post(
            "/add",
            data={
                "type": "Income",
                "category": "Consulting",
                "amount": "1500.00",
                "date": "2026-09-09",
                "note": "Client invoice #102",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"recorded successfully", response.data)
        self.assertIn(b"Consulting", response.data)
        self.assertIn(b"1,500.00", response.data)

    def test_validation_amount_greater_than_zero(self):
        """Test that amount <= 0 is rejected."""
        response = self.client.post(
            "/add",
            data={
                "type": "Expense",
                "category": "Coffee",
                "amount": "0",
                "date": "2026-09-09",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Amount must be greater than 0", response.data)

        # Negative amount
        response_neg = self.client.post(
            "/add",
            data={
                "type": "Expense",
                "category": "Coffee",
                "amount": "-25.50",
                "date": "2026-09-09",
            },
            follow_redirects=True,
        )
        self.assertEqual(response_neg.status_code, 200)
        self.assertIn(b"Amount must be greater than 0", response_neg.data)

    def test_validation_mandatory_fields(self):
        """Test that missing mandatory fields are rejected with proper messages."""
        # Missing category
        resp_cat = self.client.post(
            "/add",
            data={
                "type": "Expense",
                "category": "",
                "amount": "50",
                "date": "2026-09-09",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Category is required", resp_cat.data)

        # Missing date
        resp_date = self.client.post(
            "/add",
            data={
                "type": "Expense",
                "category": "Lunch",
                "amount": "15",
                "date": "",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Date is required", resp_date.data)

        # Invalid type
        resp_type = self.client.post(
            "/add",
            data={
                "type": "InvalidType",
                "category": "Lunch",
                "amount": "15",
                "date": "2026-09-09",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Please select a valid transaction type", resp_type.data)

    def test_analytics_summary_route(self):
        """Test GET /summary route for day, month, and year views."""
        database.add_transaction("Income", "Salary", 4000.00, "2026-09-10", "", self.temp_db_path)
        database.add_transaction("Expense", "Rent", 1200.00, "2026-09-10", "", self.temp_db_path)
        database.add_transaction("Expense", "Groceries", 150.00, "2026-09-05", "", self.temp_db_path)

        # Test month view
        response_month = self.client.get("/summary?timeframe=month&period=2026-09")
        self.assertEqual(response_month.status_code, 200)
        self.assertIn(b"SPENDING SUMMARY", response_month.data)
        self.assertIn(b"4,000.00", response_month.data)

        # Test day view
        response_day = self.client.get("/summary?timeframe=day&period=2026-09-10")
        self.assertEqual(response_day.status_code, 200)
        self.assertIn(b"1,200.00", response_day.data)

    def test_user_registration_and_login_isolation(self):
        """Test that different users only see their own transactions."""
        # 1. Register User A
        u_a, err_a = database.create_user("user_alice", "password123", self.temp_db_path)
        self.assertIsNotNone(u_a)
        self.assertIsNone(err_a)

        # 2. Register User B
        u_b, err_b = database.create_user("user_bob", "password456", self.temp_db_path)
        self.assertIsNotNone(u_b)
        self.assertIsNone(err_b)

        # 3. Add transaction for User A (Alice: 10,000 Income)
        database.add_transaction("Income", "Salary", 10000.00, "2026-09-01", "Alice Salary", user_id=u_a["id"], db_path=self.temp_db_path)

        # 4. Add transaction for User B (Bob: 500 Expense)
        database.add_transaction("Expense", "Books", 500.00, "2026-09-02", "Bob Books", user_id=u_b["id"], db_path=self.temp_db_path)

        # 5. Check Alice's summary
        summary_a = database.get_financial_summary(user_id=u_a["id"], db_path=self.temp_db_path)
        self.assertEqual(summary_a["total_income"], 10000.00)
        self.assertEqual(summary_a["total_expense"], 0.00)
        self.assertEqual(summary_a["transaction_count"], 1)

        # 6. Check Bob's summary
        summary_b = database.get_financial_summary(user_id=u_b["id"], db_path=self.temp_db_path)
        self.assertEqual(summary_b["total_income"], 0.00)
        self.assertEqual(summary_b["total_expense"], 500.00)
        self.assertEqual(summary_b["transaction_count"], 1)

        # 7. Test authentication helper
        auth_success = database.authenticate_user("user_alice", "password123", self.temp_db_path)
        self.assertIsNotNone(auth_success)
        self.assertEqual(auth_success["username"], "user_alice")

        auth_fail = database.authenticate_user("user_alice", "wrongpass", self.temp_db_path)
        self.assertIsNone(auth_fail)


if __name__ == "__main__":
    unittest.main()

