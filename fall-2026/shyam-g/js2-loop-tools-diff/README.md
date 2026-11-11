# Job-Search Agent 2 — the loop, the tools, and the diff

A bounded loop that watches four public job boards across two applicant-tracking systems
(Greenhouse, Lever). One of the four fails on purpose. Every fetch, read, and write goes through a
permission policy enforced in code. An independent check catches runs that finish cleanly and are
still wrong.

**Started from:** my Job-Search Agent 1 (`../js1-contract-and-watch`). The relevance rule and the
fictional persona are reused unchanged. See SOURCES.md.

## Toolchain
- Python 3.12.5, standard library only for the agent
- pytest 9.2.0 (`requirements.txt`), for the tests only
- Windows 11 / PowerShell. On macOS or Linux, use `.venv/bin/python` in place of `.venv\Scripts\python.exe`.

## Commands (from a fresh clone)
```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest tests -q

# 1. the real run, including the deliberate failure (nosuchboard-js2-xyz -> HTTP 404)
.venv\Scripts\python.exe agent2.py run --label live
.venv\Scripts\python.exe check.py jobs/runs/<that-run-dir>

# 2. the finished wrong answer (SEEDED, offline replay of run 1): exits "finished", check.py fails it
.venv\Scripts\python.exe agent2.py run --boards config/boards-clean.json --replay jobs/runs/<run-1-dir> --inject-empty formlabs --label SEEDED-finished-wrong --no-state
.venv\Scripts\python.exe check.py jobs/runs/<that-run-dir>

# 3. retry policy on a timeout (SIMULATED)
.venv\Scripts\python.exe agent2.py run --simulate-timeout spotify --label SIMULATED-timeout --no-state

# 4. offline reproduction of any saved run (no network)
.venv\Scripts\python.exe agent2.py run --replay jobs/runs/<dir> --label replay --no-state
```
Exit codes: `agent2.py` returns 0 finished, 2 incomplete, 3 budget_exhausted, 4 error, 5 policy
violation. `check.py` returns 0 passed, 1 failed, 2 unchecked boards.

## What each run writes (only under `jobs/`, enforced by `js2/policy.py`)
`jobs/runs/<timestamp>-<label>/` contains `report.json` (exit status and per-board results),
`trace.jsonl` (every observation, including policy decisions), and `raw/` (saved raw responses
plus `index.json`). Per-board seen ids go in `jobs/state/`.

## Files
| Path | What | Written by |
|---|---|---|
| `GATE.md` | exits, budgets, repeat rule, error policy, permission policy, wrong versions | me |
| `labels/hand_labels.csv` | hand counts per board, taken before any run or Claude call | me |
| `config/*.json` | boards, budgets, policy (must match GATE.md) | Claude defaults, edited by me |
| `js2/loop.py` | the bounded loop | Claude Code |
| `js2/policy.py` | permission policy enforcement | Claude Code |
| `js2/providers.py` | Greenhouse + Lever | Claude Code |
| `js2/rule.py` | relevance rule from JS1 | me (JS1) |
| `agent2.py` | CLI | Claude Code |
| `check.py` | independent check; imports nothing from `js2/` | Claude Code |
| `BOUNDARY-TESTS.md`, `tests/test_boundary.py`, `tests/test_loop.py` | predictions + tests | me |
| `REVIEW.md` | review packet | me |
| `SIGNOFF.md` | sign-off + driver's seat | me |
| `evidence/` | console output of the runs I submit | me |

## What ran (all on 2026-11-10, ET; outputs in `evidence/`, run folders in `jobs/runs/`)
| When | Command | Result |
|---|---|---|
| 14:43 | `agent2.py run --label live` | exit `incomplete`: formlabs 249, spotify 86, palantir 304; `nosuchboard-js2-xyz` HTTP 404 → `count=None`. `check.py` **FAILED**: +1 drift on formlabs and spotify vs. hand labels (tolerance 0); palantir ok; 404 board ok (no count invented). `evidence/01` |
| 14:43 | SEEDED: `--replay` the live run, `--inject-empty formlabs`, `boards-clean.json` | exit **`finished`** (code 0), formlabs reported 0. `check.py` **FAILED** it: "FINISHED-WRONG… agent 0, hand 248". `evidence/02` |
| 14:43 | SIMULATED: `--simulate-timeout spotify` | spotify: 2 attempts, then error with no count; exit `incomplete`. `evidence/03` |
| evening | `pytest tests -v`, before the patch | 20 passed, 5 failed (row 14; GATE 6.1, 6.2, 6.3; 6.6c redirect followed). `evidence/04` |
| 21:39 | `pytest tests -v`, after the redirect patch `23888ac` | 21 passed, 4 failed (6.6c now passes; the other 4 unchanged). `evidence/05` |
| 21:39 | `agent2.py run --label after-patch --no-state` | formlabs 250, spotify 86, palantir 304; 404 board `count=None`. `jobs/runs/2026-11-10T213906-after-patch/` |

The 4 tests that still fail are open, not hidden: my GATE's status names (`bad_name`, `ok_empty`,
`failed`) differ from the code's (`error`, `ok`), and row 14 was my wrong prediction. See SIGNOFF.md.
