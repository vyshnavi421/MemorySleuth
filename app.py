"""MemorySleuth: a scripted concept prototype (no LLM, no real retrieval, no email)."""
import json

import streamlit as st

from core import (
    APPROVED_RECIPIENTS, GENESIS_HASH, MEMORIES, SCENARIOS, make_record, verify_chain,
)

st.set_page_config(page_title="MemorySleuth", page_icon="🔎", layout="wide")

st.title("🔎 MemorySleuth")
st.subheader("AI agent memory poisoning: investigation and forensic traceability")
st.caption("Scripted concept prototype · deterministic · not a live-LLM detector")
st.warning("Educational simulation only. No real emails or external actions are performed.")

if "ledger" not in st.session_state:
    st.session_state.ledger = []


def run_scenario(key: str) -> None:
    ledger = st.session_state.ledger
    prev = ledger[-1]["hash"] if ledger else GENESIS_HASH
    ledger.append(make_record(prev, SCENARIOS[key]))


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
    "The agent is a rule-based text parser that reads the retrieved memories. "
    "Which memories are retrieved is fixed per scenario."
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
        st.rerun()

st.divider()

# 3. Evidence ledger ----------------------------------------------------------
st.markdown("### 3. Evidence ledger")
ledger = st.session_state.ledger
if ledger:
    rows = [
        {
            "Time": r["time"],
            "Scenario": r["scenario"],
            "Retrieved": ", ".join(r["retrieved"]),
            "Proposed recipient": r["proposed"]["recipient"],
            "Decision": r["decision"],
            "Reason": r["reason"],
            "Candidate(s)": ", ".join(r["candidates"]) or "none",
            "Hash": r["hash"][:10],
        }
        for r in ledger
    ]
    st.dataframe(rows, width="stretch", hide_index=True)

    ok, bad = verify_chain(ledger)
    m1, m2, m3 = st.columns(3)
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
    st.download_button(
        "Download ledger (JSON)",
        data=json.dumps(ledger, indent=2),
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
**Implemented:** a rule-based agent that reads memory text; a deny-by-default policy
gate that sees only the proposed action (approved recipients: `{", ".join(sorted(APPROVED_RECIPIENTS))}`);
leave-one-out replay; a hash-chained, in-session ledger with an integrity check and JSON export.

**Scripted or simulated:** which memories are retrieved, the trust labels, the memory
contents. There is no LLM, no real retrieval, and no automated detection.

**Known limits:** the gate checks the recipient only, so scenario C is allowed. The
ledger lives in the browser session. The gate runs in the same process as the agent, so
its independence is a design principle, not deployment isolation.
"""
    )
