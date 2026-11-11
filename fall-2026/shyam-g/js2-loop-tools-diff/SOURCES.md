# SOURCES

## Started from
- My own Job-Search Agent 1 (`js1-contract-and-watch/`): the relevance rule and résumé validation
  (copied unchanged into `js2/rule.py`), the fictional persona `persona/jordan_rivera.json`, and
  the Greenhouse board `formlabs`.

## Public endpoints used (read-only, no login)
- Greenhouse Job Board API: `https://boards-api.greenhouse.io/v1/boards/<token>/jobs`
- Lever Postings API: `https://api.lever.co/v0/postings/<company>?mode=json`

## What Claude Code contributed (Claude Code, model Claude Opus 5.5, session of 2026-11-10)
Written by Claude Code at my request:
- `js2/loop.py`: bounded loop, four exits, budgets, repeat rule, retry/no-retry error handling, trace
- `js2/policy.py`: permission policy enforcement (hosts, methods, read/write roots, symlink and
  prefix-safe path checks, approval for overwrites, forbidden actions)
- `js2/providers.py`: Greenhouse and Lever URL builders, parsers, HTTP error classification
- `agent2.py`: CLI, raw-response saving, per-board state, SEEDED / SIMULATED / REPLAY modes
- `check.py`: the independent check (shares no code with the agent)
- `tests/conftest.py`: fixtures only, no assertions
- `tests/test_boundary.py` and `tests/test_loop.py`: written by Claude Code at my request on
  2026-11-10, AFTER I committed my predictions (92c6a6d) and GATE.md section 6 (2f256e7).
  Each test asserts my prediction or my GATE rule as written. I did not write the test code itself.
- The Test name and Actual columns in BOUNDARY-TESTS.md, filled in from the real pytest output
- `config/*.json`: proposed default values, to be replaced by my decisions in GATE.md
- Empty templates: GATE.md, BOUNDARY-TESTS.md, REVIEW.md, SIGNOFF.md, FRICTIONAL.md, labels/

- `js2/providers.py` redirect patch (commit 23888ac), my review-packet change
- `check.py` fix: a blank hand count is UNCHECKED instead of a crash (b9aae78)
- Draft text that I edited and own: REVIEW.md sections 1–5 and 7–8, SIGNOFF.md, the FRICTIONAL.md rows,
  and README "What ran" (from the real outputs in evidence/)

Written by me: GATE.md (2f256e7), labels/hand_labels.csv (c9be3ec, e930977), the BOUNDARY-TESTS.md
predictions (92c6a6d) and row 14 note, the edits and decisions in REVIEW.md, SIGNOFF.md and
FRICTIONAL.md, and the commands in REVIEW.md section 6, which I ran myself.

## What I accepted, modified, or rejected
- Accepted the agent code, but made my GATE the authority. Its 6 disagreements are logged, and 4 are still open.
- Accepted the redirect patch on evidence (REVIEW.md section 7).
- Did not accept changing my wrong row 14 prediction, or loosening the tolerance after seeing the drift.
- No Claude output is used inside the agent. JS2 makes no Claude calls at run time.
