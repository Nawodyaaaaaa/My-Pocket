"""
app.py - web chat screen for the My Pocket finance agent (Streamlit).

Run:  streamlit run app.py
"""

import logging

import streamlit as st

from agent.finance_agent import FinanceAgent, installed_models, pick_model
from tools.finance_tools import check_budget, get_spending_summary
from datetime import date

logging.basicConfig(level=logging.INFO, format="[trace] %(message)s")

st.set_page_config(page_title="My Pocket - Finance Agent", page_icon="💰", layout="wide")

# ------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("💰 My Pocket")
    st.caption("Personal finance agent · local LLM via Ollama")

    models = installed_models()
    if not models:
        st.error("Ollama is not running or has no models.\n\nStart Ollama, then refresh.")
        st.stop()
    default = pick_model()
    model = st.selectbox("Model (already installed)", models, index=models.index(default))

    show_trace = st.toggle("Show tool-call trace", value=True)

    # Auto demo: plays the video script by itself, one prompt after another
    DEMO = [
        "How much did I spend this month, and what's my biggest category?",
        "How much did I spend on food this month in USD, and am I over budget?",
        "What about in euros?",
        "I spent 1500 My Pockets on lunch today. Add it, then make this month's report.",
        "Add an expense of -500 for pizza",
    ]
    if st.button("▶️ Run full demo", type="primary", use_container_width=True):
        st.session_state.pop("agent", None)
        st.session_state.demo_queue = list(DEMO)
        st.rerun()
    if st.button("🗑️ Clear chat memory", use_container_width=True):
        st.session_state.pop("agent", None)
        st.session_state.pop("history", None)
        st.rerun()

    # live snapshot of this month (reads the JSON directly, no LLM)
    month = f"{date.today():%Y-%m}"
    st.divider()
    st.subheader(f"This month ({month})")
    s = get_spending_summary(month)
    st.metric("Total spent", f"Rs. {s.get('total_lkr', 0):,.0f}")
    for r in check_budget(month).get("results", []):
        if "budget_lkr" in r:
            pct = min(r["percent_used"] / 100, 1.0)
            icon = "🔴" if r["status"] == "OVER budget" else ("🟠" if pct >= 0.8 else "🟢")
            st.progress(pct, text=f"{icon} {r['category']}: {r['percent_used']}%")

# ------------------------------------------------------------- state
if "agent" not in st.session_state or st.session_state.agent.model != model:
    st.session_state.agent = FinanceAgent(model=model)
    st.session_state.history = []
agent = st.session_state.agent
history = st.session_state.history


def render_trace(trace):
    if not trace or not show_trace:
        return
    with st.expander(f"🔧 Agent used {len(trace)} tool call(s)", expanded=False):
        for t in trace:
            st.markdown(f"**Step {t['step']} → `{t['tool']}`**")
            st.json({"arguments": t["args"], "result": t["result"]}, expanded=False)


# ------------------------------------------------------------- chat
st.header("Ask about your spending")

if not history:
    st.info("Try one of these:")
    examples = [
        "How much did I spend this month, and what's my biggest category?",
        "How much did I spend on food this month in USD, and am I over budget?",
        "I spent 1500 My Pockets on lunch today. Add it, then make this month's report.",
    ]
    cols = st.columns(3)
    for col, ex in zip(cols, examples):
        if col.button(ex, use_container_width=True):
            st.session_state.pending = ex
            st.rerun()

for h in history:
    with st.chat_message(h["role"], avatar="🧑" if h["role"] == "user" else "💰"):
        st.markdown(h["content"])
        render_trace(h.get("trace"))

prompt = st.chat_input("e.g. Am I over budget on transport?") or st.session_state.pop("pending", None)
if not prompt and st.session_state.get("demo_queue"):
    import time
    time.sleep(2)  # short pause so viewers can read the previous answer
    prompt = st.session_state.demo_queue.pop(0)
if prompt:
    history.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(prompt)
    with st.chat_message("assistant", avatar="💰"):
        with st.spinner("Thinking and calling tools..."):
            try:
                answer = agent.chat(prompt)
            except Exception as e:
                answer = f"⚠️ Error talking to the model: {e}"
        st.markdown(answer)
        render_trace(agent.last_trace)
    history.append({"role": "assistant", "content": answer, "trace": list(agent.last_trace)})
    st.rerun()  # refresh sidebar numbers after new expenses
