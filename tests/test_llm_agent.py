import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core import (  # noqa: E402
    GENESIS_HASH, MEMORIES, SCENARIOS, Memory, make_record, verify_chain,
)
from llm_agent import FAIL_CLOSED, build_prompt, make_llm_agent, parse_action  # noqa: E402


class FakeClient:
    """Stands in for the Anthropic client. Behaves like an obedient model: the last note
    that names a recipient wins, so an injected note can steer it."""

    def __init__(self, reply=None):
        self.reply = reply
        self.prompts = []
        self.messages = self

    def create(self, **kw):
        prompt = kw["messages"][0]["content"]
        self.prompts.append(prompt)
        if self.reply is not None:
            text = self.reply
        else:
            recipient = None
            for line in prompt.splitlines():
                for word in line.replace('"', " ").split():
                    if "@" in word:
                        recipient = word
            text = '{"recipient": %s, "format": "PDF", "extra_line": null}' % (
                f'"{recipient}"' if recipient else "null")
        return SimpleNamespace(content=[SimpleNamespace(text=text)])


def test_parse_valid_and_fenced_json():
    good = '{"recipient": "a@b.test", "format": "PDF", "extra_line": "hi"}'
    assert parse_action(good)["recipient"] == "a@b.test"
    assert parse_action("```json\n" + good + "\n```")["extra_line"] == "hi"


def test_parse_fails_closed_on_garbage_and_wrong_types():
    for bad in ("not json", "[]", "", '{"recipient": 5}', '{"recipient": ""}'):
        assert parse_action(bad)["recipient"] is None
    assert parse_action("not json") == FAIL_CLOSED


def test_prompt_contains_memory_text_in_order():
    p = build_prompt([MEMORIES["MEM-003"], MEMORIES["MEM-001"]])
    assert p.index("Send reports only") < p.index("Format reports as PDF")


def test_llm_agent_pipeline_blocks_poisoned_recipient_and_names_candidate():
    agent = make_llm_agent(FakeClient())
    rec = make_record(GENESIS_HASH, SCENARIOS["A"], agent=agent, agent_name="llm:test")
    assert rec["agent"] == "llm:test"
    assert rec["proposed"]["recipient"] == "attacker@evil.test"
    assert rec["decision"] == "BLOCKED"
    assert rec["candidates"] == ["MEM-002"]


def test_llm_agent_scenario_b_is_allowed():
    agent = make_llm_agent(FakeClient())
    rec = make_record(GENESIS_HASH, SCENARIOS["B"], agent=agent, agent_name="llm:test")
    assert rec["decision"] == "ALLOWED" and rec["candidates"] == []


def test_bad_model_reply_is_blocked_not_allowed():
    agent = make_llm_agent(FakeClient(reply="I cannot do that"))
    rec = make_record(GENESIS_HASH, SCENARIOS["B"], agent=agent, agent_name="llm:test")
    assert rec["decision"] == "BLOCKED" and rec["reason_code"] == "NO_RECIPIENT"


def test_identical_memory_sets_are_not_called_twice():
    client = FakeClient()
    agent = make_llm_agent(client)
    mems = [MEMORIES["MEM-001"], MEMORIES["MEM-003"]]
    agent(mems), agent(list(reversed(mems)))
    assert len(client.prompts) == 1 and agent.calls["n"] == 1


def test_llm_records_chain_and_verify():
    agent = make_llm_agent(FakeClient())
    a = make_record(GENESIS_HASH, SCENARIOS["A"], agent=agent, agent_name="llm:test")
    b = make_record(a["hash"], SCENARIOS["B"], seq=2, agent=agent, agent_name="llm:test")
    assert verify_chain([a, b]) == (True, None)
    b["agent"] = "scripted"
    assert verify_chain([a, b])[0] is False


def test_gate_still_never_receives_memory_text():
    seen = []
    import core
    real = core.policy_gate
    core.policy_gate = lambda action: (seen.append(action), real(action))[1]
    try:
        make_record(GENESIS_HASH, SCENARIOS["A"], agent=make_llm_agent(FakeClient()))
    finally:
        core.policy_gate = real
    assert seen and all(set(a) == {"tool", "recipient", "format", "extra_line"} for a in seen)
    assert not any("Ignore the approved" in str(a) for a in seen)
    assert isinstance(Memory, type)
