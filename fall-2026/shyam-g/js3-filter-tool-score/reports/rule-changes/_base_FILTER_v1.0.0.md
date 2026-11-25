# FILTER.md: the gate for Job-Search Agent 3

**Version:** 1.0.0 (written 2026-11-23, before any filter code existed; see git order)
**Persona:** Jordan Rivera, fictional (`persona/jordan_rivera.json`). Wants entry-to-mid-level
supply chain, procurement, planning, operations-analyst, or project/product manager roles in the
Boston area or remote, with 5 years of experience or less.

The filter **is** this document. `js3/filter.py` reads the JSON block in section 1 straight out of
this file, so any change to a rule is a change to FILTER.md, with a version bump and a line in
section 6.

---

## 1. The filter (machine-readable; each rule's reason is in section 2)

```json filter
{
  "version": "1.0.0",
  "role_words_strong": ["supply chain", "procurement", "sourcing", "buyer", "demand planner",
    "demand planning", "supply planner", "planner", "logistics", "operations analyst",
    "strategy & operations", "business operations", "project manager", "program manager",
    "product manager"],
  "role_words_weak": ["analyst", "operations", "coordinator", "planning"],
  "topic_words": ["sql", "power bi", "sap", "mrp", "forecasting", "inventory", "excel",
    "procurement", "supply chain", "erp", "s&op", "supplier", "logistics", "tableau"],
  "topic_cap": 4,
  "location_ok": ["boston", "cambridge", "somerville", "massachusetts", "billerica", ", ma",
    "remote"],
  "title_exclude": ["senior", "sr.", "sr", "director", "vp", "vice president", "principal",
    "head of", "staff", "intern", "internship"],
  "max_years": 5,
  "weights": {"role_strong": 3, "role_weak": 1, "topic_each": 1},
  "threshold": 4
}
```

**Decision procedure, in order:**
1. **Location gate.** `location` must contain a `location_ok` term (whole word or phrase,
   case-insensitive). If it doesn't, the posting is rejected (`reject:location`). If the
   location field is empty, the posting is not rejected silently: it is marked `cannot_tell:location`.
2. **Title exclusions.** A `title_exclude` term in the title means reject (`reject:seniority_title`).
3. **Years rule.** If the posting text states a required number of years greater than
   `max_years` ("6+ years", "7 years of experience", "minimum of 8 years"), the posting is rejected
   (`reject:years`). The largest stated number is the one that counts.
4. **Score.** `role_strong` (3) if the title has a strong role word, otherwise `role_weak` (1) if
   it has a weak one, plus `topic_each` (1) for each distinct topic word found in the posting
   text, up to `topic_cap` (4). **Keep if score ≥ threshold (4).**

All matching is by whole word or phrase, case-insensitive (`(?<!\w)term(?!\w)`), never by substring.

## 2. One line of reasoning per rule

| Rule | Why |
|---|---|
| Location is a gate, not a weight | A Shenzhen job is not "partly" relevant to someone who lives in Boston. If location were a weight, a strong title could buy its way past it. |
| Empty location → `cannot_tell`, not reject and not pass | A missing field is not evidence either way (see wrong version W3). |
| `location_ok` includes `, ma` and `billerica` | Formlabs writes "Somerville, MA" and "Billerica, MA". `, ma` catches Massachusetts towns I didn't list. |
| `remote` passes the gate | The persona accepts remote work. Risk: "Remote – EMEA" also passes. Noted in section 5. |
| Strong role words = the persona's targets plus their close synonyms | Sourcing, buyer, and planner are the same job family as procurement and demand planner. |
| Weak role words score only 1 | "Analyst" or "operations" alone covers security analyst and IT operations too, so it needs topic words to back it up. |
| Topic words come from the persona's skills plus supply-chain vocabulary | They show what the job does, not what it's called. The cap of 4 stops a long posting from winning on length alone. |
| Title exclusions | The persona avoids director/VP/principal/senior (JS1 `exclude_keywords`). I added "staff" (a senior ladder rung) and "intern" (the JS1 hand label marked a sourcing intern not relevant). |
| `max_years` = 5 | The persona brief says 5 years or less, carried over from JS1 and the Reallocation mode (≤2 years would be stricter, but planners often ask for 3). |
| Threshold 4 | A strong title plus one topic word, or a weak title plus three topic words. Hand-set, not fitted (see SCORE-ORIGINS.md). |

## 3. Evidence rules (applied to every claim in a shortlist justification)

