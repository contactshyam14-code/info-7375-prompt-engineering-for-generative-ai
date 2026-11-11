# Sign-off — Job-Search Agent 2

**Checked:**
- Permission policy: 13 of my 14 predicted boundary cases matched (tests/test_boundary.py,
  evidence/04). Row 14 was my wrong prediction.
- A failed board is never given a count: the 404 board reported count=None (evidence/01,
  test_6_1).
- Finished wrong answer: the SEEDED empty formlabs run exited "finished" (code 0) and check.py
  failed it, 0 vs. my hand count of 248 (evidence/02).
- Retry policy: the simulated timeout made exactly 2 attempts, then failed (evidence/03, test_6_3).
- Redirect hole: test_6_6c went red then green (c64bf5c → 23888ac), and I reran the tests myself
  (REVIEW.md section 6).

**How:** I counted the boards by hand on the public pages (c9be3ec). I wrote GATE.md (2f256e7) and
the boundary predictions (92c6a6d) myself, before any test existed. Claude Code wrote the test code
from my committed predictions and GATE section 6, and wrote the agent code (see SOURCES.md).
check.py recounts from the saved raw files and imports nothing from the agent.

**Not checked:**
1. Board drift: my tolerance was 0, so the live check flagged 248→249 and 85→86. I did not set
   or justify a tolerance.
2. Four tests still fail, where my GATE names (bad_name, ok_empty, failed) differ from the code's
   names (error, ok). Left open: I'd either amend GATE.md to the code's names or change the code,
   and I didn't decide in time.
3. Lever and Greenhouse pagination, and boards larger than one response.
4. Windows junctions (only a symlink was tested).
5. The relevance rule only matches English keywords, so non-English postings are never marked
   relevant.

**Not claiming:** that the relevance rule finds good jobs, that the agent works on any other ATS,
or that a "finished" run is correct without check.py.

**Signed:** Shyam Sundar Jayaraman Gopalakrishnan, 2026-11-10

## Driver's seat

| Part | What Claude should do | What I should do | Why this part stays mine | Evidence |
|---|---|---|---|---|
| The loop | Write the loop, providers, retry and trace code | Decide the exits, budgets, retry count and what counts as failure (GATE.md) | Only I can decide what "done" and "safe" mean for my search | 2f256e7 GATE; f38bc0e code |
| The review | Propose and write the patch | Name the defect in advance, get the red test, read the diff, decide | Accepting code is a judgment I sign for | GATE §6 item 6; c64bf5c → 23888ac; REVIEW §7 |