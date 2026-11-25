import json
import re

from js3.filter import FILTER_MD, decide, load_rules, stated_years

R = load_rules()


def P(title, location, content=""):
    return {"id": "t", "title": title, "location": location, "content": content}


def test_rules_come_from_the_document():
    text = FILTER_MD.read_text(encoding="utf-8")
    block = re.search(r"```json filter\s*\n(.*?)\n```", text, re.S).group(1)
    assert json.loads(block) == R
    assert R["version"] in text.splitlines()[2]          # header version matches the block


def test_location_is_a_gate_not_a_weight():
    rich = "Experience with SQL, SAP, MRP, forecasting, inventory and procurement."
    assert decide(P("Supply Chain Analyst", "Shenzhen", rich), R)["reason"] == "reject:location"
    assert decide(P("Supply Chain Analyst", "Somerville, MA", rich), R)["decision"] == "keep"


def test_years_rule_uses_largest_figure():
    p = P("Supply Chain Analyst", "Boston, MA", "2+ years of experience with SQL. 7+ years of experience in SAP.")
    assert decide(p, R)["reason"] == "reject:years"


def test_role_word_required_v11():
    p = P("Startup Founder", "Boston, MA", "Familiarity with SQL, Excel, Tableau. Set up a supply chain.")
    assert decide(p, R)["reason"] == "reject:no_role_word"


def test_threshold_boundary():
    # strong title (3) + exactly one topic word (1) = 4 = threshold -> keep; with none -> reject
    assert decide(P("Product Manager", "Boston, MA", "Experience with SQL."), R)["decision"] == "keep"
    assert decide(P("Product Manager", "Boston, MA", "Great team."), R)["reason"] == "reject:score"


def test_stated_years_shapes():
    assert stated_years("5+ years of experience in chemical") == [5]
    assert stated_years("minimum of 8 years of relevant experience") == [8]
    assert stated_years("1-3 years of progressive FP&A, data analytics, business intelligence, "
                        "or strategic finance experience") == [1]
    assert stated_years("Experience: 2–4 years in consulting") == [2]
    assert stated_years("Formlabs was founded 10 years ago") == []


def test_known_false_positive_is_documented():
    # FILTER.md section 7 (v1.2) accepts this false positive; if it ever stops matching, update the doc.
    assert stated_years("our 3 years of growth and customer experience") == [3]
