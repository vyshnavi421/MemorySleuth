# MemorySleuth: 2-minute demo script and judge Q&A

## Demo (about 2 minutes)
1. **Setup (15s).** "Four stored memories. Two trusted, two from untrusted sources. The trust labels are set by our demo; we don't claim to detect poison."
2. **Run A (30s).** "Same task: send the report. An imported document planted MEM-002. The agent proposes attacker@evil.test. The policy gate sees only the action, not the memory text, and blocks it."
3. **Run B (20s).** "Replay without MEM-002 and the approved recipient comes back. Leave-one-out tells us which memory changed the action. It shows influence, not causal proof."
4. **Run C (25s).** "This one changes the report text, not the recipient. The standard gate allows it. That is a limit we show openly. Turn on Strict policy and it is blocked."
5. **Integrity (20s).** "Every run is one SHA-256 hash-chained record. We edit a copy, the chain check says Detected. Deleting the last record is only caught with a head hash kept outside the ledger."
6. **Optional LLM (10s).** "Toggle the live LLM agent: same gate, same replay, same ledger, real model."

## Likely questions
- **Isn't this just a policy filter?** The gate stops the action. MemorySleuth also answers which stored memory steered it, and keeps tamper-evident proof.
- **Trust labels are hand-set.** Yes, stated on the slides. Provenance at ingestion is the next step.
- **Is the replay proof of cause?** No. One run shows influence. A live model is one trial per call; repeated trials are future work.
- **Can't an attacker edit the ledger?** An edit breaks the chain. A full recompute or tail deletion needs an outside head hash; we say so.
- **Why is the gate in the same process?** Independence is by design (it accepts only the action), not deployment isolation. Separate deployment is future work.
- **What is real vs scripted?** Real: gate, replay, ledger, tests, optional LLM agent. Scripted: memory contents, retrieval, trust labels.
