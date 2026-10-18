"""MemorySleuth: scripted concept prototype with an optional live-LLM agent (no real retrieval, no email)."""
import json
import os

import streamlit as st

from core import (
    APPROVED_RECIPIENTS, GENESIS_HASH, MEMORIES, SCENARIOS, make_record, strict_policy_gate,
    verify_chain,
)
from llm_agent import DEFAULT_MODEL, make_anthropic_client, make_llm_agent

st.set_page_config(page_title="MemorySleuth", page_icon="🔎", layout="wide")

st.title("🔎 MemorySleuth")
st.subheader("AI agent memory poisoning: investigation and forensic traceability")
with st.sidebar:
    st.markdown("### Policy gate")
    strict = st.toggle("Strict policy", value=False,
                       help="Also blocks any extra text added to the report. Closes the "
                            "scenario C blind spot. Off by default (standard gate).")
    st.markdown("### Agent")
    use_llm = st.toggle("Use live LLM agent", value=False,
                        help="Default is the scripted rule-based agent. The LLM agent only "
                             "proposes an action; the policy gate and ledger are unchanged.")
    api_key = ""
    if use_llm:
        try:
            api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        except Exception:
            api_key = ""
        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            api_key = st.text_input("Anthropic API key", type="password",
                                    help="Kept in this browser session only; never written to the ledger.")
        model = st.text_input("Model", value=DEFAULT_MODEL)
        st.caption("Each scenario makes a handful of model calls (one run plus replays). "
                   "A single model call is one trial: influence, not causal proof.")

if use_llm:
    st.caption("Live LLM agent proposes the action · gate, replay and ledger unchanged · not a detector")
else:
    st.caption("Scripted concept prototype · deterministic · not a live-LLM detector")
st.warning("Educational simulation only. No real emails or external actions are performed.")

if "ledger" not in st.session_state:
    st.session_state.ledger = []
if "head" not in st.session_state:
    st.session_state.head = None  # head hash noted outside the ledger (the anchor)


def run_scenario(key: str) -> None:
    ledger = st.session_state.ledger
    prev = ledger[-1]["hash"] if ledger else GENESIS_HASH
    agent, name = None, "scripted"
    gate_kw = {"gate": strict_policy_gate, "gate_name": "strict"} if strict else {}
    if use_llm:
        if not api_key:
            st.error("Enter an Anthropic API key in the sidebar, or turn the LLM agent off.")
            return
        try:
            agent = make_llm_agent(make_anthropic_client(api_key), model)
            name = f"llm:{model}"
            with st.spinner("Asking the model and running replays..."):
                record = make_record(prev, SCENARIOS[key], seq=len(ledger) + 1,
                                     agent=agent, agent_name=name, **gate_kw)
        except Exception as exc:  # network, auth, quota: no ledger entry is written
            st.error(f"LLM call failed ({type(exc).__name__}). No ledger entry was written.")
            return
    else:
        record = make_record(prev, SCENARIOS[key], seq=len(ledger) + 1, **gate_kw)
    ledger.append(record)
    st.session_state.head = ledger[-1]["hash"]


# 1. Memory store -------------------------------------------------------------
st.markdown("### 1. Memory store")
st.caption("Trust labels are assigned by this demo. Nothing here detects poisoning.")
cols = st.columns(len(MEMORIES))
for col, mem in zip(cols, MEMORIES.values()):
    with col:
        (st.success if mem.trust == "trusted" else st.error)(
            f"{mem.id} | {mem.trust.upper()}"
        )
        st.code(mem.text, language=None)
        st.caption(f"Source: {mem.source} · sha256 {mem.digest}")

st.divider()

# 2. Run scenarios ------------------------------------------------------------
st.markdown("### 2. Run scenarios")
st.caption(
    "The agent (scripted rule-based parser by default, or a live LLM from the sidebar) reads "
    "the retrieved memories and only proposes an action. Which memories are retrieved is fixed per scenario."
)
b1, b2, b3, b4 = st.columns(4)
with b1:
    if st.button("🚨 A: Poisoned recipient", width="stretch"):
        run_scenario("A")
with b2:
    if st.button("🔁 B: Replay without MEM-002", width="stretch"):
        run_scenario("B")
with b3:
    if st.button("⚠️ C: Poisoned content (blind spot)", width="stretch"):
        run_scenario("C")
with b4:
    if st.button("🗑️ Clear ledger", width="stretch"):
        st.session_state.ledger = []
        st.session_state.head = None
        st.rerun()

st.divider()

