# 🔎 MemorySleuth

**Memory poisoning investigation for AI agents: guard the action, keep the evidence.**

> Once an agent's memory is poisoned, you can't trust the agent's own judgment. Enforcement and
> investigation have to sit **outside** the agent.

Built by Team HEXELLE (Vyshnavi, Abhishek) for the Mitigata CyberForge Hackathon 2026.
**Live demo:** https://memorysleuth-ktta2duyosxyjccycerhtg.streamlit.app/

> **Scope, stated plainly:** the default agent is a deterministic, scripted concept prototype. An
> optional live-LLM agent (sidebar toggle, your own API key) proposes the action through the same
> gate, replay and ledger. There is no real retrieval, no automated poisoning detection and no real
> email. Trust labels are assigned by the demo. It demonstrates an enforcement-and-evidence
> *workflow*; it is not a detector.

## What the demo shows

Four stored memories (two trusted, two from untrusted sources) feed a rule-based, scripted "agent"
that proposes a `send_report` action. A separate policy gate decides, and every run is written to a
hash-chained evidence ledger.

| Scenario | Retrieved memories | Proposed recipient | Gate | Candidate |
|---|---|---|---|---|
| **A**: poisoned recipient | MEM-001, 002, 003 | attacker@evil.test | **BLOCKED** | MEM-002 |
| **B**: replay without MEM-002 | MEM-001, 003 | finance@company.test | **ALLOWED** | none |
| **C**: poisoned *content* (known blind spot) | MEM-001, 003, 004 | finance@company.test | **ALLOWED** | MEM-004 (advisory) |

Scenario C is intentional. The gate checks the recipient only, so it allows a report whose text was
altered by untrusted memory. The ledger records the advisory, but nothing blocks it. We show this
limit instead of hiding it.

**Strict policy (optional sidebar toggle, off by default):** `strict_policy_gate` also denies any extra
report text, so scenario C is BLOCKED (`CONTENT_NOT_ALLOWED`) while A and B are unchanged. It is a
deliberately blunt allow-list, not a content classifier. Each ledger record names the policy used.

## What is implemented

- **Rule-based agent** (`propose_action`): reads memory text with simple patterns; later memories override earlier ones. This is the default.
- **Optional live-LLM agent** (`llm_agent.py`): the same pipeline with a real model as the agent. It only returns a proposed action as JSON; output is validated and fails closed, nothing is executed, and the gate never sees memory text or model reasoning. Each ledger record names the agent used (`scripted` or `llm:<model>`). With a real model, replay is a single trial and runs can differ, so it shows influence, not causal proof. Enable it in the sidebar and enter an Anthropic API key (or set `ANTHROPIC_API_KEY` / Streamlit secrets); `MEMORYSLEUTH_MODEL` overrides the default model.
- **Independent policy gate** (`policy_gate`): deny-by-default and fail-closed on malformed input; its function signature takes only the proposed action, never memory text. A unit test enforces that.
- **Leave-one-out replay** (`influence`): re-runs the agent with each memory removed. A memory is *influential* if that changes the action, and a *candidate* if it is also untrusted. A trusted, benign memory (MEM-003) can be influential without being flagged. A joint-removal check (`group_influence`) also flags untrusted memories whose *combined* removal changes the action, which catches poison planted twice.
- **Hash-chained ledger** (`make_record`, `verify_chain`): each record includes the previous record's hash, a sequence number, a UTC timestamp and the full SHA-256 of every retrieved memory's text, so the evidence is bound to what the memory said. The UI shows an integrity check, a tamper check and a truncation check on copies, the head hash, and JSON export.
- **Tests** (`tests/`, 29 tests; the LLM-agent tests use a fake client, so no API key or network is needed) cover the gate (including malformed input), the agent, all three scenarios, the benign control, memory digests, redundant poison, tamper detection, truncation and the recomputed-rewrite limit.

## Architecture

```mermaid
flowchart LR
    M["Memory store<br/>(source, trust, hash)"] --> R["Retrieval<br/>(fixed IDs per scenario)"]
    R --> A["Agent<br/>(rule-based parser)"]
    A --> P["Proposed action"]
    P --> G["Policy gate<br/>(sees only the action)"]
    G --> L["Evidence ledger<br/>(hash-chained)"]
    L --> I["Leave-one-out replay<br/>candidate memories"]
```

