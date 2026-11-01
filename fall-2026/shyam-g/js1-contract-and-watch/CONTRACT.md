# CONTRACT: Job-Search Agent 1

Written: 10/30/2026, before any implementation code existed.
Author: Shyam Sundar Jayaraman Gopalakrishnan.
Disclosure: the first draft of this contract was written by Claude; I
rewrote it on 10/30/2026. Amended 10/31/2026; see section 8. What I changed is listed in SOURCES.md.

## 1. In
- **Board:** one public job board, named by host and board token.
  - Host: `boards-api.greenhouse.io`
  - Board token: `formlabs` (verified 10/31/2026: returned JSON, 238 postings)
  - Endpoint: `https://boards-api.greenhouse.io/v1/boards/formlabs/jobs?content=true`
- **Résumé:** `persona/jordan_rivera.json`, a FICTIONAL persona (not me),
  with fields `name`, `email` (@example.com), `phone` (555 number),
  `target_titles[]`, `skills[]`, `locations[]`, `exclude_keywords[]`.
- **Needs:**
  - network access to hosts listed in `allowlist.txt` only
  - a writable `state/` folder holding `seen_ids.json` and `raw/` responses
  - a logged-in Claude Code CLI (`claude -p`) for the Claude judge;
    no API key or credential in the repo

## 2. Out
For each NEW posting only (never one already seen), one record:
- `posting_id`
- `rule_verdict`: `relevant` | `not_relevant`. A RECORD, computed by
  the rule in section 4. Anyone can recompute it.
- `claude_verdict`: `relevant` | `not_relevant`. A JUDGMENT, always
  labeled "Claude's judgment", never shown as fact.
- `justification`: names at least one résumé field and one posting
  field behind the verdict, for example
  `resume.skills: "sql", "power bi" matched posting.content`.
- Baseline run: reports zero new postings, saves the raw response and
  the ids it saw.

## 3. Refuses
- Fetching any host not in `allowlist.txt`.
- Showing a real résumé on screen, in logs, or on GitHub.
- Presenting a model's judgment as a fact.
- Applying, emailing or messaging anyone, or logging in anywhere.
- Accepting a Claude output that fails the validator. It is rejected
  and logged, never silently repaired.
- Judging a posting it has already seen.

## 4. The rule (rule_verdict)
Matching: case-insensitive, WHOLE-WORD/PHRASE. A term matches only if
the characters before and after it are not letters or digits (regex
`(?<!\w)term(?!\w)`, term escaped). So "sql" does not match "sqlite",
"excel" does not match "excellent". Input is the posting's plain text;
HTML in `content` is STRIPPED first: entities are unescaped, tags are
removed, then entities are unescaped again (Greenhouse escapes its HTML).
Pinned by `tests/test_extra.py::test_html_is_stripped_before_matching`.

A posting is `relevant` only if ALL hold:
1. TITLE: `title` matches at least one `resume.target_titles` entry.
2. LOCATION: `location.name` matches an entry in `resume.locations`,
   or matches "remote".
3. SKILLS: `content` matches at least 2 DISTINCT `resume.skills` entries.
4. EXCLUSIONS: neither `title` nor `content` matches any
   `resume.exclude_keywords` entry.
Otherwise `not_relevant`.

Decision: "ma" is NOT a location term (it matched "Germany" as a
substring). Consequence: "Worcester, MA" is `not_relevant` unless
"massachusetts" appears. I accept this limitation; fixture 1009 pins it.

Persona values live in `persona/jordan_rivera.json`. A TA with that
file and a posting can compute the verdict by hand in under a minute.

## 5. Wrong versions the tests must catch
1. **Verdicts paired with the wrong postings.** The verdicts are
   right but attached to the wrong ids (misalignment, sorting).
   Test: `test_each_id_gets_its_own_verdict` over 10 fixture postings.
2. **Justification that cites nothing real.** Text like "good fit for
   your background", or a cited résumé/posting field that does not
   exist. Test: `test_validator` rejects both.
(Optional third: baseline run reports existing postings as new.
Test: `test_baseline_reports_none_new`.)

## 6. What a failure looks like

On October 30, 2026, I expect the most likely failure to be that the
rule rejects real fits such as "Supply Planner" or "Business Operations
Analyst" because my target_titles list only contains exact phrases,
which I would notice because my hand label says relevant while
rule_verdict says not_relevant for those postings in the output file.

## 7. Claude output format (validated)
JSON only, no prose, no code fences:
{"posting_id": "<string>",
 "verdict": "relevant" | "not_relevant",
 "resume_fields": ["skills", "locations", ...],
 "posting_fields": ["title", "content", "location"],
 "justification": "<one to three sentences>"}
Validator rejects: invalid JSON, extra keys, a verdict outside the two
values, empty field lists, field names not in the résumé or posting
schema, or a `posting_id` that does not match the posting asked about.

## 8. Amendments (10/31/2026, after implementation existed)
Made at my direction after `agent.py` was written; the rule in section 4
did not change except where it was left undecided.
1. Board token filled in: `formlabs` (Somerville, MA, matches persona
   `locations`).
2. HTML decision made: stripped before matching (was "DECIDE").
3. Claude access: the Claude Code CLI replaces "an Anthropic API key in
   an environment variable". Each call is a fresh, tool-less conversation.
4. Résumé validation added: `agent.validate_resume` refuses a résumé
   missing a rule field, or whose email is not @example.com or phone is
   not a 555 number, before any fetch (`tests/test_resume.py`).
