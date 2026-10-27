# My Pocket — Personal Finance Agent (Ollama)

An AI agent that tracks expenses in **Sri Lankan My Pockets (LKR)** and answers spending questions.
It runs a **local LLM through Ollama** and decides on its own which tools to call, in what order,
to reach an answer.

> Example: *"How much did I spend on food this month in USD, and am I over budget?"*
> → `get_spending_summary` → `convert_currency` → `check_budget` → final answer.

## Features
- 6 tools with typed parameters, descriptions, and input validation
- Persistent data in JSON (`data/expenses.json`, `data/budgets.json`)
- Agent loop with multiple tool calls per request and a `MAX_STEPS = 8` safety limit
- Conversation memory, so follow-up questions work ("now show that in euros")
- Step-by-step tool trace in the terminal, also saved to `logs/agent.log`
- No cloud APIs, no keys, no real payments (currency rates are a realistic mock)

## Project structure
```
finance-agent/
├── app.py                   # web chat screen (Streamlit)
├── main.py                  # CLI interface + logging setup
├── agent/
│   └── finance_agent.py     # system prompt + agent loop + memory
├── tools/
│   ├── finance_tools.py     # the 6 tool functions
│   └── schemas.py           # tool descriptions sent to the model
├── data/
│   ├── expenses.json        # sample expenses (Sep–Oct 2026)
│   └── budgets.json         # monthly budget limits per category
├── reports/                 # generated monthly reports
├── logs/                    # agent.log (tool-call trace)
└── tests/test_tools.py      # tool tests (no LLM needed)
```

## Tools
| Tool | Purpose | Parameters |
|---|---|---|
| `add_expense` | Save an expense (writes JSON) | amount, category, note, date_str |
| `list_expenses` | List expenses for a month | month, category, limit |
| `get_spending_summary` | Totals by category | month, category |
| `convert_currency` | LKR ↔ USD/EUR/GBP/INR/AUD/JPY (mock rates) | amount, from_currency, to_currency |
| `check_budget` | Compare spending vs budget limits | month, category |
| `generate_report` | Write `reports/report_YYYY-MM.txt` | month |

Categories: food, transport, bills, shopping, entertainment, health, education, other.

## Setup
1. **Install Ollama:** https://ollama.com/download
2. **Have any tool-calling model installed** (no new download needed if you already have one).
   The app picks one automatically: qwen3 / qwen2.5 / llama3.2 / llama3.1 / mistral first.
   If you have none: `ollama pull llama3.2`
3. **Install Python packages** (Python 3.9+):
   ```bash
   pip install -r requirements.txt
   ```

## Run
**Windows quick start:** double-click `START.bat`.

**Web screen (recommended):**
```bash
streamlit run app.py
```
Opens in your browser: chat window, example-prompt buttons, model picker, a tool-call trace
under every answer, and a live budget panel for the current month.
The **▶️ Run full demo** button plays 5 example tasks automatically (used for the demo video).

**Terminal version:**
```bash
python main.py                    # auto-picks an installed model
python main.py --model qwen3:4b   # or choose one
```
Commands inside the chat: `/reset` clears memory, `/exit` quits.

Run the tests:
```bash
python -m pytest tests -v
```

## Example prompts
1. `How much did I spend this month, and what's my biggest category?`
2. `How much did I spend on food in October in USD, and am I over budget?` *(multi-step)*
3. `I spent 1500 My Pockets on lunch today. Add it, then make my October report.` *(multi-step, writes files)*

Follow-up to show memory: after prompt 2, ask `What about in euros?`

## Model choice
**llama3.2 (3B, ~2 GB)**: supports tool calling and runs on a normal laptop with no GPU.
`qwen3:4b` also works and is often more reliable at choosing multi-step tool sequences.

## Credits
- [Ollama](https://ollama.com) and the [`ollama` Python library](https://github.com/ollama/ollama-python)
- AI coding assistants were used for help and debugging (see the report appendix).


## Team
| Member | Role |
|---|---|
| Sanjula Nawodya | Agent loop, system prompt, web UI, repository |
| Chamod Mihiranga | Tools: gifts category, SGD currency |
| Komul Harana | Testing: agent tests, currency and category tests |