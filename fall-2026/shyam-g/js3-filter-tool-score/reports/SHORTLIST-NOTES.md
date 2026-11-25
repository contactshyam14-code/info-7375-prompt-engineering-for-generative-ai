# Shortlist notes: relevance vs. entailment, the abstention rule, and its limits

Companion to `reports/SHORTLIST.md` (generated, filter v1.2.0, 11 postings, 64 Claude claims +
33 computed gate claims, every one labeled). The labels there are computed by `js3/evidence.py`.
This file holds the cases I'm making an argument about, and the places where the computed label
and the posting text disagree.

## 1. Relevance is not entailment: "Technical Program Manager - Entry Level" (8249069, Boston)
- **Why it's on the shortlist:** strong role word "program manager" (3) + topic word "supply chain"
  (1) = 4 = the threshold. Without "supply chain" it would be rejected.
- **The only place "supply chain" occurs:** "Have the ability to work cross-functionally between
  product, engineering, production, and supply chain personnel."
- **Claude's claim (2026-11-23):** "The role involves working with supply chain personnel, which draws
  on the candidate's supply chain …" (`reports/claude/shortlist/8249069.json`).
- **Label: insufficient.** The sentence says the job works *with* supply-chain people. It doesn't say
  the job does supply-chain work or needs supply-chain skill. The word matched, so the posting is
  *relevant* to the filter, but the claim isn't *entailed* by the text.
- The same pattern holds for both "Materials Program Manager" postings (8334912, 8335124): identical
  sentence, also kept at exactly 4.
- Without the collaboration-mention rule, the checker's cue list would have labeled this **supported**,
  because the sentence has the term and a cue-like verb ("work"). Claude Code wrote that rule into the
  checker after reading this sentence in the v1.0 run. It's recorded in FILTER.md §3 and §7 as a v1.1
  addition. It sits in the checker only. The filter still scores the word.

## 2. The abstention rule
FILTER.md §3: check three gate claims (role from the title, location from the location field,
experience from a stated years figure). Any *contradicted* gives "not relevant". Otherwise any
*insufficient* gives **"I cannot tell"**, naming the claim. Only three *supported* give "relevant".
On this shortlist: 6 relevant, 5 "I cannot tell", 0 not relevant.

| Posting | Verdict | Unsettled claim | What text would settle it |
|---|---|---|---|
| FP&A Analyst | I cannot tell | role | FP&A is finance, not one of the role words. My label: I'd want the title to say planning or analyst in an operations sense |
| Fulfillment Coordinator - May 2027 Graduates | I cannot tell | role, experience | a years figure; "coordinator" is only a weak role word |
| Mechanical Project Manager | I cannot tell | experience | a years figure (the posting says "You don't need to check every box") |
| NPI Operations Program Manager | I cannot tell | experience | a years figure |
| Technical Program Manager - Entry Level | I cannot tell | experience | **already in the title**, see counterexample B |

## 3. Counterexamples that expose the rule's limits
**A. "Relevant" when it isn't: Supply Chain Engineer (8368295 Somerville / 8372071 Boston).**
All three gates are *supported*: title "supply chain", location Somerville/Boston, and "5+ years of
experience in chemical, specialty materials, polymer, coatings, adhesives…", where 5 ≤ 5. So the rule
says **relevant**. But the years are in chemical/materials manufacturing, a domain the persona
(supply chain analyst, SQL/SAP/forecasting) doesn't have, and "5+" means *at least* five. The rule
checks the **number**, not the **domain** or the direction of the "+". Pinned by
`tests/test_evidence.py::test_abstention_limit_counterexample`, which asserts the rule *does* say
"relevant", so the limit can't be fixed silently without anyone noticing.

**B. "I cannot tell" when the answer is right there: Technical Program Manager - Entry Level.**
The experience claim is *insufficient* because no years figure appears. But the title says "Entry
Level", and Claude's own experience claim quoted it. The rule only accepts a number, so it abstains
on a posting whose seniority is stated in words.

**C. The rule is only as good as the extractor (found and fixed).** With checker v1.1, Strategy &
Operations Analyst got "I cannot tell" because the extractor didn't read "Experience: 2–4 years in
consulting…", and the FP&A posting's "1-3 years of progressive FP&A … experience" was also missed.
Claude's claims had both figures right. Fixed in v1.2 (FILTER.md §7, P6). The before-snapshot is
`reports/shortlist-checker-v1.1.json`. The fix brought a false positive I accepted: "our 3 years of
growth and customer experience" reads as 3 (pinned in `tests/test_filter.py`).

**D. What the rule never asks:** work authorization, sponsorship, clearance, pay, travel. A posting
can pass all three gates and still be out of reach for reasons the rule doesn't look at.

## 4. Where the computed label and the text disagree (read by Claude Code, 2026-11-23; not my hand verdicts)

