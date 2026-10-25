"""Agent tests with a scripted (fake) model, so no Ollama is needed."""

import shutil
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import agent.finance_agent as fa  # noqa: E402
from ollama import Message  # noqa: E402
import tools.finance_tools as ft  # noqa: E402


@pytest.fixture(autouse=True)
def temp_data(tmp_path, monkeypatch):
    """Use a copy of the data, so real demo runs can't change the test results."""
    shutil.copy(ft.EXPENSES_FILE, tmp_path / "expenses.json")
    shutil.copy(ft.BUDGETS_FILE, tmp_path / "budgets.json")
    monkeypatch.setattr(ft, "EXPENSES_FILE", tmp_path / "expenses.json")
    monkeypatch.setattr(ft, "BUDGETS_FILE", tmp_path / "budgets.json")


def test_finds_tool_call_written_as_text():
    text = ('To convert, I will first get the summary. '
            '{"name": "get_spending_summary", "parameters": {"category": "food", "month": "2026-10"}}')
    assert fa.find_text_tool_calls(text) == [
        ("get_spending_summary", {"category": "food", "month": "2026-10"})]


def test_ignores_normal_text_and_unknown_tools():
    assert fa.find_text_tool_calls("You spent Rs. 30,440 {not json}") == []
    assert fa.find_text_tool_calls('{"name": "delete_everything", "parameters": {}}') == []


def test_loop_runs_text_tool_call(monkeypatch):
    replies = [
        Message(role="assistant", content='{"name": "get_spending_summary", '
                '"parameters": {"category": "food", "month": "2026-10"}}'),
        Message(role="assistant", content="You spent Rs. 30,440 on food."),
    ]
    monkeypatch.setattr(fa.ollama, "chat", lambda **k: types.SimpleNamespace(message=replies.pop(0)))
    agent = fa.FinanceAgent()
    answer = agent.chat("food this month?")
    assert answer == "You spent Rs. 30,440 on food."
    assert agent.last_trace[0]["tool"] == "get_spending_summary"
    expected = ft.get_spending_summary("2026-10", "food")["total_lkr"]
    assert agent.last_trace[0]["result"]["total_lkr"] == expected
