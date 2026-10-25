"""Agent tests with a scripted (fake) model, so no Ollama is needed."""

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import agent.finance_agent as fa  # noqa: E402
from ollama import Message  # noqa: E402


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
    assert agent.last_trace[0]["result"]["total_lkr"] == 30440.0
