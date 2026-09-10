# 💰 FinTrack — Expense Tracker Web Application

A clean, modern, and responsive **Expense Tracker** web application built with **Python (Flask)**, **SQLite**, and **Bootstrap 5**. The application empowers users to effortlessly log income and expenses, monitor real-time balance calculations, inspect categorized breakdowns, and manage their transaction history with an intuitive user interface.

---

## ✨ Features

### 1. ➕ Add Transactions
- **Dual-Mode Selector**: Quickly switch between **Income** and **Expense** with animated segmented controls.
- **Dynamic Category Presets**: Category quick-pick pills update automatically depending on the selected transaction type (e.g., *Salary*, *Freelance*, *Investments* for Income; *Food*, *Rent*, *Groceries*, *Utilities* for Expense).
- **Custom Category Support**: Type any custom category or click a preset pill to autofill.
- **Amount & Date Input**: Numeric input with validation, and an automatic date picker pre-filled with today's date.
- **Optional Notes**: Attach contextual descriptions (e.g., *“Client invoice #102”* or *“Weekly grocery run”*).

### 2. 🛡️ Robust Validation
- **Mandatory Fields**: Type, Category, Amount, and Date are strictly enforced.
- **Positive Amounts Only**: Amounts must be numerical and strictly greater than `0`.
- **Dual-Layer Validation**:
  - **Client-Side**: Instant Bootstrap feedback styling on submit.
  - **Server-Side**: Flask flash alerts with clear danger banners to prevent bypass.

### 3. 📊 Real-Time Financial Summary
- **Total Income**: Sum of all recorded earnings with vibrant emerald indicators.
- **Total Expense**: Sum of all recorded spendings with alert rose indicators.
- **Current Balance**: Automatically computed as `Total Income - Total Expense`, color-coded dynamically (positive cash flow in indigo/green, negative cash flow in red).
- **Visual Ratio Bar**: Visual income-to-expense percentage breakdown bar.

### 4. 📜 Transaction History & Management
- **Detailed Log Table**: Shows Date, Transaction Type badge, Category tag, formatted Currency (`+$X.XX` or `-$X.XX`), and optional note.
- **Filters & Search**:
  - Filter tabs for **All**, **Income**, and **Expense**.
  - Search bar to filter by category keywords or note text.
- **Safe Deletion**: Deleting transactions triggers a confirmation modal to avoid accidental loss.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.x, Flask
- **Database**: SQLite3 (persisted to `expense_tracker.db`)
- **Frontend / Styling**:
  - HTML5 & CSS3 (Custom responsive stylesheet with glassmorphic cards and soft shadows)
  - [Bootstrap 5.3](https://getbootstrap.com/)
  - [Bootstrap Icons 1.11](https://icons.getbootstrap.com/)
  - [Google Fonts (Plus Jakarta Sans)](https://fonts.google.com/specimen/Plus+Jakarta+Sans)
- **Testing**: Python `unittest` suite with temporary database isolation

---

## 📁 Project Structure

```
ExpenseTracker/
├── app.py                 # Flask app, routing, request validation, flash notifications
├── database.py            # SQLite database schema, queries, and summary calculations
├── requirements.txt       # Python dependencies (Flask)
├── test_app.py            # Automated test suite (database operations & route checks)
├── README.md              # Project documentation
├── static/
│   ├── css/
│   │   └── style.css      # Custom styling, card elevations, badges, and animations
│   └── js/
│       └── main.js        # Dynamic category presets, client-side validation, date autofill
└── templates/
    ├── base.html          # Base layout template with navbar, alerts container, and footer
    └── index.html         # Unified dashboard: Stat cards, entry form, and transaction table
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9 or higher installed on your system.

### 1. Clone or Open the Repository
```bash
cd ExpenseTracker
```

### 2. Create and Activate a Virtual Environment
- **Windows (PowerShell / Command Prompt)**:
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\activate
  ```
- **macOS / Linux**:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🧪 Running Automated Tests

A comprehensive unit test suite is included in `test_app.py` covering database initialization, transaction insertion, calculation accuracy, boundary validations (e.g. `<= 0` amount), and record deletion.

Run tests using:
```bash
python -m unittest test_app.py
```

Expected output:
```
......
----------------------------------------------------------------------
Ran 6 tests in 0.32s

OK
```

---

## 💡 Database Details

The application creates an SQLite file named `expense_tracker.db` in the project root on initial run.

### Schema:
```sql
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK(type IN ('Income', 'Expense')),
    category TEXT NOT NULL,
    amount REAL NOT NULL CHECK(amount > 0),
    date TEXT NOT NULL,
    note TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
```

---

## 📝 License
This project is open-source and free to use for personal and educational purposes.
