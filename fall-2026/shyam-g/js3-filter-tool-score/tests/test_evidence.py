from js3.evidence import (gate_claims, label_claim, label_experience, label_location, label_role,
                          quote_found, verdict)
from js3.filter import load_rules

R = load_rules()


def P(title, location, content=""):
    return {"id": "t", "title": title, "location": location, "content": content}


def test_quote_must_be_verbatim():
    p = P("Demand Planner", "Boston, MA", "Own the S&OP forecast using SAP.")
    assert quote_found("own the  S&OP forecast", p)            # whitespace/case-normalized
    c = {"type": "skill", "term": "SAP", "quote": "Expert in SAP"}  # not in the posting
    assert label_claim(p, c, R)["label"] == "insufficient"


def test_location_labels():
    assert label_location(P("x", "Somerville, MA"), R)["label"] == "supported"
    assert label_location(P("x", "London, United Kingdom"), R)["label"] == "contradicted"
    assert label_location(P("x", ""), R)["label"] == "insufficient"


def test_experience_labels():
    assert label_experience(P("x", "y", "3+ years of experience in planning."), R)["label"] == "supported"
    assert label_experience(P("x", "y", "8+ years of experience in planning."), R)["label"] == "contradicted"
    assert label_experience(P("x", "y", "A great team."), R)["label"] == "insufficient"


def test_role_labels():
    assert label_role(P("Senior Buyer", "y"), R)["label"] == "contradicted"
    assert label_role(P("Buyer", "y"), R)["label"] == "supported"
    assert label_role(P("FP&A Analyst", "y"), R)["label"] == "insufficient"


def test_abstention_rule():
    ok = P("Demand Planner", "Boston, MA", "2+ years of experience with forecasting.")
    assert verdict(gate_claims(ok, R))["verdict"] == "relevant"
    no_years = P("Demand Planner", "Boston, MA", "Forecasting with SAP.")
    v = verdict(gate_claims(no_years, R))
    assert v["verdict"] == "I cannot tell" and v["because"] == ["experience"]
    far = P("Demand Planner", "Denver, CO", "Forecasting.")
    assert verdict(gate_claims(far, R))["verdict"] == "not relevant"


def test_abstention_limit_counterexample():
    """The documented limit (reports/SHORTLIST-NOTES.md): every gate claim is 'supported', so the rule
    says 'relevant', yet the years are in a domain the persona doesn't have. The rule checks the
    number, not the domain."""
    p = P("Supply Chain Engineer", "Somerville, MA",
          "5+ years of experience in chemical, specialty materials, polymer, coatings, adhesives manufacturing.")
    assert verdict(gate_claims(p, R))["verdict"] == "relevant"
