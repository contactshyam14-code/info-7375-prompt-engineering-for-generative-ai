"""The filter. Reads its rules from the ```json filter block in FILTER.md (the document is the filter).

decide(posting, rules) -> {"decision": "keep"|"reject"|"cannot_tell", "reason", "score", "checks"}
"""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
FILTER_MD = ROOT / "FILTER.md"

# v1.2 (after the shortlist showed misses): three shapes of a stated requirement
#   "5+ years of experience", "minimum of 8 years ... experience"   (figure, then up to 120 characters, then experience)
#   "1-3 years of progressive FP&A ... experience"                 (same, with a range: lower bound counts)
#   "Experience: 2–4 years in consulting"                           (the word experience first)
YEARS_RE = re.compile(
    r"(?:minimum of |at least |min\.? )?(\d{1,2})\s*(?:\+|plus)?\s*(?:(?:-|–|—|to)\s*\d{1,2}\s*\+?\s*)?"
    r"(?:years?|yrs?)\b(?:[\s,/&()\w'’-]{0,120}?)\b(?:experience|exp)\b"
    r"|experience\s*:\s*(\d{1,2})\s*\+?\s*(?:(?:-|–|—|to)\s*\d{1,2}\s*)?(?:years?|yrs?)\b",
    re.I,
)


def load_rules(path: pathlib.Path | str = FILTER_MD) -> dict:
    text = pathlib.Path(path).read_text(encoding="utf-8")
    m = re.search(r"```json filter\s*\n(.*?)\n```", text, re.S)
    if not m:
        raise ValueError(f"no ```json filter block in {path}")
    return json.loads(m.group(1))


def term_re(term: str) -> re.Pattern:
    return re.compile(r"(?<!\w)" + re.escape(term.lower()) + r"(?!\w)")


def matched(terms, text: str) -> list[str]:
    t = (text or "").lower()
    return [w for w in terms if term_re(w).search(t)]


def stated_years(text: str) -> list[int]:
    """Every years-of-experience figure the text states (the lower bound of a range)."""
    out = []
    for m in YEARS_RE.finditer(text or ""):
        n = int(m.group(1) or m.group(2))
        if 0 < n <= 30:
            out.append(n)
    return out


def checks(posting: dict, rules: dict) -> dict:
    title = posting.get("title") or ""
    loc = posting.get("location") or ""
    content = posting.get("content") or ""
    return {
        "location": matched(rules["location_ok"], loc),
        "location_empty": not loc.strip(),
        "title_exclude": matched(rules["title_exclude"], title),
        "years": stated_years(content),
        "role_strong": matched(rules["role_words_strong"], title),
        "role_weak": matched(rules["role_words_weak"], title),
        "topic": sorted(set(matched(rules["topic_words"], content))),
    }


def score_of(c: dict, rules: dict) -> int:
    w = rules["weights"]
    role = w["role_strong"] if c["role_strong"] else (w["role_weak"] if c["role_weak"] else 0)
    return role + w["topic_each"] * min(len(c["topic"]), rules["topic_cap"])


def decide(posting: dict, rules: dict) -> dict:
    c = checks(posting, rules)
    s = score_of(c, rules)
    if c["location_empty"]:
        d, why = "cannot_tell", "cannot_tell:location"
    elif not c["location"]:
        d, why = "reject", "reject:location"
    elif c["title_exclude"]:
        d, why = "reject", "reject:seniority_title"
    elif c["years"] and max(c["years"]) > rules["max_years"]:
        d, why = "reject", "reject:years"
    elif rules.get("require_role_word") and not (c["role_strong"] or c["role_weak"]):
        d, why = "reject", "reject:no_role_word"
    elif s >= rules["threshold"]:
        d, why = "keep", "keep:score"
    else:
        d, why = "reject", "reject:score"
    return {"decision": d, "reason": why, "score": s, "threshold": rules["threshold"],
            "version": rules["version"], "checks": c}


def load_corpus(path: pathlib.Path | str = ROOT / "data" / "corpus.jsonl") -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
