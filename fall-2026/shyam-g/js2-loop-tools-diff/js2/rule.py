"""The relevance rule, copied unchanged from Job-Search Agent 1 (js1-contract-and-watch/agent.py,
sections "résumé validation" and "the rule"). JS1 CONTRACT.md section 4 defines it.
Only the imports and this docstring are new."""
import html
import re

STRIP_HTML = True

VERDICTS = ("relevant", "not_relevant")
RESUME_FIELDS = ("target_titles", "skills", "locations", "exclude_keywords")
MIN_SKILLS = 2

# ---------- résumé validation (fictional persona only) ----------

def validate_resume(resume: dict) -> dict:
    """Reject a résumé the rule cannot use, or one that looks real (CONTRACT sections 1 and 3)."""
    if not isinstance(resume, dict):
        raise ValueError("résumé must be a JSON object")
    for key in RESUME_FIELDS:
        vals = resume.get(key)
        if not isinstance(vals, list) or not all(isinstance(v, str) and v.strip() for v in vals):
            raise ValueError(f"résumé.{key} must be a list of non-empty strings")
    for key in ("target_titles", "skills", "locations"):
        if not resume[key]:
            raise ValueError(f"résumé.{key} is empty; the rule can never match")
    if not str(resume.get("email", "")).lower().endswith("@example.com"):
        raise ValueError("refused: email is not @example.com, so this may be a real résumé")
    if "555" not in re.sub(r"\D", "", str(resume.get("phone", ""))):
        raise ValueError("refused: phone is not a 555 number, so this may be a real résumé")
    return resume


# ---------- the rule (a record) ----------

def plain_text(s: str) -> str:
    if not STRIP_HTML:
        return s or ""
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    return html.unescape(s)


def matched(terms, text: str) -> list[str]:
    """Terms that appear as whole words/phrases, case-insensitive (CONTRACT section 4)."""
    text = text.lower()
    return [t for t in terms if re.search(r"(?<!\w)" + re.escape(t.lower()) + r"(?!\w)", text)]


def rule_checks(resume: dict, posting: dict) -> dict:
    title = posting.get("title") or ""
    location = (posting.get("location") or {}).get("name") or ""
    content = plain_text(posting.get("content") or "")
    return {
        "title": matched(resume["target_titles"], title),
        "location": matched(list(resume["locations"]) + ["remote"], location),
        "skills": sorted(set(matched(resume["skills"], content))),
        "exclusions": sorted(set(matched(resume["exclude_keywords"], title + "\n" + content))),
    }


def judge_rule(resume: dict, posting: dict) -> str:
    c = rule_checks(resume, posting)
    ok = c["title"] and c["location"] and len(c["skills"]) >= MIN_SKILLS and not c["exclusions"]
    return "relevant" if ok else "not_relevant"


def rule_justification(resume: dict, posting: dict) -> str:
    c = rule_checks(resume, posting)
    parts = [
        f"resume.target_titles vs posting.title: {c['title'] or 'no match'}",
        f"resume.locations(+remote) vs posting.location.name: {c['location'] or 'no match'}",
        f"resume.skills vs posting.content: {c['skills'] or 'none'} "
        f"({len(c['skills'])}/{MIN_SKILLS} needed)",
        f"resume.exclude_keywords vs posting.title+content: {c['exclusions'] or 'none'}",
    ]
    return "; ".join(parts)
