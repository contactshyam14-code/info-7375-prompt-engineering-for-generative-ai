# FILTER.md: the gate for Job-Search Agent 3

**Version:** 1.2.0 (v1.0.0 written 2026-11-23 before any filter code existed, commit 85730d3; v1.1.0 and v1.2.0 changes are in section 7)
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
  "version": "1.2.0",
  "require_role_word": true,
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
4. **Role word required (v1.1).** If the title has no strong or weak role word, reject
   (`reject:no_role_word`), whatever the topic score.
5. **Score.** `role_strong` (3) if the title has a strong role word, otherwise `role_weak` (1) if
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
| A role word is required (v1.1) | In v1.0, "Startup Founder" was kept on topic words alone ("excel" as a verb, "setting up a supply chain"). Topic words show what the job touches. The title shows what the job is. |
| Threshold 4 | A strong title plus one topic word, or a weak title plus three topic words. Hand-set, not fitted (see SCORE-ORIGINS.md). |

## 3. Evidence rules (applied to every claim in a shortlist justification)

A **claim** is one sentence of the form "this posting has property P", with the claim type
and, wherever possible, a **quote** copied from the posting.

| Label | When |
|---|---|
| **supported** | The quote appears **verbatim** (whitespace-normalized) in the posting's title, location, or text, **and** the quote itself states P: for a skill claim, it names the skill outside a negation ("not required", "no … needed", "nice to have" counts as *insufficient*, not supported). For location, the location field satisfies the gate. For experience, the posting states a years figure ≤ `max_years` and none above it. |
| **contradicted** | The posting's own text states not-P: a location field that names a place outside the gate with no "remote"; a years figure above `max_years`; a title exclusion word; or a skill named only in a negation. |
| **insufficient** | Neither. Includes: no quote, a quote not found verbatim, a term that appears only in boilerplate (benefits, EEO, "about us"), a skill listed as "nice to have"/"bonus"/"preferred", and no years figure stated at all. |

**Collaboration mentions (added in v1.1 after measuring).** If a topic term is followed directly by
"personnel / team(s) / partners / stakeholders / organization / group(s) / functions", it names people
the job works *with*, and the skill claim is *insufficient*. Example: "work cross-functionally
between product, engineering, production, and supply chain personnel."

**Requirement sentences and soft sections (v1.2).** A skill claim is *supported* only if its
sentence reads as a duty or requirement (a cue such as "experience", "proficiency", "required",
"must", "comfortable", "writing", "manage"). A sentence that sits under a "Bonus / Bonus Points /
Nice to have / Preferred" header is *insufficient* (nice-to-have), even if the sentence itself says
"proficiency".

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
- False friends found in v1.0 (see reports/AUDIT.md and FALSE-FRIENDS.md): "excel" as a verb
  ("You excel at hiring"), "supply chain" as a collaboration mention ("supply chain personnel"),
  and "staff" in "Operations Staff" (a junior role, not the "Staff" seniority rung).

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
| 1.0.0 | Initial filter, written before the build | — | — | — | 85730d3 |
| 1.1.0 | P1: require a strong or weak role word in the title | **added** | corpus decision diff; JS1 dev labels (n=10) | 5 keeps → rejects (4× "Startup Founder", "Finance Systems Engineer"). JS1 dev agreement unchanged at 6/10. All 5 had scored only on topic words; 2 of the 4 founder hits came from "excel" used as a verb | `reports/rule-changes/P1-require-role-word.json` |
| — | P2: cut "staff" from title_exclude ("Accounting & Operations Staff" is junior, not a "Staff" ladder rung) | **rejected** | corpus diff | 0 decisions change. Those postings already fail the location gate. Kept as a known false friend in section 5 | `P2-cut-staff.json` |
| — | P3: cut "excel" from topic words (false friend: "You excel at…") | **rejected** | corpus diff | 4 keeps → rejects, the same founders P1 already removes. But "Advanced use of Microsoft Excel" is a real persona skill in 6 sourcing/ops postings, so cutting the word throws away real evidence. P1 fixes the symptom; the false friend stays documented | `P3-cut-excel.json` |
| — | P4: cut "intern"/"internship" from title_exclude | **rejected** | corpus diff; JS1 dev labels | 4 rejects → keeps (sourcing/ops interns). JS1 dev agreement drops 6/10 → 5/10, because my JS1 hand label marked the sourcing intern not relevant | `P4-cut-intern.json` |
| — | P5: threshold 4 → 3 | **deferred** to SCORE-REPORT.md (a setting, measured once on held-out labels) | corpus diff | 4 rejects → keeps: 2× "Operational Excellence Lead", "Product Manager, Hardware/Software" | `P5-threshold-3.json` |
| 1.1.0 | Evidence rule: collaboration mentions are *insufficient* (section 3) | **added** | the Technical Program Manager case in SHORTLIST.md | "supply chain personnel" had been read as a supply-chain skill | (this commit) |

