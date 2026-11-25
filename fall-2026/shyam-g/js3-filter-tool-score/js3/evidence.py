"""Evidence rules from FILTER.md section 3: label one claim supported / contradicted / insufficient
against the posting's own text. No Claude call happens here. Every label is computed from the text.

Claim shape: {"type": "role"|"location"|"experience"|"skill"|"other", "claim": str,
              "term": str (skill claims), "quote": str (optional, must be verbatim)}
"""
from __future__ import annotations

import re

from .filter import matched, stated_years, term_re, YEARS_RE

NEGATION = re.compile(r"\b(not required|no prior|not necessary|not needed|don't need|do not need|"
                      r"no experience)\b", re.I)
SOFT = re.compile(r"\b(nice to have|nice-to-have|bonus|a plus|preferred|plus if|ideally)\b", re.I)
BOILERPLATE = re.compile(r"\b(equal opportunity|benefits|401\(k\)|parental leave|we are all owners|"
                         r"about (us|formlabs|spotify|palantir)|accommodation|privacy notice|"
                         r"compensation)\b", re.I)
# A term followed by one of these is a mention of people the job works WITH, not a skill it uses.
COLLAB_AFTER = re.compile(r"^\s*(personnel|teams?|partners?|stakeholders|organization|groups?|"
                          r"counterparts|colleagues|functions?)\b", re.I)
REQUIREMENT_CUE = re.compile(r"\b(experience|proficien\w*|familiar\w*|knowledge|expertise|skills?|"
                             r"required|requires?|must|comfortable|writing|"   # v1.2 additions
                             r"background|fluent|fluency|use|using|build|own|manage|managing|"
                             r"analy\w+|forecast\w*|plan\w*|responsible|drive|lead)\b", re.I)
# v1.2: a line under one of these headers is nice-to-have, even if the line itself doesn't say so
SOFT_HEADER = re.compile(r"^\s*(bonus( points| skills)?|nice[ -]to[ -]haves?|preferred( qualifications)?|"
                         r"pluses|extra credit|good to have)\s*:?\s*$", re.I)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if s.strip()]


def is_header(line: str) -> bool:
    line = line.strip()
    return bool(line) and len(line) <= 60 and (line.endswith(":") or bool(SOFT_HEADER.match(line)))


def soft_section_lines(text: str) -> list[str]:
    """Normalized lines that sit under a 'Bonus / Nice to have / Preferred' header."""
    out, soft = [], False
    for line in (text or "").split("\n"):
        if is_header(line):
            soft = bool(SOFT_HEADER.match(line.strip()))
            continue
        if soft and line.strip():
            out.append(norm(line))
    return out


def in_soft_section(sentence: str, soft_lines: list[str]) -> bool:
    s = norm(sentence)
    return bool(s) and any(s in line for line in soft_lines)


def quote_found(quote: str, posting: dict) -> bool:
    q = norm(quote)
    if not q:
        return False
    hay = norm(" ".join([posting.get("title") or "", posting.get("location") or "",
                         posting.get("content") or ""]))
    return q in hay


def _label(label: str, why: str, evidence: str = "") -> dict:
    return {"label": label, "why": why, "evidence": evidence}


def label_role(posting: dict, rules: dict) -> dict:
    title = posting.get("title") or ""
    excl = matched(rules["title_exclude"], title)
    if excl:
        return _label("contradicted", f"title has exclusion word(s) {excl}", title)
    strong = matched(rules["role_words_strong"], title)
    if strong:
        return _label("supported", f"title has role word(s) {strong}", title)
    return _label("insufficient", "title has no strong role word; the title alone can't settle it", title)


def label_location(posting: dict, rules: dict) -> dict:
    loc = (posting.get("location") or "").strip()
    if not loc:
        return _label("insufficient", "location field is empty")
    ok = matched(rules["location_ok"], loc)
    if ok:
        return _label("supported", f"location field matches {ok}", loc)
    return _label("contradicted", "location field names a place outside the gate and no 'remote'", loc)