| Posting | Claim | Computed | Reading of the text |
|---|---|---|---|
| Fulfillment Coordinator, Mechanical PM, S&O Analyst, Supply Chain Engineer ×2 | 5 skill claims whose line sits under a "Bonus Skills:" / "Bonus Points" header | **supported** under checker v1.1, **insufficient** under v1.2 | the v1.2 soft-section rule fixed these. Claude's own claim text had called each one "a bonus" |
| Supply Chain Engineer | experience claim "5+ years" → **supported** | supported | see counterexample A |
| Supply Chain Engineer ×2 | "advanced Excel/Sheets required" | **insufficient** under v1.1, **supported** under v1.2 | fixed by adding "required" to the cue words |
| Global Sourcing Manager | procurement claim, quote "Manage supplier selection, negotiation, and contract execution" | insufficient (quote doesn't name the word) | the duty *is* procurement work in substance. The checker only accepts the literal word, so this one is a false *insufficient* |
| all postings | 13 "other"-type claims (pay range, "apply even if you don't check every box", MBA) | insufficient: "needs a hand label" | no entailment rule exists for free-form claims. The quotes are verbatim, but the checker can't judge them |

**Owner hand check (to do before signing):** spot-check at least 10 of the 64 Claude claims in
`reports/SHORTLIST.md` against the posting URLs and record agree/disagree here.

The 10 claims below were drawn at random by Claude Code (Python `random.Random(7375)`: 5 of the 31
*supported*, 5 of the 33 *insufficient*), so the selection isn't cherry-picked. The last two columns are mine.
My label: `supported` (the quote shows the claim is true), `contradicted` (the posting says the opposite), or
`insufficient` (the quote doesn't really show it).

| # | Posting (open the link) | Claude's claim | Quote Claude gave | Computed label | My label | Agree? |
|---|---|---|---|---|---|---|
| 1 | [Materials Program Manager, Boston, MA](https://careers.formlabs.com/job/8335124/apply/?gh_jid=8335124) | The role is a program management position, matching the candidate's interest in project/product manager roles. | "Use disciplined project management methodology to define scope, develop program plans which deliver the program within cost and schedule" | supported | supported | yes |
| 2 | [Strategy & Operations Analyst, Somerville, MA](https://careers.formlabs.com/job/8311099/apply/?gh_jid=8311099) | The role is an operations analyst position aimed at early-career candidates, matching the candidate's target of operations analyst roles. | "This is a role for someone early in their career with a very strong ability to learn quickly" | supported | supported | yes |
| 3 | [Supply Chain Engineer, Boston, MA](https://careers.formlabs.com/job/8372071/apply/?gh_jid=8372071) | SQL is listed as a plus, and SQL is one of the candidate's skills. | "SQL, Python, or Tableau a plus" | insufficient | supported | no |
| 4 | [Materials Program Manager, Boston, MA](https://careers.formlabs.com/job/8335124/apply/?gh_jid=8335124) | The posting asks for 5+ years of experience, which is at the top edge of the candidate's 5-years-or-less range, though it also encourages applicants who don't meet every requirement. | "5+ years of experience in an engineering or R&D environment, with demonstrated experience in project or program management." | supported | insufficient | no |
| 5 | [Technical Program Manager - Entry Level, Boston, MA](https://careers.formlabs.com/job/8249069/apply/?gh_jid=8249069) | The posting is labeled entry level, which fits a candidate with 5 years of experience or less. | "Technical Program Manager - Entry Level" | insufficient | supported | no |
| 6 | [Fulfillment Coordinator - May 2027 Graduates, Somerville, MA](https://careers.formlabs.com/job/8249635/apply/?gh_jid=8249635) | The role involves inventory reconciliation work, matching the candidate's inventory skill. | "Implement inventory reconciliation tasks by assisting in weekly cycle counts and investigating discrepancies between physical warehouse stock and digital records." | insufficient | supported | no |
| 7 | [FP&A Analyst, Somerville, MA](https://careers.formlabs.com/job/8074475/apply/?gh_jid=8074475) | The role involves owning inventory forecasting models, matching the candidate's inventory and forecasting skills. | "Build and maintain financial models, for example, inventory and COGS forecasts grounded in unit economics" | supported | supported | yes |
| 8 | [NPI Operations Program Manager, Somerville, MA](https://careers.formlabs.com/job/8103603/apply/?gh_jid=8103603) | The posting encourages applicants who do not meet every listed requirement to apply anyway. | "Even if you don't check every box, but see yourself contributing, please apply." | insufficient | supported | no |
| 9 | [Materials Program Manager, Somerville, MA](https://careers.formlabs.com/job/8334912/apply/?gh_jid=8334912) | The posting asks for 5+ years of experience, which sits at the upper edge of the candidate's 5-years-or-less range and may be a stretch. | "5+ years of experience in an engineering or R&D environment, with demonstrated experience in project or program management." | supported | supported | yes |
| 10 | [NPI Operations Program Manager, Somerville, MA](https://careers.formlabs.com/job/8103603/apply/?gh_jid=8103603) | The posting states a base pay range starting at $100,000 and also includes equity. | "The annual base pay range for this role is: $100,000 — $186,000 USD" | insufficient | insufficient | yes |

**Result (my hand labels, 2026-11-25; also in `labels/spotcheck_edit.csv`): I agreed with the computed label on 5 of 10.**

- 4 disagreements (rows 3, 5, 6, 8) are computed *insufficient* where I said *supported*. In rows 3 and 8 the
  claim itself is literally true as worded ("SQL is listed as a plus"; "encourages applicants who don't meet
  every requirement to apply"). The checker asks a different question, whether the skill is *required*, so its
  "insufficient" is right for the filter's purpose and wrong as a judgment of the sentence. That is the
  relevance-vs-entailment gap again, inside the checker.
  Row 5 is the known "Entry Level"-in-the-title miss (counterexample B): the checker only reads years.
  Row 6 is a plain checker miss: "Implement inventory reconciliation tasks … weekly cycle counts" is a duty
  sentence, but none of the checker's requirement cue words appear in it. Not fixed.
- 1 disagreement (row 4) is computed *supported* where I said *insufficient*: "5+ years" for a ≤5-year candidate.
- Rows 4 and 9 are the same kind of claim ("5+ years … upper edge of the range") on the two Materials Program
  Manager postings, and I labeled them differently (insufficient vs. supported). I left both as I entered them;
  this inconsistency is part of what my hand labels show.
- 10 claims is a spot check, not a measurement of the checker's accuracy on all 64.
