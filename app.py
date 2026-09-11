import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session
import database

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "expense-tracker-secret-key-2026")

# Ensure database is initialized
database.init_db()


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(os.path.join(app.root_path, "static"), "favicon.ico", mimetype="image/vnd.microsoft.icon")


@app.template_filter("format_currency")
def format_currency(value):
    """Format a numeric value into Rupees currency format (₹)."""
    try:
        val = float(value)
        return f"₹{val:,.2f}"
    except (ValueError, TypeError):
        return "₹0.00"


@app.before_request
def ensure_session_user():
    """Ensure every visitor has a session assigned (defaults to Guest user_id = 1)."""
    if "user_id" not in session:
        session["user_id"] = 1
        session["username"] = "Guest"


@app.context_processor
def inject_context():
    """Inject dynamic time-of-day greeting and current_user into all Jinja templates."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        greeting = "Good morning!"
    elif 12 <= hour < 17:
        greeting = "Good afternoon!"
    elif 17 <= hour < 22:
        greeting = "Good evening!"
    else:
        greeting = "Good night!"

    user_id = session.get("user_id", 1)
    username = session.get("username", "Guest")
    is_guest = (user_id == 1 or username == "Guest")

    return dict(
        greeting=greeting,
        current_user={"id": user_id, "username": username, "is_guest": is_guest}
    )


# ==============================================================================
# AUTHENTICATION ROUTES
# ==============================================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not username:
            flash("Username is required.", "danger")
            return render_template("register.html", username=username)

        if not password:
            flash("Password is required.", "danger")
            return render_template("register.html", username=username)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html", username=username)

        user, err = database.create_user(username, password)
        if err:
            flash(err, "danger")
            return render_template("register.html", username=username)

        # Log in the newly registered user
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        flash(f"Welcome, {user['username']}! Account created successfully.", "success")
        return redirect(url_for("index"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Please enter both username and password.", "danger")
            return render_template("login.html", username=username)

        user = database.authenticate_user(username, password)
        if not user:
            flash("Invalid username or password.", "danger")
            return render_template("login.html", username=username)

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        flash(f"Welcome back, {user['username']}!", "success")
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    session["user_id"] = 1
    session["username"] = "Guest"
    flash("You have logged out.", "info")
    return redirect(url_for("login"))


@app.route("/guest", methods=["GET"])
def guest_session():
    session["user_id"] = 1
    session["username"] = "Guest"
    flash("Switched to Guest Mode. Create an account to save your private records!", "info")
    return redirect(url_for("index"))


# ==============================================================================
# MAIN APPLICATION ROUTES (ISOLATED BY USER_ID)
# ==============================================================================

@app.route("/", methods=["GET"])
def index():
    user_id = session.get("user_id", 1)
    filter_type = request.args.get("type", "").strip()
    search_query = request.args.get("search", "").strip()

    transactions = database.get_all_transactions(
        user_id=user_id,
        filter_type=filter_type if filter_type in ("Income", "Expense") else None,
        search_query=search_query if search_query else None,
    )
    summary = database.get_financial_summary(user_id=user_id)
    breakdown = database.get_category_breakdown(user_id=user_id)

    today_str = datetime.today().strftime("%Y-%m-%d")

    return render_template(
        "index.html",
        transactions=transactions,
        summary=summary,
        breakdown=breakdown,
        filter_type=filter_type,
        search_query=search_query,
        today=today_str,
        active_tab="dashboard",
    )


@app.route("/summary", methods=["GET"])
def summary():
    user_id = session.get("user_id", 1)
    timeframe = request.args.get("timeframe", "month").strip().lower()
    if timeframe not in ("day", "month", "year"):
        timeframe = "month"

    target_period = request.args.get("period", "").strip()

    today_str = datetime.today().strftime("%Y-%m-%d")
    current_month_str = datetime.today().strftime("%Y-%m")
    current_year_str = datetime.today().strftime("%Y")

    if not target_period:
        if timeframe == "day":
            target_period = today_str
        elif timeframe == "year":
            target_period = current_year_str
        else:
            target_period = current_month_str

    analytics = database.get_analytics_summary(user_id=user_id, timeframe=timeframe, target_period=target_period)

    return render_template(
        "summary.html",
        analytics=analytics,
        today=today_str,
        current_month=current_month_str,
        current_year=current_year_str,
        active_tab="summary",
    )


@app.route("/add", methods=["POST"])
def add_transaction():
    user_id = session.get("user_id", 1)
    tx_type = request.form.get("type", "").strip()
    category = request.form.get("category", "").strip()
    amount_raw = request.form.get("amount", "").strip()
    date_val = request.form.get("date", "").strip()
    note = request.form.get("note", "").strip()

    # Validation
    errors = []

    if not tx_type or tx_type not in ("Income", "Expense"):
        errors.append("Please select a valid transaction type (Income or Expense).")

    if not category:
        errors.append("Category is required.")

    if not amount_raw:
        errors.append("Amount is required.")
    else:
        try:
            amount = float(amount_raw)
            if amount <= 0:
                errors.append("Amount must be greater than 0.")
        except ValueError:
            errors.append("Amount must be a valid number.")

    if not date_val:
        errors.append("Date is required.")
    else:
        try:
            datetime.strptime(date_val, "%Y-%m-%d")
        except ValueError:
            errors.append("Invalid date format. Please use YYYY-MM-DD.")

    if errors:
        for err in errors:
            flash(err, "danger")
        return redirect(url_for("index"))

    try:
        database.add_transaction(
            user_id=user_id,
            tx_type=tx_type,
            category=category,
            amount=amount,
            date=date_val,
            note=note,
        )
        flash(
            f"{tx_type} of {format_currency(amount)} recorded successfully in '{category}'!",
            "success",
        )
    except Exception as e:
        flash(f"Error recording transaction: {str(e)}", "danger")

    return redirect(url_for("index"))


@app.route("/delete/<int:tx_id>", methods=["POST"])
def delete_transaction(tx_id):
    user_id = session.get("user_id", 1)
    success = database.delete_transaction(tx_id, user_id=user_id)
    if success:
        flash("Transaction deleted successfully.", "info")
    else:
        flash("Transaction not found or could not be deleted.", "warning")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