A **claim** is one sentence of the form "this posting has property P", with the claim type
and, wherever possible, a **quote** copied from the posting.

| Label | When |
|---|---|
| **supported** | The quote appears **verbatim** (whitespace-normalized) in the posting's title, location, or text, **and** the quote itself states P: for a skill claim, it names the skill outside a negation ("not required", "no … needed", "nice to have" counts as *insufficient*, not supported). For location, the location field satisfies the gate. For experience, the posting states a years figure ≤ `max_years` and none above it. |
| **contradicted** | The posting's own text states not-P: a location field that names a place outside the gate with no "remote"; a years figure above `max_years`; a title exclusion word; or a skill named only in a negation. |
| **insufficient** | Neither. Includes: no quote, a quote not found verbatim, a term that appears only in boilerplate (benefits, EEO, "about us"), a skill listed as "nice to have"/"bonus"/"preferred", and no years figure stated at all. |

**Relevance is not entailment.** A posting can pass the filter because a topic word occurs and
still not support the claim "this job uses that skill". "Inventory" in "manage our inventory of
demo printers" is not a planning skill. Matching words gets a posting onto the shortlist.
It doesn't support any claim about the posting.

**Abstention rule: when the agent must say "I cannot tell".** For each shortlisted posting,
three gate claims are checked: role (title), location, and experience (≤ 5 years). If **any**
gate claim is *insufficient*, the agent's verdict on that posting is **"I cannot tell"**, not
"relevant". It lists which claim it couldn't settle and what text would settle it. If any gate
claim is *contradicted*, the verdict is "not relevant", whatever the score. Claude's
justification never overrides a gate label.

## 4. Expected sources

| Board | ATS | Endpoint | Fields used | Expected status |
|---|---|---|---|---|
| formlabs | Greenhouse | `boards-api.greenhouse.io/v1/boards/formlabs/jobs?content=true` | id, title, location.name, content (HTML→text), absolute_url | ok |
| spotify | Lever | `api.lever.co/v0/postings/spotify?mode=json` | id, text, categories.location, workplaceType, descriptionPlain, lists, additionalPlain, hostedUrl | ok |
| palantir | Lever | `api.lever.co/v0/postings/palantir?mode=json` | same as spotify | ok |
| nosuchboard-js2-xyz | Greenhouse | (deliberate 404 from JS2) | — | error |

**When something is missing:**
- **A board errored or is absent:** report it as **unchecked**, never as "0 relevant postings".
  The shortlist states which boards it covers.
- **A posting has an empty location:** `cannot_tell:location`, listed separately and never kept
  silently.
- **A posting has empty or very short text (< 200 characters):** topic score is 0 and the
  experience claim is *insufficient*. If it makes the shortlist on title alone, it gets "I cannot tell".
- **A field the evidence rules need isn't in the source** (Greenhouse has no workplaceType):
  that claim is *insufficient*. It isn't inferred from other fields.

Corpus for this assignment: my JS2 real run `2026-11-10T213906-after-patch` (640 postings:
formlabs 250, spotify 86, palantir 304). The 404 board is unchecked.

## 5. Known risks I'm accepting in v1
- `remote` passes the gate even when it's "Remote – UK".
- Non-English postings will never match topic words (also found in JS2).
- `sr` as a bare title word could appear in other senses (rare in titles).

## 6. Wrong versions my tests must catch

| ID | Plausible but wrong | Why it's wrong | Test |
|---|---|---|---|
| W1 | Substring matching (`"sap" in text`, `"excel" in text`) | "excel" matches "excellent", and "sap" matches "Sapporo". Topic scores inflate on prose. | `tests/test_wrong_versions.py::test_w1_substring` |
| W2 | Rank by raw topic-word count, with no title exclusion | A "Senior Director, Supply Chain" with 8 skills ranks first, and the persona can't take it. | `::test_w2_rank_without_exclusion` |
| W3 | Treat a missing location as a pass ("probably remote") | Silence isn't evidence. It turns an unknown into a keep. | `::test_w3_missing_location` |
| W4 | Evidence = "the term occurs anywhere in the posting" | Labels a negated or nice-to-have skill as supported (relevance mistaken for entailment). | `::test_w4_occurrence_is_not_support` |

## 7. Change log (every rule added, cut, or rejected after measuring)

| Version | Change | Added / cut / rejected | Measured on | Result | Commit |
|---|---|---|---|---|---|
| 1.0.0 | Initial filter, written before the build | — | — | — | (this commit) |
