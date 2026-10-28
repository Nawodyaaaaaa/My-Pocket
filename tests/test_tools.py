"""
Tool tests - run with:  python -m pytest tests -v
These test the tools directly (no LLM needed), including bad inputs.
Each test uses a temporary copy of the data so real data is not changed.
"""

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tools.finance_tools as ft  # noqa: E402


@pytest.fixture(autouse=True)
def temp_data(tmp_path, monkeypatch):
    shutil.copy(ft.EXPENSES_FILE, tmp_path / "expenses.json")
    shutil.copy(ft.BUDGETS_FILE, tmp_path / "budgets.json")
    monkeypatch.setattr(ft, "EXPENSES_FILE", tmp_path / "expenses.json")
    monkeypatch.setattr(ft, "BUDGETS_FILE", tmp_path / "budgets.json")
    monkeypatch.setattr(ft, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(ft, "BASE_DIR", tmp_path)


def test_add_expense_saves_to_file():
    before = ft.get_spending_summary("2026-10", "food")["total_lkr"]
    r = ft.add_expense(1500, "food", "lunch", "2026-10-24")
    assert r["ok"]
    after = ft.get_spending_summary("2026-10", "food")["total_lkr"]
    assert after == before + 1500


def test_add_expense_accepts_text_amount():
    assert ft.add_expense("1,500", "food", "lunch")["ok"]


@pytest.mark.parametrize("amount", [-50, 0, "abc"])
def test_add_expense_rejects_bad_amount(amount):
    r = ft.add_expense(amount, "food")
    assert not r["ok"] and "Amount" in r["error"]


def test_bad_category_and_month():
    assert not ft.add_expense(100, "pizza")["ok"]
    assert not ft.get_spending_summary("October")["ok"]


def test_summary_empty_month():
    r = ft.get_spending_summary("2020-01")
    assert r["ok"] and r["total_lkr"] == 0


def test_convert_currency():
    r = ft.convert_currency(30000, "LKR", "USD")
    assert r["ok"] and r["result"] == 100.0
    assert not ft.convert_currency(100, "LKR", "XYZ")["ok"]


def test_check_budget_flags_over():
    r = ft.check_budget("2026-10")
    assert r["ok"] and "food" in r["over_budget"]


def test_generate_report_writes_file():
    r = ft.generate_report("2026-10")
    assert r["ok"]
    assert (ft.BASE_DIR / r["file"]).exists()



def test_convert_to_euro():
    r = ft.convert_currency(32500, "LKR", "EUR")
    assert r["ok"] and r["result"] == 100.0


def test_convert_to_pound():
    r = ft.convert_currency(38500, "LKR", "GBP")
    assert r["ok"] and r["result"] == 100.0


def test_list_expenses_newest_first():
    r = ft.list_expenses("2026-10", "food", 5)
    dates = [e["date"] for e in r["expenses"]]
    assert r["ok"] and dates == sorted(dates, reverse=True)

