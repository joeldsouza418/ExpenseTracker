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


def get_analytics_summary(timeframe="month", target_period=None, db_path=None):
    """
    Retrieves period-based summary, category breakdown, and time-series trend data
    for Day, Month, or Year filters.
    """
    from datetime import datetime, date as date_cls
    import calendar

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    today = date_cls.today()

    # Determine default target_period if not provided or invalid
    if timeframe == "day":
        if not target_period or len(target_period) != 10:
            target_period = today.strftime("%Y-%m-%d")
        sql_where = "WHERE date = ?"
        params = [target_period]
    elif timeframe == "year":
        if not target_period or len(target_period) != 4:
            target_period = today.strftime("%Y")
        sql_where = "WHERE strftime('%Y', date) = ?"
        params = [target_period]
    else:  # month (default)
        timeframe = "month"
        if not target_period or len(target_period) != 7:
            target_period = today.strftime("%Y-%m")
        sql_where = "WHERE strftime('%Y-%m', date) = ?"
        params = [target_period]

    # 1. Total Income, Expense, Count for period
    cursor.execute(
        f"""
        SELECT 
            COALESCE(SUM(CASE WHEN type = 'Income' THEN amount ELSE 0 END), 0) AS total_income,
            COALESCE(SUM(CASE WHEN type = 'Expense' THEN amount ELSE 0 END), 0) AS total_expense,
            COUNT(*) AS total_count
        FROM transactions
        {sql_where}
        """,
        params,
    )
    row = cursor.fetchone()
    period_income = float(row["total_income"])
    period_expense = float(row["total_expense"])
    period_balance = period_income - period_expense
    count = int(row["total_count"])

    savings_rate = 0.0
    if period_income > 0:
        savings_rate = round(((period_income - period_expense) / period_income) * 100, 1)

    # 2. Category Breakdown for Expenses in Period
    cursor.execute(
        f"""
        SELECT category, SUM(amount) as total, COUNT(*) as count
        FROM transactions
        {sql_where} AND type = 'Expense'
        GROUP BY category
        ORDER BY total DESC
        """,
        params,
    )
    expense_rows = cursor.fetchall()
    expense_categories = []
    for r in expense_rows:
        tot = float(r["total"])
        pct = round((tot / period_expense * 100), 1) if period_expense > 0 else 0.0
        expense_categories.append({
            "category": r["category"],
            "total": tot,
            "count": int(r["count"]),
            "percentage": pct
        })

    # 3. Category Breakdown for Income in Period
    cursor.execute(
        f"""
        SELECT category, SUM(amount) as total, COUNT(*) as count
        FROM transactions
        {sql_where} AND type = 'Income'
        GROUP BY category
        ORDER BY total DESC
        """,
        params,
    )
    income_rows = cursor.fetchall()
    income_categories = []
    for r in income_rows:
        tot = float(r["total"])
        pct = round((tot / period_income * 100), 1) if period_income > 0 else 0.0
        income_categories.append({
            "category": r["category"],
            "total": tot,
            "count": int(r["count"]),
            "percentage": pct
        })

    # 4. Timeline Trend Data for Chart
    trend_labels = []
    trend_income = []
    trend_expense = []

    if timeframe == "day":
        # Group by individual transactions for that day or category breakdown
        cursor.execute(
            f"""
            SELECT type, category, amount, date
            FROM transactions
            {sql_where}
            ORDER BY id ASC
            """,
            params,
        )
        day_txs = cursor.fetchall()
        if day_txs:
            for idx, r in enumerate(day_txs, 1):
                trend_labels.append(f"{r['category']} (#{idx})")
                if r["type"] == "Income":
                    trend_income.append(float(r["amount"]))
                    trend_expense.append(0.0)
                else:
                    trend_income.append(0.0)
                    trend_expense.append(float(r["amount"]))
        else:
            trend_labels = ["Income", "Expense"]
            trend_income = [0.0, 0.0]
            trend_expense = [0.0, 0.0]

    elif timeframe == "month":
        # Days in month: 1 to max_days
        try:
            yr_str, mo_str = target_period.split("-")
            year_int, month_int = int(yr_str), int(mo_str)
            _, max_days = calendar.monthrange(year_int, month_int)
        except Exception:
            max_days = 31

        cursor.execute(
            f"""
            SELECT strftime('%d', date) as day_str, type, SUM(amount) as total
            FROM transactions
            {sql_where}
            GROUP BY day_str, type
            """,
            params,
        )
        month_rows = cursor.fetchall()
        daily_map = {d: {"Income": 0.0, "Expense": 0.0} for d in range(1, max_days + 1)}

        for r in month_rows:
            try:
                d_num = int(r["day_str"])
                if d_num in daily_map:
                    daily_map[d_num][r["type"]] = float(r["total"])
            except (ValueError, TypeError):
                pass

        for d in range(1, max_days + 1):
            trend_labels.append(f"Day {d}")
            trend_income.append(daily_map[d]["Income"])
            trend_expense.append(daily_map[d]["Expense"])

    elif timeframe == "year":
        # Months 1 to 12
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        cursor.execute(
            f"""
            SELECT strftime('%m', date) as month_str, type, SUM(amount) as total
            FROM transactions
            {sql_where}
            GROUP BY month_str, type
            """,
            params,
        )
        year_rows = cursor.fetchall()
        monthly_map = {m: {"Income": 0.0, "Expense": 0.0} for m in range(1, 13)}

        for r in year_rows:
            try:
                m_num = int(r["month_str"])
                if m_num in monthly_map:
                    monthly_map[m_num][r["type"]] = float(r["total"])
            except (ValueError, TypeError):
                pass

        for m in range(1, 13):
            trend_labels.append(month_names[m - 1])
            trend_income.append(monthly_map[m]["Income"])
            trend_expense.append(monthly_map[m]["Expense"])

    conn.close()

    return {
        "timeframe": timeframe,
        "target_period": target_period,
        "period_income": period_income,
        "period_expense": period_expense,
        "period_balance": period_balance,
        "savings_rate": savings_rate,
        "transaction_count": count,
        "expense_categories": expense_categories,
        "income_categories": income_categories,
        "chart_data": {
            "labels": trend_labels,
            "income": trend_income,
            "expense": trend_expense,
        },
    }

