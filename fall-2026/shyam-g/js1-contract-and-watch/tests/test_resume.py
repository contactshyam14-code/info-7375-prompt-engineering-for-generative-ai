"""Résumé validation tests, written by Claude on 2026-10-31 after agent.py existed (student-directed)."""
import copy, json, pathlib
import pytest
import agent

PERSONA = json.loads((pathlib.Path(__file__).parent.parent / "persona" / "jordan_rivera.json").read_text(encoding="utf-8"))


def test_shipped_persona_is_valid():
    assert agent.validate_resume(copy.deepcopy(PERSONA))


@pytest.mark.parametrize("key", ["target_titles", "skills", "locations", "exclude_keywords"])
def test_missing_field_rejected(key):
    r = copy.deepcopy(PERSONA); del r[key]
    with pytest.raises(ValueError):
        agent.validate_resume(r)


def test_empty_skills_rejected():
    r = copy.deepcopy(PERSONA); r["skills"] = []
    with pytest.raises(ValueError):
        agent.validate_resume(r)


def test_non_string_entry_rejected():
    r = copy.deepcopy(PERSONA); r["skills"] = ["sql", 5]
    with pytest.raises(ValueError):
        agent.validate_resume(r)


def test_real_looking_email_refused():
    r = copy.deepcopy(PERSONA); r["email"] = "someone@gmail.com"
    with pytest.raises(ValueError, match="real"):
        agent.validate_resume(r)


def test_non_555_phone_refused():
    r = copy.deepcopy(PERSONA); r["phone"] = "617-373-2000"
    with pytest.raises(ValueError, match="real"):
        agent.validate_resume(r)


def test_run_refuses_invalid_resume_before_fetching(tmp_path):
    bad = tmp_path / "real.json"
    bad.write_text(json.dumps({**PERSONA, "email": "me@northeastern.edu"}), encoding="utf-8")
    with pytest.raises(ValueError):
        agent.run("formlabs", None, "live", False, str(bad), state=tmp_path / "state")
    assert not (tmp_path / "state").exists()
