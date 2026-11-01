"""Extra tests written by Claude AFTER agent.py existed (not part of the pre-written gate).
They pin the Refuses section and the HTML-stripping decision."""
import pytest
import agent


def test_refuses_host_not_on_allowlist():
    with pytest.raises(PermissionError):
        agent.fetch("https://api.lever.co/v0/postings/example")


def test_refuses_plain_http_even_for_allowed_host():
    with pytest.raises(PermissionError):
        agent.fetch("http://boards-api.greenhouse.io/v1/boards/x/jobs")


def test_html_is_stripped_before_matching():
    assert agent.plain_text("&lt;li&gt;SQL&lt;/li&gt;&lt;li&gt;Power BI&lt;/li&gt;").split() == ["SQL", "Power", "BI"]


def test_justification_cites_resume_and_posting_fields():
    resume = {"target_titles": ["demand planner"], "skills": ["sap", "excel"],
              "locations": ["boston"], "exclude_keywords": []}
    j = agent.rule_justification(resume, {"id": 1, "title": "Demand Planner",
                                          "location": {"name": "Remote"}, "content": "SAP, Excel"})
    for field in ("resume.target_titles", "posting.title", "resume.skills", "posting.content",
                  "resume.locations", "posting.location"):
        assert field in j


def test_prompt_never_contains_contact_details():
    resume = {"name": "Jordan Rivera", "email": "j@example.com", "phone": "555-0142",
              "target_titles": ["x"], "skills": ["y"], "locations": ["z"], "exclude_keywords": []}
    p = agent.build_prompt(resume, {"id": 1, "title": "t", "location": {"name": "l"}, "content": "c"})
    assert "Jordan" not in p and "example.com" not in p and "555" not in p
