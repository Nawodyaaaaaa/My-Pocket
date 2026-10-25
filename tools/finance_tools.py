"""
finance_tools.py
----------------
The 6 tools the agent can call. Each tool:
  - is a normal Python function with type hints + docstring
  - validates its inputs
  - NEVER crashes: it returns {"ok": False, "error": "..."} on bad input
  - returns a dict that gets turned into JSON and sent back to the model

Persistent data lives in data/expenses.json and data/budgets.json.
"""

import json
from datetime import date, datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
EXPENSES_FILE = DATA_DIR / "expenses.json"
BUDGETS_FILE = DATA_DIR / "budgets.json"

CATEGORIES = ["food", "transport", "bills", "shopping",
              "entertainment", "health", "education", "other"]

# Mock exchange rates: how many LKR = 1 unit of the currency.
# (Realistic values, but fixed — this is a mock, not a live API.)
RATES_TO_LKR = {
    "LKR": 1.0,
    "USD": 300.0,
    "EUR": 325.0,
    "GBP": 385.0,
    "INR": 3.6,
    "AUD": 195.0,
    "JPY": 2.0,
}


# ---------------------------------------------------------------- helpers
def _load_json(path: Path, default):
    """Read a JSON file. If it is missing or broken, return the default."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _error(msg: str) -> dict:
    return {"ok": False, "error": msg}


def _check_month(month: str):
    """Return an error message if month is not 'YYYY-MM', else None."""
    try:
        datetime.strptime(str(month), "%Y-%m")
        return None
    except ValueError:
        return f"Invalid month '{month}'. Use the format YYYY-MM, e.g. 2026-10."


def _check_category(category: str, allow_all: bool = False):
    valid = CATEGORIES + (["all"] if allow_all else [])
    if str(category).lower() not in valid:
        return f"Unknown category '{category}'. Valid categories: {', '.join(valid)}."
    return None


def _to_amount(amount):
    """Small models sometimes send numbers as text ("1,500"). Clean it up."""
    try:
        value = float(str(amount).replace(",", "").replace("Rs.", "").replace("Rs", "").strip())
    except ValueError:
        return None
    return value


# ------------------------------------------------------------------ tools
def add_expense(amount: float, category: str, note: str = "", date_str: str = "") -> dict:
    """Save a new expense (in LKR) to the expenses file.

    Args:
        amount: Amount spent in Sri Lankan My Pockets. Must be > 0.
        category: One of food, transport, bills, shopping, entertainment, health, education, other.
        note: Short description, e.g. "lunch at canteen".
        date_str: Date as YYYY-MM-DD. Empty means today.
    """
    value = _to_amount(amount)
    if value is None or value <= 0:
        return _error(f"Amount must be a positive number, got '{amount}'.")
    if value > 10_000_000:
        return _error("Amount looks too large (over Rs. 10 million). Please check it.")

    err = _check_category(category)
    if err:
        return _error(err)

    if not date_str:
        date_str = date.today().isoformat()
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return _error(f"Invalid date '{date_str}'. Use YYYY-MM-DD.")

    expenses = _load_json(EXPENSES_FILE, [])
    new_id = max((e["id"] for e in expenses), default=0) + 1
    expense = {
        "id": new_id,
        "date": date_str,
        "amount": round(value, 2),
        "category": category.lower(),
        "note": str(note)[:100],
    }
    expenses.append(expense)
    _save_json(EXPENSES_FILE, expenses)
    return {"ok": True, "message": "Expense saved.", "expense": expense}


def list_expenses(month: str, category: str = "all", limit: int = 10) -> dict:
    """List individual expenses for a month, newest first.

    Args:
        month: Month as YYYY-MM.
        category: A category name, or "all".
        limit: Max number of expenses to return (1-50).
    """
    err = _check_month(month) or _check_category(category, allow_all=True)
    if err:
        return _error(err)
    try:
        limit = max(1, min(50, int(limit)))
    except (ValueError, TypeError):
        limit = 10

    expenses = [e for e in _load_json(EXPENSES_FILE, []) if e["date"].startswith(month)]
    if category.lower() != "all":
        expenses = [e for e in expenses if e["category"] == category.lower()]
    expenses.sort(key=lambda e: e["date"], reverse=True)
    return {"ok": True, "month": month, "category": category.lower(),
            "count": len(expenses), "expenses": expenses[:limit]}


def get_spending_summary(month: str, category: str = "all") -> dict:
    """Total spending for a month, broken down by category (amounts in LKR).

    Args:
        month: Month as YYYY-MM.
        category: A category name, or "all" for every category.
    """
    err = _check_month(month) or _check_category(category, allow_all=True)
    if err:
        return _error(err)

    expenses = [e for e in _load_json(EXPENSES_FILE, []) if e["date"].startswith(month)]
    if not expenses:
        return {"ok": True, "month": month, "total_lkr": 0,
                "message": f"No expenses recorded for {month}."}

    by_category = {}
    for e in expenses:
        by_category[e["category"]] = by_category.get(e["category"], 0) + e["amount"]

    if category.lower() != "all":
        total = by_category.get(category.lower(), 0)
        count = sum(1 for e in expenses if e["category"] == category.lower())
        return {"ok": True, "month": month, "category": category.lower(),
                "total_lkr": round(total, 2), "number_of_expenses": count}

    by_category = dict(sorted(by_category.items(), key=lambda kv: kv[1], reverse=True))
    return {"ok": True, "month": month,
            "total_lkr": round(sum(by_category.values()), 2),
            "number_of_expenses": len(expenses),
            "by_category_lkr": {k: round(v, 2) for k, v in by_category.items()},
            "top_category": next(iter(by_category))}


def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    """Convert money between currencies using fixed mock rates.

    Args:
        amount: The amount to convert.
        from_currency: 3-letter code, e.g. LKR.
        to_currency: 3-letter code, e.g. USD.
    """
    value = _to_amount(amount)
    if value is None or value < 0:
        return _error(f"Amount must be a non-negative number, got '{amount}'.")
    src, dst = str(from_currency).upper(), str(to_currency).upper()
    for code in (src, dst):
        if code not in RATES_TO_LKR:
            return _error(f"Unsupported currency '{code}'. Supported: {', '.join(RATES_TO_LKR)}.")

    in_lkr = value * RATES_TO_LKR[src]
    result = in_lkr / RATES_TO_LKR[dst]
    return {"ok": True, "amount": value, "from": src, "to": dst,
            "result": round(result, 2),
            "rate_used": f"1 {dst} = {RATES_TO_LKR[dst] / RATES_TO_LKR[src]:.4f} {src}",
            "note": "Mock rates for demo purposes, not live market data."}


def check_budget(month: str, category: str = "all") -> dict:
    """Compare spending against the monthly budget limits.

    Args:
        month: Month as YYYY-MM.
        category: A category name, or "all" to check every budgeted category.
    """
    err = _check_month(month) or _check_category(category, allow_all=True)
    if err:
        return _error(err)

    budgets = _load_json(BUDGETS_FILE, {})
    if not budgets:
        return _error("No budgets found. Add limits to data/budgets.json.")

    summary = get_spending_summary(month)
    spent = summary.get("by_category_lkr", {})

    cats = list(budgets) if category.lower() == "all" else [category.lower()]
    results = []
    for cat in cats:
        if cat not in budgets:
            results.append({"category": cat, "status": "no budget set",
                            "spent_lkr": spent.get(cat, 0)})
            continue
        limit = budgets[cat]
        used = spent.get(cat, 0)
        pct = round(used / limit * 100, 1) if limit else 0
        status = "OVER budget" if used > limit else ("warning (80%+ used)" if pct >= 80 else "ok")
        results.append({"category": cat, "budget_lkr": limit, "spent_lkr": round(used, 2),
                        "remaining_lkr": round(limit - used, 2),
                        "percent_used": pct, "status": status})

    over = [r["category"] for r in results if r.get("status") == "OVER budget"]
    return {"ok": True, "month": month, "results": results, "over_budget": over}


def generate_report(month: str) -> dict:
    """Write a monthly spending report to reports/report_YYYY-MM.txt.

    Args:
        month: Month as YYYY-MM.
    """
    err = _check_month(month)
    if err:
        return _error(err)

    summary = get_spending_summary(month)
    if summary.get("total_lkr", 0) == 0:
        return _error(f"No expenses for {month}, so there is nothing to report.")
    budget = check_budget(month)
    usd = convert_currency(summary["total_lkr"], "LKR", "USD")

    lines = [
        f"MONTHLY SPENDING REPORT - {month}",
        "=" * 42,
        f"Total spent : Rs. {summary['total_lkr']:,.2f}  (~USD {usd['result']:,.2f})",
        f"Expenses    : {summary['number_of_expenses']}",
        f"Top category: {summary['top_category']}",
        "",
        "BY CATEGORY",
        "-" * 42,
    ]
    total = summary["total_lkr"]
    for cat, amt in summary["by_category_lkr"].items():
        bar = "#" * int(amt / total * 30)
        lines.append(f"{cat:<14} Rs. {amt:>10,.2f}  {bar}")

    lines += ["", "BUDGET CHECK", "-" * 42]
    for r in budget.get("results", []):
        if "budget_lkr" in r:
            lines.append(f"{r['category']:<14} {r['percent_used']:>6}% of Rs. {r['budget_lkr']:,.0f}  [{r['status']}]")
    lines += ["", f"Generated: {datetime.now():%Y-%m-%d %H:%M}"]

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"report_{month}.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    return {"ok": True, "message": "Report written.", "file": str(path.relative_to(BASE_DIR)),
            "total_lkr": total, "over_budget": budget.get("over_budget", [])}


# --------------------------------------------- registry used by the agent
TOOL_FUNCTIONS = {
    "add_expense": add_expense,
    "list_expenses": list_expenses,
    "get_spending_summary": get_spending_summary,
    "convert_currency": convert_currency,
    "check_budget": check_budget,
    "generate_report": generate_report,
}
