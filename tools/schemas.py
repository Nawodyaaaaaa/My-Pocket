"""
schemas.py
----------
Describes each tool to the LLM in the JSON-schema format Ollama expects.
The model reads these descriptions to decide WHICH tool to call and
WHAT arguments to send. Good descriptions = better tool choices.
"""

from tools.finance_tools import CATEGORIES, RATES_TO_LKR

MONTH = {"type": "string", "description": "Month in YYYY-MM format, e.g. 2026-10"}
CATEGORY_OR_ALL = {"type": "string", "enum": CATEGORIES + ["all"],
                   "description": "Spending category, or 'all'"}


def _tool(name, description, properties, required):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }


TOOL_SCHEMAS = [
    _tool("add_expense",
          "Save a new expense in Sri Lankan Rupees (LKR). Use when the user says they spent money.",
          {
              "amount": {"type": "number", "description": "Amount in LKR, e.g. 1500"},
              "category": {"type": "string", "enum": CATEGORIES, "description": "Expense category"},
              "note": {"type": "string", "description": "Short description, e.g. 'lunch'"},
              "date_str": {"type": "string", "description": "YYYY-MM-DD. Leave empty for today."},
          },
          ["amount", "category"]),

    _tool("list_expenses",
          "List individual expenses for a month (newest first). Use to show details or find specific items.",
          {"month": MONTH, "category": CATEGORY_OR_ALL,
           "limit": {"type": "integer", "description": "How many to show (1-50)"}},
          ["month"]),

    _tool("get_spending_summary",
          "Get total spending for a month in LKR, with a breakdown by category.",
          {"month": MONTH, "category": CATEGORY_OR_ALL},
          ["month"]),

    _tool("convert_currency",
          "Convert an amount between currencies (mock fixed rates). Supported: " + ", ".join(RATES_TO_LKR),
          {"amount": {"type": "number", "description": "Amount to convert"},
           "from_currency": {"type": "string", "description": "3-letter code, e.g. LKR"},
           "to_currency": {"type": "string", "description": "3-letter code, e.g. USD"}},
          ["amount", "from_currency", "to_currency"]),

    _tool("check_budget",
          "Check spending against monthly budget limits. Shows if a category is over budget.",
          {"month": MONTH, "category": CATEGORY_OR_ALL},
          ["month"]),

    _tool("generate_report",
          "Create a monthly spending report text file in the reports folder.",
          {"month": MONTH},
          ["month"]),
]