def label_experience(posting: dict, rules: dict) -> dict:
    text = posting.get("content") or ""
    hits = [(int(m.group(1) or m.group(2)), m.group(0)) for m in YEARS_RE.finditer(text)
            if 0 < int(m.group(1) or m.group(2)) <= 30]
    if not hits:
        return _label("insufficient", "the posting states no years-of-experience figure")
    big = [h for h in hits if h[0] > rules["max_years"]]
    if big:
        return _label("contradicted", f"states {big[0][0]} years > max {rules['max_years']}", big[0][1])
    return _label("supported", f"largest stated figure {max(h[0] for h in hits)} ≤ {rules['max_years']}",
                  hits[0][1])


def label_skill(posting: dict, term: str, quote: str = "") -> dict:
    """Skill claim: 'the job requires/uses <term>'."""
    text = posting.get("content") or ""
    rx = term_re(term)
    if quote:
        if not quote_found(quote, posting):
            return _label("insufficient", "quote not found verbatim in the posting", quote)
        if not rx.search(quote.lower()):
            return _label("insufficient", f"quote does not name '{term}'", quote)
        cands = [quote]
    else:
        cands = [s for s in sentences(text) if rx.search(s.lower())]
        if not cands:
            return _label("insufficient", f"'{term}' does not occur in the posting text")
    soft_lines = soft_section_lines(text)
    best = None
    for s in cands:
        low = s.lower()
        m = rx.search(low)
        if NEGATION.search(s):
            return _label("contradicted", f"'{term}' appears only under a negation", s)
        if BOILERPLATE.search(s):
            best = best or _label("insufficient", "term occurs in boilerplate, not in the job's duties", s)
            continue
        if COLLAB_AFTER.search(low[m.end():]):
            best = best or _label("insufficient",
                                  f"'{term}' names people the job works with, not a skill it uses", s)
            continue
        if SOFT.search(s) or in_soft_section(s, soft_lines):
            best = best or _label("insufficient", f"'{term}' is nice-to-have, not required", s)
            continue
        if REQUIREMENT_CUE.search(s):
            return _label("supported", f"'{term}' named in a duty/requirement sentence", s)
        best = best or _label("insufficient", f"'{term}' occurs but not as a duty or requirement", s)
    return best


def label_claim(posting: dict, claim: dict, rules: dict) -> dict:
    t = claim.get("type")
    quote = claim.get("quote") or ""
    if t == "role":
        out = label_role(posting, rules)
    elif t == "location":
        out = label_location(posting, rules)
    elif t == "experience":
        out = label_experience(posting, rules)
    elif t == "skill":
        out = label_skill(posting, claim.get("term") or "", quote)
    else:
        # A free-form claim: the only thing checkable mechanically is its quote.
        if quote and quote_found(quote, posting):
            out = _label("insufficient", "quote is verbatim, but this claim type has no entailment "
                                         "rule; needs a hand label", quote)
        else:
            out = _label("insufficient", "no verbatim quote", quote)
    if quote and t in ("role", "location", "experience") and not quote_found(quote, posting):
        out = dict(out, note="claim's own quote was not found verbatim; label computed from the fields")
    return out


def gate_claims(posting: dict, rules: dict) -> dict:
    return {"role": label_role(posting, rules), "location": label_location(posting, rules),
            "experience": label_experience(posting, rules)}


def verdict(gates: dict) -> dict:
    """Abstention rule (FILTER.md section 3)."""
    contra = [k for k, v in gates.items() if v["label"] == "contradicted"]
    insuff = [k for k, v in gates.items() if v["label"] == "insufficient"]
    if contra:
        return {"verdict": "not relevant", "because": contra}
    if insuff:
        return {"verdict": "I cannot tell", "because": insuff}
    return {"verdict": "relevant", "because": []}
