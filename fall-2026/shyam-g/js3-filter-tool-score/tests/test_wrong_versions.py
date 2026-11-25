"""FILTER.md section 6: each plausible-but-wrong version is implemented here on purpose. Each test
shows (a) the wrong version gives the wrong answer on a concrete posting and (b) the real filter or
checker gives the right one. If someone 'simplifies' the real code into a wrong version, (b) fails."""
import re

from js3.evidence import gate_claims, label_skill, verdict
from js3.filter import decide, load_rules

R = load_rules()


def P(title, location, content=""):
    return {"id": "t", "title": title, "location": location, "content": content}


# ---- W1: substring matching ----
def wrong_topic_substring(text):
    return sorted({w for w in R["topic_words"] if w in text.lower()})


def test_w1_substring():
    p = P("Operations Analyst", "Boston, MA",
          "You have excellent judgment. Partners at our Sapporo office. Inventory-free role.")
    wrong = wrong_topic_substring(p["content"])
    assert "excel" in wrong and "sap" in wrong          # the wrong version is fooled
    real = decide(p, R)["checks"]["topic"]
    assert "excel" not in real and "sap" not in real     # whole-word matching is not


# ---- W2: rank by raw topic count, no title exclusion ----
def wrong_rank(postings):
    return sorted(postings, key=lambda p: -len(wrong_topic_substring(p["content"])))


def test_w2_rank_without_exclusion():
    rich = " ".join(["SQL", "Power BI", "SAP", "MRP", "forecasting", "inventory", "Excel", "procurement"])
    senior = P("Senior Director, Supply Chain", "Boston, MA", f"Experience with {rich}.")
    junior = P("Demand Planner", "Boston, MA", "Experience with SQL and forecasting.")
    assert wrong_rank([junior, senior])[0] is senior     # the wrong ranking puts the director first
    assert decide(senior, R)["reason"] == "reject:seniority_title"
    assert decide(junior, R)["decision"] == "keep"


# ---- W3: missing location treated as a pass ----
def wrong_location_ok(p):
    return (not p["location"].strip()) or any(
        re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", p["location"].lower()) for t in R["location_ok"])


def test_w3_missing_location():
    p = P("Supply Chain Analyst", "", "Experience with SQL, SAP and forecasting.")
    assert wrong_location_ok(p) is True                  # wrong version: silence = pass
    d = decide(p, R)
    assert d["decision"] == "cannot_tell" and d["reason"] == "cannot_tell:location"
    assert verdict(gate_claims(p, R))["verdict"] == "I cannot tell"


# ---- W4: evidence = the term occurs anywhere ----
def wrong_support(p, term):
    return "supported" if term.lower() in p["content"].lower() else "insufficient"


def test_w4_occurrence_is_not_support():
    p = P("Program Manager", "Boston, MA",
          "Work cross-functionally between product, engineering, production, and supply chain personnel.\n"
          "SQL is not required for this role.\n"
          "Bonus Skills:\nBasic proficiency in Excel for data entry.")
    for term in ("supply chain", "SQL", "Excel"):
        assert wrong_support(p, term) == "supported"     # the wrong version calls all three supported
    assert label_skill(p, "supply chain")["label"] == "insufficient"   # collaboration mention
    assert label_skill(p, "SQL")["label"] == "contradicted"            # negation
    assert label_skill(p, "Excel")["label"] == "insufficient"          # under a Bonus header