# 3. Evidence ledger ----------------------------------------------------------
st.markdown("### 3. Evidence ledger")
ledger = st.session_state.ledger
if ledger:
    rows = [
        {
            "#": r["seq"],
            "Time (UTC)": r["time"],
            "Scenario": r["scenario"],
            "Agent": r.get("agent", "scripted"),
            "Policy": r.get("policy", "standard"),
            "Retrieved": ", ".join(r["retrieved"]),
            "Proposed recipient": r["proposed"]["recipient"],
            "Decision": r["decision"],
            "Reason": r["reason"],
            "Candidate(s)": ", ".join(r["candidates"])
            or ("group: " + ", ".join(r["group_candidates"]) if r["group_candidates"] else "none"),
            "Hash": r["hash"][:10],
        }
        for r in ledger
    ]
    st.dataframe(rows, width="stretch", hide_index=True)

    ok, bad = verify_chain(ledger)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Latest policy decision", ledger[-1]["decision"])
    m2.metric("Ledger integrity", "VALID" if ok else f"BROKEN at record {bad}")
    tampered = [dict(r) for r in ledger]
    tampered[0]["decision"] = "ALLOWED" if tampered[0]["decision"] == "BLOCKED" else "BLOCKED"
    t_ok, t_bad = verify_chain(tampered)
    m3.metric(
        "Check on a tampered copy",
        "Detected" if not t_ok else "Missed",
        help="Flips the decision in record 1 of a copy and re-verifies the hash chain.",
    )
    h_ok, _ = verify_chain(ledger[:-1], expected_head=st.session_state.head)
    m4.metric(
        "Check on a truncated copy",
        "Detected" if not h_ok else "Missed",
        help="Drops the last record of a copy. The chain alone cannot see this; "
        "it is caught only because the head hash was noted outside the ledger.",
    )
    st.caption(
        f"Head hash (note this outside the ledger): `{ledger[-1]['hash']}` · "
        f"{len(ledger)} record(s)"
    )
    st.download_button(
        "Download ledger (JSON)",
        data=json.dumps(
            {"head_hash": ledger[-1]["hash"], "record_count": len(ledger), "records": ledger},
            indent=2,
        ),
        file_name="memorysleuth_ledger.json",
        mime="application/json",
    )
else:
    st.info("Run a scenario above to generate evidence.")

# 4. Findings -----------------------------------------------------------------
st.markdown("### 4. Latest finding")
if ledger:
    last = ledger[-1]
    p = last["proposed"]
    st.write(
        f"**Proposed action:** send a {p['format']} report to `{p['recipient']}`"
        + (f' with the extra line "{p["extra_line"]}"' if p["extra_line"] else "")
        + f"\n\n**Policy gate:** {last['decision']} ({last['reason_code']}): {last['reason']}"
    )
    st.write(
        "**Leave-one-out replay:** memories whose removal changes the proposed action: "
        + (", ".join(last["influential"]) or "none")
        + ". Candidate for investigation (influential and untrusted): "
        + (", ".join(last["candidates"]) or "none")
        + "."
        + (
            " Group replay (all untrusted removed together) changes the action: "
            + ", ".join(last["group_candidates"]) + "."
            if last["group_candidates"] else ""
        )
    )
    if last["advisory"]:
        st.warning(last["advisory"])
    st.caption(
        "One deterministic run: a replay hint, not causal proof. "
        "A human decides whether to remove the memory or tighten policy."
    )
else:
    st.write("Findings appear here after a run.")

# 5. Scope --------------------------------------------------------------------
with st.expander("What is real and what is scripted"):
    st.markdown(
        f"""
**Implemented:** a rule-based agent that reads memory text, plus an optional live-LLM agent
(sidebar toggle) that proposes the action the same way; a deny-by-default policy
gate that sees only the proposed action (approved recipients: `{", ".join(sorted(APPROVED_RECIPIENTS))}`);
leave-one-out replay plus a joint-removal check for redundant poison; a hash-chained,
in-session ledger with an integrity check, memory-content digests, a head hash and JSON export.

**Scripted or simulated:** which memories are retrieved, the trust labels, the memory
contents. The default agent is scripted; there is no real retrieval and no automated
detection. With the LLM agent, a replay is a single trial of a non-deterministic model.

**Known limits:** the standard gate checks the recipient only, so scenario C is allowed (the optional strict policy blocks it, bluntly, by denying any extra report text). The
ledger lives in the browser session. A recomputed full rewrite, or deletion of the latest
records, is invisible to the chain alone; only a head hash stored elsewhere catches it, and
this demo keeps that anchor in the same session. The gate runs in the same process as the agent, so
its independence is a design principle, not deployment isolation.
"""
    )