| 1.2.0 | Years extractor: also reads "1-3 years of progressive FP&A … experience" (up to 120 characters between) and "Experience: 2–4 years" | **added** | corpus decision diff; the 11 shortlist postings | 0 filter decisions change. In the shortlist, Strategy & Operations Analyst moves from "I cannot tell" to "relevant"; the FP&A experience claim moves from insufficient to supported. New false positive accepted: "our 3 years of growth and customer experience" reads as 3 (tests/test_evidence.py) | `P6-years-extractor-v1.2.json`, `reports/shortlist-checker-v1.1.json` (before) |
| 1.2.0 | Evidence: "required", "must", "comfortable", "writing" count as requirement cues | **added** | shortlist | "advanced Excel/Sheets required" and "Comfortable writing SQL" had been labeled insufficient | (this commit) |
| 1.2.0 | Evidence: lines under a Bonus / Nice-to-have / Preferred header are nice-to-have | **added** | shortlist | "Basic proficiency in Excel" (under "Bonus Skills:") and "ERP experience (e.g., … SAP …)" (under "Bonus Points") had been labeled supported. Claude's own claim text called both a bonus | (this commit) |

### Re-measured after the hand audit (2026-11-25)

Rows above were first measured on the corpus and JS1 dev labels only. After I judged the 66 audit
postings by hand (`labels/audit_sheet.csv`; 58 decided, 8 unsure and left out), every patch was
re-run with `measure_rules.py --base reports/rule-changes/_base_FILTER_v1.0.0.md` so it is measured
against the same v1.0.0 base it was proposed on. "Audit agreement" = share of the 58 where
keep/reject matches my verdict. The audit sample over-weights close calls, so this is agreement on
*this sample*, not an accuracy for the corpus.

| Change | Audit agreement before → after | What flips (my verdict) | Decision stands? |
|---|---|---|---|
| P1 role word | 45/58 → 50/58 (77.6% → 86.2%) | 5 keeps → rejects: 4× Startup Founder, Finance Systems Engineer (all *not relevant*) | **added**: confirmed |
| P2 cut "staff" | 45/58 → 45/58 | nothing | **rejected**: unchanged |
| P3 cut "excel" | 45/58 → 49/58 on v1.0.0; **0 changes on v1.2.0** | the same 4 founders P1 already rejects | **rejected**: confirmed; it only helps a filter without P1, and it would discard real Excel evidence |
| P4 cut "intern" | 45/58 → 42/58 (72.4%) | 4 interns → keeps: 3 *not relevant*, 1 unsure | **rejected**: confirmed by both label sets |
| P5 threshold 3 | 45/58 → 45/58 | Product Manager, Hardware (*relevant*), Operational Excellence Lead (*not*), 2 unsure | **not adopted**: no net gain |

Current filter v1.2.0 agrees with 50/58 audit verdicts (`reports/rule-changes/_current-v1.2-baseline.json`).

**New candidates the audit suggested, measured on v1.2.0, not adopted:**

| Change | Audit agreement | What flips | Decision |
|---|---|---|---|
| P7: add "engineer" to title_exclude | 50/58 → 52/58 | 2× Supply Chain Engineer keep → reject (*not relevant*) | **rejected for now** |
| P8: threshold 4 → 5 | 50/58 → 53/58 | 2× Materials Program Manager, Mechanical Project Manager (*not*), Technical Program Manager – Entry Level (unsure) keep → reject | **rejected for now** |

Why not adopt P7/P8 although they score higher: I proposed them *after* reading the disagreements
on these same 58 labels, so their gain is in-sample by construction. P7 also puts a field word into
a seniority list (the reject reason would say "seniority_title" for a non-seniority reason), and P8
would cut the shortlist from 11 to 7 on evidence from one sample. Both need labels they weren't
chosen on before they go in.
