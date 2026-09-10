import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
import database

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "expense-tracker-secret-key-2026")

# Ensure database is initialized
database.init_db()


@app.template_filter("format_currency")
def format_currency(value):
    """Format a numeric value into Rupees currency format (₹)."""
    try:
        val = float(value)
        return f"₹{val:,.2f}"
    except (ValueError, TypeError):
        return "₹0.00"


@app.context_processor
def inject_context():
    """Inject dynamic time-of-day greeting into all Jinja templates."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        greeting = "Good morning!"
    elif 12 <= hour < 17:
        greeting = "Good afternoon!"
    elif 17 <= hour < 22:
        greeting = "Good evening!"
    else:
        greeting = "Good night!"
    return dict(greeting=greeting)




@app.route("/", methods=["GET"])
def index():
    filter_type = request.args.get("type", "").strip()
    search_query = request.args.get("search", "").strip()

    transactions = database.get_all_transactions(
        filter_type=filter_type if filter_type in ("Income", "Expense") else None,
        search_query=search_query if search_query else None,
    )
    summary = database.get_financial_summary()
    breakdown = database.get_category_breakdown()

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

    analytics = database.get_analytics_summary(timeframe=timeframe, target_period=target_period)

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
    success = database.delete_transaction(tx_id)
    if success:
        flash("Transaction deleted successfully.", "info")
    else:
        flash("Transaction not found or could not be deleted.", "warning")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