Scripted or simulated: memory store contents, trust labels, retrieval. Implemented: agent rules,
gate, leave-one-out replay, ledger.

## Threat model (short)

- **Attacker goal:** steer a later, legitimate-looking action (here, where a report is sent) by planting an instruction in persistent memory.
- **Entry points:** imported documents, web pages and other untrusted content that ends up stored as memory.
- **Why it persists:** a stored memory looks like any other note and is retrieved long after its source left the context.
- **Covered today:** actions to an unapproved recipient or an unknown tool.
- **Not covered today:** poison that changes content, parameters or destinations other than the recipient (scenario C); novel attack phrasing against a real model; any attack on the ledger's storage.

## Known limits

- The agent, retrieval and trust labels are scripted; the suspicious label is predefined, not detected.
- Leave-one-out here is a single deterministic run. With a real model it would need repeated trials, and would give "candidate influence", not proof. Single removal misses redundant poison; the joint-removal check covers only the all-untrusted case and relies on assigned trust labels.
- The ledger is hash-chained and exportable but lives in the browser session and can be cleared.
- The chain alone cannot detect a full rewrite with recomputed hashes, deletion of the latest records, or an empty ledger. Detecting those needs a head hash stored outside the ledger (signed or anchored elsewhere); this demo keeps that anchor in the same session, so it demonstrates the idea, not the protection.
- The gate runs in the same process as the agent. Its independence is a design principle, not deployment isolation. Production would use a separate service with its own credentials.
- Two or three scripted cases are a demonstration, not a benchmark. No detection accuracy is claimed.

## Roadmap (proposed, not built)

1. Real agent with inspectable memory retrieval.
2. Provenance and trust captured automatically at ingestion.
3. Policies on content, tools and destinations (closes scenario C).
4. Repeated-trial leave-one-out replay against a real model.
5. Persistent, access-controlled ledger storage.
6. Quarantine and rollback of suspect memory.

## Tools, third-party components and AI assistance

- **Runtime:** Python 3.11, Streamlit (UI), and the Python standard library (`hashlib`, `json`, `re`, `dataclasses`, `datetime`). **Tests:** pytest. No external APIs, datasets or models are used.
- **AI-assisted development:** the team used Claude (Anthropic) as a development assistant for substantial parts of the code, tests, README and presentation. The team directed the concept and scope, reviewed and ran the code, and is responsible for its content. Claims are limited to what the code and tests demonstrate.
- **Prior work:** leave-one-out replay is a standard ablation idea and hash-chained logs are a well-known technique. The contribution here is the investigation workflow that combines them for agent memory, as a concept prototype. Related work is listed under References.

## Run it

```bash
pip install -r requirements.txt
python -m streamlit run app.py

# tests
pip install -r requirements-dev.txt
python -m pytest -q
```

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI |
| `core.py` | Agent, policy gate, leave-one-out replay, hash-chained ledger |
| `tests/test_core.py` | Unit tests |
| `.github/workflows/tests.yml` | Runs the tests on every push |

## References

1. I. Habler, "Memory Is a Feature. It Is Also an Attack Surface," OWASP GenAI Security Project, 13 May 2026.
2. OWASP, "Top 10 for Agentic Applications for 2026," ASI06: Memory & Context Poisoning, Dec 2025.
3. Pulipaka et al., "Hidden in Memory: Sleeper Memory Poisoning in LLM Agents," arXiv:2605.15338 (preprint).
4. Chen et al., "AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases," NeurIPS 2024, arXiv:2407.12784.
5. Dong et al., MINJA, arXiv:2503.03704 (NeurIPS 2025). Title in the deck: "Memory Injection Attacks on LLM Agents via Query-Only Interaction"; an earlier version was titled "A Practical Memory Injection Attack against LLM Agents."
6. Sunil et al., "Memory Poisoning Attack and Defense on Memory Based LLM-Agents," arXiv:2601.05504 (preprint).

Published results in these papers are from other systems and are not results for MemorySleuth.
