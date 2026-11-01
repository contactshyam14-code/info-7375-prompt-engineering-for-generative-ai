# Job-Search Agent 1 — contract and watch

Watches one public Greenhouse board (`formlabs`, host `boards-api.greenhouse.io`), reports only
postings new since the last run, and judges each one twice: by the written rule in
[CONTRACT.md](CONTRACT.md) (a **record**, recomputable by hand) and by Claude under a prompt
contract (a **judgment**, labeled as one and validated).

## Toolchain
- Python 3.12.5, standard library only for the agent
- pytest 9.2.0 (`requirements.txt`)
- Claude Code CLI (`claude -p`) for the Claude judge. Each call is a fresh, tool-less
  conversation. No API key lives in this repo.
- Windows 11 / PowerShell. On macOS or Linux, use `.venv/bin/python` in place of `.venv\Scripts\python.exe`.

## Commands (from a fresh clone)
```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest tests -q            # offline, 20 tests

# the seeded two-run demo (reproduces evidence/01-seeded-two-runs.txt)
.venv\Scripts\python.exe agent.py run --board formlabs --from-file seeded/formlabs-earlier-SEEDED.json --label seeded-run1 --state state-seeded
.venv\Scripts\python.exe agent.py run --board formlabs --from-file state/raw/2026-10-31T223703-formlabs-live.json --label seeded-run2 --state state-seeded --claude

# the watch (rule only; add --claude for Claude's judgment)
.venv\Scripts\python.exe agent.py run --board formlabs --label live
# seeded second run against a saved response:
.venv\Scripts\python.exe agent.py run --board formlabs --from-file <saved.json> --label seeded

# Step 4 (needs hand labels filled in first; study.py refuses otherwise)
.venv\Scripts\python.exe study.py sample --raw state/raw/<file>.json --ids <5 ids> --n 4
.venv\Scripts\python.exe study.py experiment --raw state/raw/<file>.json --prompt prompts/baseline.txt --split dev
```

## Files
| Path | What |
|---|---|
| `CONTRACT.md` | the gate, written 2026-10-30 before any code; amendments dated in section 8 |
| `tests/test_contract.py` | written before implementation; red run in `evidence/00-red-run-before-implementation.txt` |
| `tests/test_extra.py` | added by Claude after implementation (allow-list, HTML stripping, no contact details sent to Claude) |
| `agent.py` | the watch, the rule, the validator, the Claude call |
| `allowlist.txt` | the only hosts the agent may fetch |
| `prompts/` | prompt contracts (baseline, plus one revision) |
| `state/seen_ids.json`, `state/raw/` | live state: remembered ids and every saved raw response |
| `seeded/`, `state-seeded/` | SEEDED demo: a constructed earlier response and its separate state |
| `evidence/` | red run; console output of the two seeded runs |
| `ACTION-SURFACE.md`, `surface/` | Chapter 3 comparison and its two real runs |
| `SAMPLING.md`, `EXPERIMENT.md` | Chapter 1 and Chapter 2 reports |
| `SOURCES.md`, `FRICTIONAL.md` | who did what; what went wrong |
| `output/` | one JSON report per run |
| `labels/hand_labels.csv` | 20 postings, 10 dev / 10 held-out, hand-labeled |
| `study.py`, `results/` | sampling and prompt-experiment runs |

## What ran
| When | Command | Result |
|---|---|---|
| 2026-10-30 12:20 | `pytest tests -q` (no `agent.py` yet) | red: `ModuleNotFoundError: agent` |
| 2026-10-31 | `pytest tests -q` | 20 passed |
| 2026-10-31 22:37 | `agent.py run --board formlabs --label live` | baseline: 238 postings, 0 new, raw saved |
| 2026-10-31 22:41 | SEEDED run 1: `--from-file seeded/formlabs-earlier-SEEDED.json --state state-seeded` | baseline: 233 postings, 0 new |
| 2026-10-31 22:41 | SEEDED run 2: `--from-file state/raw/...-live.json --state state-seeded --claude` | 5 new (exactly the 5 removed); rule and Claude agree on all 5; 8311099 relevant |
| 2026-10-31 22:42 | action-surface Ways 1 and 2 (`surface/runs.txt`) | both `relevant` for 8311099 |
| — | live run on a second calendar day | **not done** before the 2026-10-31 deadline; the second run is seeded |
| 2026-10-31 22:48–23:07 | `study.py sample` (5×4) and `study.py experiment` baseline on dev and held-out | 40 Claude outputs, all valid; 8161780 flipped 1 of 4; **unscored: hand labels not completed** |

The seeded run 1 is **constructed**: the live response minus its 5 most recently published postings, standing in for an earlier day. It is labeled SEEDED in its file name, its `_note`, and the evidence log.

Decision recorded in code (`agent.STRIP_HTML`): HTML in `content` is unescaped and stripped before matching.

## Sign-off — Job-Search Agent 1
_Draft by Claude, facts only. Edit, then sign or withhold._

**Checked**
- Rule verdicts on 10 constructed postings, including the word-boundary traps: `test_each_id_gets_its_own_verdict`, `test_word_boundary_traps`
- The validator rejects 8 kinds of bad Claude output (cites nothing, nonexistent fields, wrong id, extra key, code fences, ...): `test_validator`
- The baseline reports nothing new, and run 2 reports only added ids: `test_baseline_reports_none_new`, `test_second_run_reports_only_new_ids`; also shown on real data in `evidence/01-seeded-two-runs.txt`
- Allow-list refusal, HTML stripping, no contact details in the prompt: `tests/test_extra.py`

**How**
- `test_contract.py` came from the kit and was in place before `agent.py`; the red run is in `evidence/00-...`
- `test_extra.py` was written by Claude *after* the code
- One record (8311099): _student to recompute by hand before signing_

**Not checked**
- Whether the rule's or Claude's verdicts are *right*: the 20 hand labels were not completed, so the sampling and the prompt experiment are unscored and no prompt revision was run
- Greenhouse responses that lack `location` or `content`, pagination, or rate limits
- Two runs on two real calendar days (the second run so far is seeded)
- Prompt injection inside posting text
- Behaviour across Claude model versions (the CLI default model was used and not pinned)

**Not claiming**
- That Claude's verdict is a fact, or that it agreeing with the rule makes either one correct
- Anything beyond one board (Formlabs) and one fictional persona. Some Formlabs postings are not in English (e.g. 8220243, Italian), and the rule's English keywords cannot match them.

**Signed or withheld:** ____________ (name, date)

## Driver's seat
_Draft; confirm against what actually happened._

| Part | Claude does | I do | Why it stays mine | Where the split shows |
|---|---|---|---|---|
| Contract | drafts | rewrite; decide the rule, board, HTML | the rule encodes what I count as worth a day | CONTRACT header and section 8 |
| Tests | runs them | wrote/kept them before the code | otherwise the tests just mirror the code | `evidence/00-red-run-before-implementation.txt` (2026-10-30) |
| Code | writes `agent.py`, `study.py` | run the tests myself; read the diff | I sign for what it does | session 2026-10-31: "keep Formlabs and HTML stripping, update CONTRACT.md, finish it" |
| Hand labels | nothing (`study.py` refuses until they exist) | label 20 postings | ground truth can't come from the judge being graded | `study.py` refusal check |
| Prompt revision | runs it | choose the one change | choosing it after seeing held-out results would be overfitting | `EXPERIMENT.md` |
| Sign-off | drafts the facts | decide what was not tested; sign | only I know what I didn't check | this section |
