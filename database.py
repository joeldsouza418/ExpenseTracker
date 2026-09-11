import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expense_tracker.db")


def get_db_connection(db_path=None):
    """Establishes a connection to the SQLite database."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=None):
    """Initializes the database schema with user authentication & multi-tenant user_id support."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 1. Create Users table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # 2. Create Transactions table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            type TEXT NOT NULL CHECK(type IN ('Income', 'Expense')),
            category TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0),
            date TEXT NOT NULL,
            note TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )

    # Check if user_id column exists in existing transactions table (migration check)
    cursor.execute("PRAGMA table_info(transactions);")
    columns = [col[1] for col in cursor.fetchall()]
    if "user_id" not in columns:
        cursor.execute("ALTER TABLE transactions ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1;")

    # Ensure default Guest user (id=1) exists
    cursor.execute("SELECT COUNT(*) FROM users WHERE id = 1;")
    if cursor.fetchone()[0] == 0:
        guest_hash = generate_password_hash("guest123")
        cursor.execute(
            "INSERT INTO users (id, username, password_hash) VALUES (1, 'Guest', ?)",
            (guest_hash,)
        )

    # Create indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);")

    conn.commit()
    conn.close()


# ==============================================================================
# USER AUTHENTICATION & MANAGEMENT
# ==============================================================================

def create_user(username, password, db_path=None):
    """Creates a new user with hashed password."""
    username_clean = username.strip()
    if not username_clean:
        return None, "Username cannot be empty."

    if len(password) < 4:
        return None, "Password must be at least 4 characters long."

    pwd_hash = generate_password_hash(password)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username_clean, pwd_hash)
        )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return {"id": new_id, "username": username_clean}, None
    except sqlite3.IntegrityError:
        conn.close()
        return None, "Username is already taken. Please choose another."
    except Exception as e:
        conn.close()
        return None, f"Error creating user: {str(e)}"


def authenticate_user(username, password, db_path=None):
    """Authenticates username and password against database."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username.strip(),))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user["password_hash"], password):
        return {"id": user["id"], "username": user["username"]}
    return None


def get_user_by_id(user_id, db_path=None):
    """Fetches user details by user_id."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, created_at FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return dict(user)
    return None


# ==============================================================================
# TRANSACTIONS DATA QUERY & ISOLATION
# ==============================================================================

def get_all_transactions(user_id=1, db_path=None, filter_type=None, search_query=None):
    """Retrieves transactions strictly for the specified user_id ordered by date descending."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    query = "SELECT * FROM transactions WHERE user_id = ?"
    params = [user_id]

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


def add_transaction(tx_type, category, amount, date, note="", user_id=1, db_path=None):
    """Adds a new transaction record associated with a specific user_id."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO transactions (user_id, type, category, amount, date, note)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, tx_type, category.strip(), float(amount), date, note.strip() if note else ""),
    )
    conn.commit()
    inserted_id = cursor.lastrowid
    conn.close()
    return inserted_id


def delete_transaction(tx_id, user_id=1, db_path=None):
    """Deletes a transaction by its ID, ensuring it belongs to the authenticated user_id."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (tx_id, user_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def get_financial_summary(user_id=1, db_path=None):
    """Calculates total income, total expense, and current balance strictly for user_id."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 
            COALESCE(SUM(CASE WHEN type = 'Income' THEN amount ELSE 0 END), 0) AS total_income,
            COALESCE(SUM(CASE WHEN type = 'Expense' THEN amount ELSE 0 END), 0) AS total_expense,
            COUNT(*) AS total_count
        FROM transactions
        WHERE user_id = ?
        """,
        (user_id,)
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


def get_category_breakdown(user_id=1, db_path=None):
    """Returns total amounts grouped by category strictly for user_id."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT type, category, SUM(amount) as total
        FROM transactions
        WHERE user_id = ?
        GROUP BY type, category
        ORDER BY total DESC
        """,
        (user_id,)
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


def get_analytics_summary(user_id=1, timeframe="month", target_period=None, db_path=None):
    """
    Retrieves period-based summary, category breakdown, and time-series trend data
    strictly for specified user_id.
    """
    from datetime import date as date_cls
    import calendar

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    today = date_cls.today()

    # Determine default target_period if not provided or invalid
    if timeframe == "day":
        if not target_period or len(target_period) != 10:
            target_period = today.strftime("%Y-%m-%d")
        sql_where = "WHERE user_id = ? AND date = ?"
        params = [user_id, target_period]
    elif timeframe == "year":
        if not target_period or len(target_period) != 4:
            target_period = today.strftime("%Y")
        sql_where = "WHERE user_id = ? AND strftime('%Y', date) = ?"
        params = [user_id, target_period]
    else:  # month (default)
        timeframe = "month"
        if not target_period or len(target_period) != 7:
            target_period = today.strftime("%Y-%m")
        sql_where = "WHERE user_id = ? AND strftime('%Y-%m', date) = ?"
        params = [user_id, target_period]

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

