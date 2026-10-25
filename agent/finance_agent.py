"""
finance_agent.py
----------------
The agent loop:

    user message
        -> send history + tools to the model
        -> model either answers, OR asks for tool(s)
        -> we run each tool, add the result to history
        -> send again ... repeat until a final answer (or MAX_STEPS)

The `messages` list is the conversation memory. It is kept between
turns, so follow-up questions ("now in euros") work.
"""

import json
import logging
from datetime import date

import ollama

from tools.finance_tools import TOOL_FUNCTIONS
from tools.schemas import TOOL_SCHEMAS

MAX_STEPS = 8  # safety limit: stops infinite tool-calling loops

log = logging.getLogger("agent")


def build_system_prompt() -> str:
    today = date.today()
    return f"""You are My Pocket, a personal finance assistant for a user in Sri Lanka.
Today is {today.isoformat()}. The current month is {today:%Y-%m}.

RULES
- All money is stored in Sri Lankan My Pockets (LKR). Write amounts like "Rs. 12,500".
- ALWAYS use tools to get numbers. Never guess or invent amounts.
- If a question needs several steps, call tools one after another
  (e.g. get_spending_summary -> convert_currency -> check_budget).
- "This month" means {today:%Y-%m}. "Last month" means the month before it.
- If a tool returns an error, explain it simply or fix the arguments and retry once.
- If the request is unclear (e.g. no amount given), ask the user instead of guessing.
- You do not make real payments or bank transfers. You only track and analyse.

OUTPUT FORMAT
- Short and clear. Use bullet points for breakdowns.
- End with one practical tip when the user is over or close to a budget."""


def installed_models() -> list:
    """Names of the models already downloaded in Ollama (no new download needed)."""
    try:
        return [m.model for m in ollama.list().models]
    except Exception:
        return []


def pick_model(preferred: str = "") -> str:
    """Use the preferred model if installed, otherwise the first installed one."""
    models = installed_models()
    if preferred and (preferred in models or f"{preferred}:latest" in models):
        return preferred
    # prefer models known to support tool calling
    for good in ("qwen3", "qwen2.5", "llama3.2", "llama3.1", "mistral", "granite3"):
        for m in models:
            if m.startswith(good):
                return m
    return models[0] if models else (preferred or "llama3.2")


class FinanceAgent:
    def __init__(self, model: str = "llama3.2"):
        self.model = model
        self.messages = [{"role": "system", "content": build_system_prompt()}]
        self.last_trace = []  # tool calls from the latest request (shown in the UI)

    def reset(self):
        """Clear memory but keep the system prompt."""
        self.messages = self.messages[:1]

    def run_tool(self, name: str, args: dict) -> dict:
        """Execute one tool safely. Unknown tools / bad args never crash the app."""
        func = TOOL_FUNCTIONS.get(name)
        if func is None:
            return {"ok": False, "error": f"Unknown tool '{name}'."}
        try:
            return func(**args)
        except TypeError as e:  # wrong / missing argument names
            return {"ok": False, "error": f"Bad arguments for {name}: {e}"}
        except Exception as e:  # last-resort safety net
            return {"ok": False, "error": f"{name} failed: {e}"}

    def chat(self, user_input: str) -> str:
        """Handle one user message and return the agent's final answer."""
        self.messages.append({"role": "user", "content": user_input})
        self.last_trace = []

        for step in range(1, MAX_STEPS + 1):
            # 1. Ask the model what to do next
            response = ollama.chat(model=self.model, messages=self.messages, tools=TOOL_SCHEMAS)
            msg = response.message
            self.messages.append(msg)  # keep the model's turn in memory

            # 2. No tool requested -> this is the final answer
            if not msg.tool_calls:
                log.info("STEP %d | final answer", step)
                return msg.content

            # 3. Run every tool the model asked for
            for call in msg.tool_calls:
                name = call.function.name
                args = call.function.arguments or {}
                log.info("STEP %d | CALL   %s(%s)", step, name, json.dumps(args, ensure_ascii=False))

                result = self.run_tool(name, args)
                log.info("STEP %d | RESULT %s", step, json.dumps(result, ensure_ascii=False))
                self.last_trace.append({"step": step, "tool": name, "args": args, "result": result})

                # 4. Feed the result back so the model can use it
                self.messages.append({
                    "role": "tool",
                    "tool_name": name,
                    "content": json.dumps(result, ensure_ascii=False),
                })
            # loop again -> model sees the tool results

        log.warning("Stopped after %d steps (MAX_STEPS reached)", MAX_STEPS)
        return "Sorry, that took too many steps. Please try a simpler or more specific question."
