# False friends: words that matched for the wrong reason

Found by running filter v1.0.0 on the 640-posting corpus (2026-11-10 snapshot) and reading the
context of every match that helped a posting. Counts come from one script run on 2026-11-23
(whole-word matching, the same `term_re` the filter uses). The contexts below are quoted from the
postings.

| Word | Matched where | Why it's wrong | Count in corpus | Effect on decisions | What I did |
|---|---|---|---|---|---|
| **"supply chain"** | Palantir company boilerplate: "…empower our partners to develop lifesaving drugs, forecast supply chain disruptions, locate missing children…" | It describes Palantir's customers, not the job. A software-engineer posting gets the topic point | **298 of 304** Palantir postings (301 of 304 mention it somewhere) | **None in this corpus**, because every Palantir posting fails the location gate (D.C., New York, London, Palo Alto…). A Palantir Boston office would turn this on at once | Documented. Not fixed: the boilerplate rule in `js3/evidence.py` only covers claims, not the filter's topic score. **Open.** |
| **"excel"** | "Adaptive Leadership: You **excel** at both hiring and leading teams" (Startup Founder); "Communication: **Excel** at organization and communication" (Operational Excellence Lead); "identify gaps where Formlabs can **excel**" | the verb, not the spreadsheet | 32 postings match "excel"; **13** have a verb-like use ("you/to/can/will excel", "excel at/in") | Helped keep 4× "Startup Founder" in v1.0.0 (score 4 with no role word) | v1.1.0 role-word rule (P1) removed those keeps. Cutting "excel" (P3) was **rejected**: "Advanced use of Microsoft Excel" is a real requirement in sourcing and ops postings |
| **"supply chain"** (second sense) | "Ability to work cross-functionally between product, engineering, production, and **supply chain** personnel" | names people the job works with, not supply-chain work | 4 postings with "supply chain personnel/team(s)/partners/stakeholders" | Gave the 1 topic point that put "Technical Program Manager - Entry Level" and both "Materials Program Manager" at exactly the threshold (4) | Evidence rule v1.1 labels these claims *insufficient*. **The filter still counts the word.** That's the relevance-vs-entailment case in SHORTLIST-NOTES.md |
| **"staff"** (an exclusion word) | "Accounting & Operations Staff", "Finance & Operations Staff" (Millbury, Ohio) | in these titles "staff" means a junior employee, not the senior "Staff Engineer" rung | 2 junior titles out of 9 "staff" titles | none (both fail the location gate) | Cutting "staff" (P2) was **rejected**: 0 decisions change, and 7 of the 9 titles are the senior rung |

The required example ("training" in an ML posting) doesn't come up for this persona: "training"
isn't in my word lists. The Palantir "supply chain" boilerplate is the same kind of failure, and a
bigger one. It shows that a high count of a matched word can describe the company and say nothing
about the job.
