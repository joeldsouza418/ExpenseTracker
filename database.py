import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expense_tracker.db")


def get_db_connection(db_path=None):
    """Establishes a connection to the SQLite database."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=None):
    """Initializes the database schema."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL CHECK(type IN ('Income', 'Expense')),
            category TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0),
            date TEXT NOT NULL,
            note TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    # Create indexes for performance
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);"
    )
    conn.commit()
    conn.close()


def get_all_transactions(db_path=None, filter_type=None, search_query=None):
    """Retrieves all transactions ordered by date descending."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    query = "SELECT * FROM transactions WHERE 1=1"
    params = []

    if filter_type in ("Income", "Expense"):
        query += " AND type = ?"
        params.append(filter_type)

    if search_query:
        query += " AND (category LIKE ? OR note LIKE ?)"
        term = f"%{search_query.strip()}%"
        params.extend([term, term])

    query += " ORDER BY date DESC, id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


def add_transaction(tx_type, category, amount, date, note="", db_path=None):
    """Adds a new transaction record."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO transactions (type, category, amount, date, note)
        VALUES (?, ?, ?, ?, ?)
        """,
        (tx_type, category.strip(), float(amount), date, note.strip() if note else ""),
    )
    conn.commit()
    inserted_id = cursor.lastrowid
    conn.close()
    return inserted_id


def delete_transaction(tx_id, db_path=None):
    """Deletes a transaction by its ID."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def get_financial_summary(db_path=None):
    """Calculates total income, total expense, and current balance."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 
            COALESCE(SUM(CASE WHEN type = 'Income' THEN amount ELSE 0 END), 0) AS total_income,
            COALESCE(SUM(CASE WHEN type = 'Expense' THEN amount ELSE 0 END), 0) AS total_expense,
            COUNT(*) AS total_count
        FROM transactions
        """
    )
    row = cursor.fetchone()
    conn.close()

    total_income = float(row["total_income"])
    total_expense = float(row["total_expense"])
    balance = total_income - total_expense
    count = int(row["total_count"])

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": balance,
        "transaction_count": count,
    }


def get_category_breakdown(db_path=None):
    """Returns total amounts grouped by category for expenses and income."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT type, category, SUM(amount) as total
        FROM transactions
        GROUP BY type, category
        ORDER BY total DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()

    breakdown = {"Income": [], "Expense": []}
    for row in rows:
        breakdown[row["type"]].append({
            "category": row["category"],
            "total": float(row["total"])
        })
    return breakdown
