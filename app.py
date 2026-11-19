import json
import sqlite3
from datetime import datetime, timezone

import streamlit as st
from openai import OpenAI
from anthropic import Anthropic

from hpu_core import prepare_request, evaluate_response, calculate_cost

APP_TITLE = "HPU — Native AI Integration Test"
DB_PATH = "hpu_integration_test.db"

st.set_page_config(page_title=APP_TITLE, page_icon=None, layout="wide")

def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            operation_type TEXT NOT NULL,
            language TEXT,
            prompt TEXT,
            response TEXT,
            status TEXT NOT NULL,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            input_rate_per_million REAL DEFAULT 0,
            output_rate_per_million REAL DEFAULT 0,
            estimated_cost REAL DEFAULT 0,
            cost_currency TEXT DEFAULT 'USD',
            evaluation TEXT
        )
    """)
    conn.commit()
    return conn

def save_operation(**kwargs):
    conn = db()
    fields = [
        "created_at", "provider", "model", "operation_type", "language",
        "prompt", "response", "status", "input_tokens", "output_tokens",
        "total_tokens", "input_rate_per_million", "output_rate_per_million",
        "estimated_cost", "cost_currency", "evaluation"
    ]
    values = [kwargs.get(k) for k in fields]
    conn.execute(
        f"INSERT INTO operations ({','.join(fields)}) VALUES ({','.join(['?']*len(fields))})",
        values
    )
    conn.commit()
    conn.close()

def call_provider(provider, api_key, model, system_prompt, user_prompt):
    if provider == "OpenAI":
        client = OpenAI(api_key=api_key)
        result = client.responses.create(
            model=model,
            instructions=system_prompt,
            input=user_prompt
        )
        text = result.output_text or ""
        usage = getattr(result, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0) if usage else 0
        return text, input_tokens, output_tokens

    client = Anthropic(api_key=api_key)
    result = client.messages.create(
        model=model,
        max_tokens=3000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )
    text = "\n".join(
        block.text for block in result.content if getattr(block, "type", None) == "text"
    )
    usage = getattr(result, "usage", None)
    input_tokens = int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0) if usage else 0
    return text, input_tokens, output_tokens

def get_key(provider):
    return st.session_state.get("openai_key" if provider == "OpenAI" else "anthropic_key", "").strip()

st.title(APP_TITLE)
st.caption("A separate test environment for connecting AI providers directly to HPU through their APIs.")

with st.sidebar:
    st.header("HPU Provider Gateway")
    provider = st.selectbox("AI provider", ["OpenAI", "Anthropic"])
    if provider == "OpenAI":
        key = st.text_input("OpenAI API key", type="password", key="openai_key",
                            help="Your key stays in this app session; do not share it.")
        model = st.text_input("Model ID", value="gpt-4.1-mini", key="openai_model")
    else:
        key = st.text_input("Anthropic API key", type="password", key="anthropic_key",
                            help="Your key stays in this app session; do not share it.")
        model = st.text_input("Model ID", value="claude-sonnet-4-5", key="anthropic_model")

    st.divider()
    st.subheader("Cost calculation rates")
    st.caption("Enter the rates that apply to your selected model. These are USD per 1 million tokens. Check the provider's current pricing before entering them.")
    input_rate = st.number_input("Input rate ($ / 1M tokens)", min_value=0.0, value=0.0, step=0.1, format="%.6f")
    output_rate = st.number_input("Output rate ($ / 1M tokens)", min_value=0.0, value=0.0, step=0.1, format="%.6f")
    st.caption("A zero rate means the app records usage but cannot calculate a meaningful cost.")

tab_generator, tab_history, tab_cost, tab_how = st.tabs(
    ["Generator", "Generation history", "Usage & cost", "How HPU works"]
)

with tab_generator:
    st.header("Natural-language production")
    st.write("Give HPU an instruction. HPU prepares the request, sends it to the selected AI provider, then checks the returned response.")
    col1, col2 = st.columns(2)
    with col1:
        operation_type = st.selectbox(
            "What are you creating?",
            ["LinkedIn post", "Article", "Report", "Interview analysis", "Research summary",
             "Campaign strategy", "Email", "Other"]
        )
        language = st.selectbox("Language", ["English", "Arabic", "French", "Other"])
    with col2:
        tone = st.selectbox("Tone", ["Professional", "Strategic", "Friendly", "Academic", "Persuasive", "Informative"])
        audience = st.text_input("Target audience", placeholder="e.g. business leaders, parents, students")

    context = st.text_area("Context or source material (optional)", height=130,
                           placeholder="Paste the information HPU should consider...")
    instruction = st.text_area("Your instruction", height=130,
                               placeholder="Describe exactly what you want HPU to produce...")
    generate = st.button("Generate with HPU", type="primary", use_container_width=True)

    if generate:
        if not key:
            st.error("Add the selected provider's API key in the sidebar first.")
        elif not instruction.strip():
            st.error("Enter an instruction before generating.")
        else:
            system_prompt, user_prompt = prepare_request(
                operation_type=operation_type,
                language=language,
                tone=tone,
                audience=audience,
                context=context,
                instruction=instruction
            )
            with st.spinner(f"HPU is sending the request to {provider}..."):
                try:
                    response_text, in_tokens, out_tokens = call_provider(
                        provider, key, model, system_prompt, user_prompt
                    )
                    evaluation = evaluate_response(response_text)
                    cost = calculate_cost(in_tokens, out_tokens, input_rate, output_rate)
                    status = "Completed" if evaluation["passed"] else "Needs review"
                    save_operation(
                        created_at=datetime.now(timezone.utc).isoformat(),
                        provider=provider, model=model, operation_type=operation_type,
                        language=language, prompt=user_prompt, response=response_text,
                        status=status, input_tokens=in_tokens, output_tokens=out_tokens,
                        total_tokens=in_tokens + out_tokens,
                        input_rate_per_million=input_rate,
                        output_rate_per_million=output_rate,
                        estimated_cost=cost, cost_currency="USD",
                        evaluation=json.dumps(evaluation)
                    )
                    st.session_state["last_response"] = response_text
                    st.session_state["last_prompt"] = user_prompt
                    st.session_state["last_provider"] = provider
                    st.session_state["last_model"] = model
                    st.session_state["last_usage"] = (in_tokens, out_tokens, cost)
                    st.session_state["last_evaluation"] = evaluation
                except Exception as exc:
                    st.error(f"Provider request failed: {exc}")

    if st.session_state.get("last_response"):
        st.divider()
        st.subheader("HPU result")
        st.write(st.session_state["last_response"])
        usage = st.session_state.get("last_usage", (0, 0, 0.0))
        m1, m2, m3 = st.columns(3)
        m1.metric("Input tokens", f"{usage[0]:,}")
        m2.metric("Output tokens", f"{usage[1]:,}")
        m3.metric("Estimated cost", f"${usage[2]:.6f}")
        ev = st.session_state.get("last_evaluation", {})
        if ev.get("passed"):
            st.success("HPU basic response check passed. Human review is still required.")
        else:
            st.warning("HPU recommends reviewing this response.")
        st.download_button(
            "Download result as Markdown",
            data=st.session_state["last_response"],
            file_name="hpu_generated_result.md",
            mime="text/markdown"
        )

        st.subheader("Revise the result")
        revision = st.text_area("Revision instruction", placeholder="e.g. Make it shorter and more evidence-based.")
        if st.button("Revise with selected provider"):
            if not key:
                st.error("Add the selected provider's API key in the sidebar first.")
            elif not revision.strip():
                st.error("Enter a revision instruction.")
            else:
                rev_system, rev_user = prepare_request(
                    operation_type="Revision",
                    language=language,
                    tone=tone,
                    audience=audience,
                    context=st.session_state["last_response"],
                    instruction=revision
                )
                try:
                    with st.spinner("Revising..."):
                        revised, in_t, out_t = call_provider(provider, key, model, rev_system, rev_user)
                    cost = calculate_cost(in_t, out_t, input_rate, output_rate)
                    evaluation = evaluate_response(revised)
                    save_operation(
                        created_at=datetime.now(timezone.utc).isoformat(),
                        provider=provider, model=model, operation_type="Revision",
                        language=language, prompt=rev_user, response=revised,
                        status="Completed" if evaluation["passed"] else "Needs review",
                        input_tokens=in_t, output_tokens=out_t, total_tokens=in_t+out_t,
                        input_rate_per_million=input_rate, output_rate_per_million=output_rate,
                        estimated_cost=cost, cost_currency="USD",
                        evaluation=json.dumps(evaluation)
                    )
                    st.session_state["last_response"] = revised
                    st.session_state["last_usage"] = (in_t, out_t, cost)
                    st.session_state["last_evaluation"] = evaluation
                    st.rerun()
                except Exception as exc:
                    st.error(f"Revision failed: {exc}")

with tab_history:
    st.header("Generation history")
    conn = db()
    rows = conn.execute("SELECT id, created_at, provider, model, operation_type, status, input_tokens, output_tokens, estimated_cost FROM operations ORDER BY id DESC LIMIT 100").fetchall()
    conn.close()
    if rows:
        st.dataframe([dict(r) for r in rows], use_container_width=True, hide_index=True)
        selected_id = st.number_input("Open operation ID", min_value=1, step=1)
        if st.button("Load operation"):
            conn = db()
            item = conn.execute("SELECT * FROM operations WHERE id=?", (int(selected_id),)).fetchone()
            conn.close()
            if item:
                st.subheader(f"Operation #{item['id']} — {item['operation_type']}")
                st.write(item["response"] or "No response stored.")
            else:
                st.warning("Operation ID not found.")
    else:
        st.info("No generations have been recorded yet.")

with tab_cost:
    st.header("AI usage & cost intelligence")
    st.caption("This dashboard reports usage captured from API responses by this test app. It is not the provider's official invoice.")
    conn = db()
    totals = conn.execute("""
        SELECT COUNT(*) AS operations,
               COALESCE(SUM(input_tokens),0) AS input_tokens,
               COALESCE(SUM(output_tokens),0) AS output_tokens,
               COALESCE(SUM(estimated_cost),0) AS estimated_cost
        FROM operations
    """).fetchone()
    by_provider = conn.execute("""
        SELECT provider, model, COUNT(*) AS operations,
               SUM(input_tokens) AS input_tokens,
               SUM(output_tokens) AS output_tokens,
               SUM(estimated_cost) AS estimated_cost
        FROM operations GROUP BY provider, model ORDER BY estimated_cost DESC
    """).fetchall()
    by_type = conn.execute("""
        SELECT operation_type, COUNT(*) AS operations,
               SUM(input_tokens + output_tokens) AS total_tokens,
               SUM(estimated_cost) AS estimated_cost
        FROM operations GROUP BY operation_type ORDER BY estimated_cost DESC
    """).fetchall()
    conn.close()
    a,b,c,d = st.columns(4)
    a.metric("Operations", f"{totals['operations']:,}")
    b.metric("Input tokens", f"{totals['input_tokens']:,}")
    c.metric("Output tokens", f"{totals['output_tokens']:,}")
    d.metric("Estimated cost", f"${totals['estimated_cost']:.6f}")
    st.subheader("By provider and model")
    if by_provider:
        st.dataframe([dict(r) for r in by_provider], use_container_width=True, hide_index=True)
        st.subheader("By operation type")
        st.dataframe([dict(r) for r in by_type], use_container_width=True, hide_index=True)
    else:
        st.info("Usage data will appear after the first successful API operation.")
    st.warning("For accurate cost estimates, enter the correct current model rates in the sidebar. This test app does not include image, audio, cached-token, web-search or other non-token charges.")

with tab_how:
    st.header("How HPU works")
    st.markdown("""
    1. **Receive:** HPU receives the user's task, context and requirements.
    2. **Prepare:** HPU structures the request and sends it to the selected provider.
    3. **Process:** The selected AI provider generates a response.
    4. **Evaluate:** HPU performs a basic response check (non-empty response and word count).
    5. **Record:** HPU stores the operation, provider, model, token usage and estimated cost.

    **Important boundaries**
    - HPU Core logic and the AI provider are separate.
    - The basic response check is not a full validation of factual accuracy or quality.
    - A human should review important outputs.
    - API keys are held in Streamlit session state in this test app; for production, use secure server-side secrets and a proper credential-management design.
    - ChatGPT subscriptions do not provide API credits. API usage is billed separately.
    """)
