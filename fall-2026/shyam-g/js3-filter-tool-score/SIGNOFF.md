# Sign-off: Job-Search Agent 3

> Drafted by Claude Code on 2026-11-23 from the commits and outputs in this folder.
> The reject-audit line below can't be true until you've run `python audit.py label`.

**Checked:**
- The filter reads its rules from FILTER.md, and the header version matches the JSON block:
  `tests/test_filter.py::test_rules_come_from_the_document`.
- All four wrong versions are caught. The wrong implementation gives the wrong answer and the real one
  doesn't: `tests/test_wrong_versions.py` (W1 substring, W2 ranking without exclusion, W3 missing
  location, W4 occurrence-as-support). 21/21 tests pass (`evidence/03-pytest.txt`).
- The location gate, years rule, role-word rule, and threshold boundary: `tests/test_filter.py`.
- The evidence labels and abstention rule, including a pinned counterexample: `tests/test_evidence.py`.
- The MCP server's protocol and error paths (parse error, unknown method, unknown tool, extra
  argument, path-like id), and no network or subprocess imports: `tests/test_mcp_server.py`. Two real
  clients exercised it: my `mcp_client.py`, and Claude Code 2.1.316 (`transcripts/`).
- Reject audit: 0 of 27 decided random rejects wrong by my hand verdict (3 unsure; 95% exact interval
  0%–12.8% of the 624 rejects in this corpus, a sample estimate). Non-location rejects 1/9 wrong, close
  calls 10/19, other keeps 2/3: the filter's errors are mostly false *keeps*, not false rejects
  (`reports/AUDIT.md`). P1–P5 re-measured against these verdicts (FILTER.md §7).
- Held-out measurement of one change at a time: `reports/SCORE-REPORT-data.md` (E0–E5).

**How:**
- By hand: the 66 audit verdicts (`labels/audit_sheet.csv`, judged blind to the filter's decision,
  entered via `labels/audit_verdicts_edit.csv` + `audit.py import`). After the first import, Claude Code
  pointed out 5 verdicts that contradicted my own checklist; I changed 4 of them (A026, A031, A052,
  A058) to not relevant. Those 4 changes were prompted by Claude, not blind (FRICTIONAL row 13);
  the JS1 dev/held-out labels (October, before JS3 existed); the claim spot-check
  in `reports/SHORTLIST-NOTES.md` §4: 10 random Claude claims (seed 7375), I agreed with
  the computed label on 5 of 10.
- By a test written before reading Claude's code: **none.** Claude Code wrote both the code and the
  tests in this session. The tests assert rules from FILTER.md, and v1.0.0 was committed before any
  code (85730d3). They're still Claude-written tests of Claude-written code.
- By recomputation: the experiment table is recomputed from the saved raw Claude responses
  (`experiments.py report`), and the shortlist labels from saved responses (`shortlist.py`).
- With Claude's help: all code, the tests, and the first drafts of every document (SOURCES.md says which parts).

**Not checked:**
1. The computed claim labels beyond my 10-claim spot check. On those 10 I agreed with 5: the checker
   asks "is it required?" while I judged "is the sentence true?", it misses "Entry Level" titles, and it
   missed one duty sentence (SHORTLIST-NOTES §4). I also labeled two identical "5+ years" claims differently.
2. Run-to-run variance of Claude's verdicts. Each E3–E5 condition ran once per posting.
3. The held-out labels were visible to Claude Code during the build, so E2 and E3b are contaminated (SCORE-REPORT §3).
4. Anything about spotify and palantir beyond the location gate. Every posting there failed it, so no
   label, no shortlist entry, and no audit judgment beyond "not in Boston" covers those boards.
5. A runtime network capture of my MCP server (the "no network" claim is a static source check).
6. The Palantir "supply chain" boilerplate false friend is documented, not fixed (FALSE-FRIENDS.md).
7. Postings newer than 2026-11-10. The corpus is a snapshot, and the server can't tell whether a job is still open.

**Not claiming:**
- That the filter finds the jobs worth my time. It finds postings whose words match a fictional persona.
- Any false-reject *rate* for postings in general. The audit is a sample estimate for one corpus on one day.
- That any of the Claude prompts or the threshold-3 setting is better in general (n = 10, contaminated).
- That the tool server is safe for any client or any data other than the ones tested here.

**Signed:** Shyam Sundar Jayaraman Gopalakrishnan, 2026-11-25

## Driver's seat

| Part | What Claude should do | What I should do | Why this stays mine |
|---|---|---|---|
| The filter (FILTER.md) | Draft rules, implement them, measure every proposed change (corpus diff, labels) | Decide each add / cut / reject; sign the version | Which jobs are "relevant" is a statement about my own career. A measurement can inform it but can't make it |
| The reject audit | Draw the sample, build the blind sheet, compute the interval | Judge every posting myself, without seeing the filter's decision | An audit graded by the thing being audited checks nothing |
| The shortlist | Write justifications with verbatim quotes; label claims mechanically | Spot-check claims; read the posting before I act on any "relevant" | "Supported" means the words are there. Whether the job fits me is a different question |
| The tool server | Write it, test it, expose only a read-only scoring tool | Decide which clients may connect and which tools they may call | A client isn't entitled to trust a server's self-description. That trust decision is mine (TOOL-EVALUATION.md) |
| The score | Run one-change experiments and report them with their limits | Decide whether any change ships (I didn't ship threshold 3) | n = 10 and contaminated labels don't justify a change; I have to own that call |
| Whether a posting is worth my time | Nothing beyond surfacing it with its evidence and its "I cannot tell"s | Read it, weigh pay, visa sponsorship, team, growth, and how I feel about it | The agent sees words. It can't see my visa timeline, my goals, or what I'd regret. The agent never applies, emails, messages, or logs in |
