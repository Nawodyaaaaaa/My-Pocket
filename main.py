"""
main.py - command-line interface for the My Pocket finance agent.

Run:  python main.py
      python main.py --model qwen3:4b
"""

import argparse
import logging
import os
from pathlib import Path

from agent.finance_agent import FinanceAgent, pick_model

BASE_DIR = Path(__file__).resolve().parent


def setup_logging():
    """Show the tool-call trace in the terminal AND save it to logs/agent.log."""
    (BASE_DIR / "logs").mkdir(exist_ok=True)
    fmt = logging.Formatter("%(asctime)s | %(message)s", "%H:%M:%S")

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("   [trace] %(message)s"))
    file = logging.FileHandler(BASE_DIR / "logs" / "agent.log", encoding="utf-8")
    file.setFormatter(fmt)

    log = logging.getLogger("agent")
    log.setLevel(logging.INFO)
    log.addHandler(console)
    log.addHandler(file)


def main():
    parser = argparse.ArgumentParser(description="My Pocket - personal finance agent (Ollama)")
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", ""),
                        help="Ollama model name. Default: first suitable model you already have.")
    args = parser.parse_args()
    args.model = pick_model(args.model)

    setup_logging()
    agent = FinanceAgent(model=args.model)

    print("=" * 60)
    print(f" My Pocket - Personal Finance Agent   (model: {args.model})")
    print(" Commands: /reset = clear memory, /exit = quit")
    print("=" * 60)

    while True:
        try:
            user = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if not user:
            continue
        if user.lower() in ("/exit", "exit", "quit"):
            print("Bye!")
            break
        if user.lower() == "/reset":
            agent.reset()
            print("Memory cleared.")
            continue

        try:
            answer = agent.chat(user)
        except Exception as e:  # e.g. Ollama not running
            answer = (f"Error talking to the model: {e}\n"
                      "Is Ollama running? Try: ollama serve  and  ollama pull " + args.model)
        print(f"\nMy Pocket: {answer}")


if __name__ == "__main__":
    main()
