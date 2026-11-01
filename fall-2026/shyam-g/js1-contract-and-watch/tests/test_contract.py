"""Tests written BEFORE reading Claude Code's implementation.
Rename the import to match your module. They should FAIL until the agent exists.

Interface to require in the Claude Code prompt:
  judge_rule(resume: dict, posting: dict) -> "relevant" | "not_relevant"
  new_postings(seen_ids: set, response: dict, baseline: bool = False) -> list[posting]
  validate_claude(raw: str, posting_id: str, resume: dict) -> dict   # raises ValueError if invalid
"""
import json, pathlib, pytest
from agent import judge_rule, new_postings, validate_claude

ROOT = pathlib.Path(__file__).parent.parent
load = lambda p: json.loads((ROOT / p).read_text())
RESUME = load("persona/jordan_rivera.json")
POSTINGS = {str(j["id"]): j for j in load("fixtures/postings.json")["jobs"]}
EXPECTED = load("fixtures/expected_rule_verdicts.json")

# Wrong version 1: verdicts attached to the wrong postings
def test_each_id_gets_its_own_verdict():
    got = {pid: judge_rule(RESUME, p) for pid, p in POSTINGS.items()}
    assert got == {pid: e["verdict"] for pid, e in EXPECTED.items()}

# Substring traps: Germany/'ma', Worcester MA, sqlite/'sql', excellent/'excel'
@pytest.mark.parametrize("pid", ["1002", "1009", "1010"])
def test_word_boundary_traps(pid):
    assert judge_rule(RESUME, POSTINGS[pid]) == "not_relevant"

# Wrong version 2: justification that cites nothing real
@pytest.mark.parametrize("case", load("fixtures/claude_outputs.json")["cases"], ids=lambda c: c["name"])
def test_validator(case):
    raw = case.get("raw") or json.dumps(case["output"])
    if case["expect_valid"]:
        validate_claude(raw, "1001", RESUME)
    else:
        with pytest.raises(ValueError):
            validate_claude(raw, "1001", RESUME)

# Optional third wrong version: baseline reports postings as new
def test_baseline_reports_none_new():
    assert new_postings(set(), load("fixtures/seeded_run1.json"), baseline=True) == []

def test_second_run_reports_only_new_ids():
    seen = {str(j["id"]) for j in load("fixtures/seeded_run1.json")["jobs"]}
    ids = [j["id"] for j in new_postings(seen, load("fixtures/seeded_run2.json"))]
    assert sorted(ids) == load("fixtures/expected_new.json")["expected_new_on_run2"]  # removed 1002 is not "new"
