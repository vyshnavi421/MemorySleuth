import copy
import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import core  # noqa: E402
from core import (  # noqa: E402
    GENESIS_HASH, MEMORIES, SCENARIOS, influence, make_record,
    policy_gate, propose_action, verify_chain,
)

REQUIRED_FIELDS = {
    "time", "scenario", "retrieved", "proposed", "decision", "reason_code",
    "reason", "influential", "candidates", "advisory", "prev_hash", "hash",
}


def run(key, prev=GENESIS_HASH):
    return make_record(prev, SCENARIOS[key])


def test_policy_blocks_unapproved_and_allows_approved():
    base = {"tool": "send_report", "recipient": "finance@company.test"}
    assert policy_gate(base).allowed
    assert not policy_gate({**base, "recipient": "attacker@evil.test"}).allowed
    assert policy_gate({**base, "recipient": None}).code == "NO_RECIPIENT"


def test_policy_is_deny_by_default_for_unknown_tools():
    d = policy_gate({"tool": "delete_everything", "recipient": "finance@company.test"})
    assert not d.allowed and d.code == "TOOL_NOT_ALLOWED"


def test_policy_gate_takes_only_the_action():
    params = list(inspect.signature(policy_gate).parameters)
    assert params == ["action"]


def test_agent_reads_memory_text():
    assert propose_action([MEMORIES["MEM-001"]])["recipient"] == "finance@company.test"
    both = propose_action([MEMORIES["MEM-001"], MEMORIES["MEM-002"]])
    assert both["recipient"] == "attacker@evil.test"


def test_scenario_a_blocked_and_flags_mem002():
    rec = run("A")
    assert rec["decision"] == "BLOCKED"
    assert rec["proposed"]["recipient"] == "attacker@evil.test"
    assert rec["candidates"] == ["MEM-002"]


def test_scenario_b_allowed_no_candidates():
    rec = run("B")
    assert rec["decision"] == "ALLOWED"
    assert rec["proposed"]["recipient"] == "finance@company.test"
    assert rec["candidates"] == []


def test_benign_trusted_memory_is_influential_but_not_a_candidate():
    influential, candidates = influence([MEMORIES[i] for i in SCENARIOS["A"].retrieved])
    assert "MEM-003" in influential
    assert "MEM-003" not in candidates


def test_scenario_c_is_the_known_blind_spot():
    rec = run("C")
    assert rec["decision"] == "ALLOWED"  # gate checks the recipient only
    assert rec["proposed"]["extra_line"]
    assert rec["candidates"] == ["MEM-004"]
    assert "does not check content" in rec["advisory"]


def test_records_have_all_fields():
    for key in SCENARIOS:
        assert REQUIRED_FIELDS <= set(run(key))


def test_chain_valid_then_detects_tampering():
    records, prev = [], GENESIS_HASH
    for key in ("A", "B", "C"):
        rec = run(key, prev)
        records.append(rec)
        prev = rec["hash"]
    assert verify_chain(records) == (True, None)

    tampered = copy.deepcopy(records)
    tampered[0]["decision"] = "ALLOWED"
    assert verify_chain(tampered) == (False, 0)

    removed = [records[0], records[2]]
    assert verify_chain(removed)[0] is False


def test_deterministic_given_same_time():
    from datetime import datetime
    t = datetime(2026, 1, 1, 12, 0, 0)
    a = make_record(GENESIS_HASH, SCENARIOS["A"], now=t)
    b = make_record(GENESIS_HASH, SCENARIOS["A"], now=t)
    assert a == b
