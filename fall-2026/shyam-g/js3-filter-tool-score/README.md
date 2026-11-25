# Job-Search Agent 3: the filter, the tool, and the score

This layer decides which collected postings reach the (fictional) candidate, and why. It has four parts:
- a filter that **is** a versioned document (FILTER.md)
- a reject audit judged by hand
- a source-grounded shortlist in which every claim is labeled supported / contradicted / insufficient
- a from-scratch MCP tool server, used by Claude Code as a real client, and a one-change-at-a-time
  report on what moves the score

**Started from:** my own Job-Search Agent 2 (`../js2-loop-tools-diff`). The corpus is the raw responses
of its real run `2026-11-10T213906-after-patch` (640 postings: formlabs 250, spotify 86, palantir 304,
plus the deliberate 404 board). From JS1 (`../js1-contract-and-watch`) I reused the fictional persona
(Jordan Rivera), the relevance prompt (`prompts/relevance_A.txt` = JS1 `revision.txt`), and my 20 hand
labels (10 dev / 10 held-out). I did not use the Reallocation Engine or Lectern code. The idea that
"the filter is a document with every added, cut, and rejected word recorded" comes from Lectern's description.

## Toolchain
- Python 3.12.5. The agent, filter, server, and client use the **standard library only**.
- pytest 9.2.0 (`requirements.txt`), for the tests only.
- Claude Code CLI 2.1.316 (`claude -p`), for the Claude calls and as an MCP client and server. Calls go
  through my Claude subscription. No API key is stored anywhere.
- git 2.x. Windows 11 / Git Bash and PowerShell. On macOS/Linux use `.venv/bin/python`.

## Commands (from a fresh clone, in this folder)
```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest tests -v                 # 21 tests, offline, no Claude calls

# corpus (already committed; rebuild only if you have the JS2 run folder next to this one)
.venv\Scripts\python.exe build_corpus.py ..\js2-loop-tools-diff\jobs\runs\2026-11-10T213906-after-patch\raw

# reject audit
.venv\Scripts\python.exe audit.py sample                    # seed 7375 -> labels\audit_sheet.csv (blind) + reports\audit_key.json
.venv\Scripts\python.exe audit.py label                     # judge each posting by hand (r/n/u), resumable
.venv\Scripts\python.exe audit.py export                    # or: fill labels\audit_verdicts_edit.csv (r/n/u) ...
.venv\Scripts\python.exe audit.py import                    # ... and copy it into labels\audit_sheet.csv
.venv\Scripts\python.exe audit.py report                    # -> reports\AUDIT.md

# measure a proposed rule change before it goes into FILTER.md
.venv\Scripts\python.exe measure_rules.py "{\"require_role_word\": true}" P1-require-role-word

# source-grounded shortlist
.venv\Scripts\python.exe shortlist.py --claude              # 11 real claude -p calls; omit --claude to relabel saved responses

# the tool server
.venv\Scripts\python.exe mcp_client.py own-server-handwritten-client --calls mcp\calls-own.json -- .venv\Scripts\python.exe mcp_server.py
.venv\Scripts\python.exe mcp\claude-client.py               # Claude Code as the client (only my tool allowed)
.venv\Scripts\python.exe mcp_client.py other-claude-mcp-serve-calls --calls mcp\calls-other.json -- claude mcp serve

# what moves the score
.venv\Scripts\python.exe experiments.py claude              # 40 real claude -p calls (skips ones already saved)
.venv\Scripts\python.exe experiments.py report              # -> reports\SCORE-REPORT-data.md
```
To use the server from Claude Code interactively: `claude mcp add js3 -- python <abs path>\mcp_server.py`.

## What ran (all on 2026-11-23, ET; nothing below is simulated or seeded)

| When | Command | Result |
|---|---|---|
| ~13:20 | filter v1.0.0 on the corpus | 16 keep, 472 reject:location, 77 reject:seniority_title, 75 reject:score |
| ~13:30 | `audit.py sample` | 66-posting blind sheet: 30 random rejects, 10 non-location rejects, 23 close calls, 3 other keeps |
| ~13:30 | `measure_rules.py` P1–P5 | P1 added, P2–P4 rejected, P5 deferred (FILTER.md §7) |
| 13:44 | `shortlist.py --claude` | 11 kept postings (v1.1), 11 real Claude responses, 64 claims labeled (`evidence/01`) |
| ~13:50 | checker v1.2 + relabel | 0 filter decisions changed. Shortlist: 6 relevant, 5 "I cannot tell"; Claude claims 31 supported / 33 insufficient |
| 13:52 | handwritten client → my server | 7 calls, every error path answered as designed |
| 13:54 | Claude Code → my server | discovery probe, version downgrade, 2 tool calls (`transcripts/`) |
| ~13:55 | handwritten client → `claude mcp serve` | 32 tools, no annotations, `Read` outside the folder succeeded |
| 13:56–13:58 | `experiments.py claude` | 40 Claude calls; held-out results E0–E5 in SCORE-REPORT.md |
| ~14:00 | `pytest tests -v` | 21 passed (`evidence/03-pytest.txt`) |
| 11-25 | `audit.py export` → my verdicts in the CSV → `audit.py import` → `report` | 66/66 judged by hand (5 relevant, 53 not, 8 unsure). Random rejects 0/27 wrong (95% CI 0–12.8%); close calls 10/19 wrong. 4 verdicts revised after Claude flagged inconsistencies (FRICTIONAL 13) |
| 11-25 | `measure_rules.py` P1–P5 (`--base` v1.0.0) + P7, P8 on v1.2.0 | P1 confirmed, P2–P4 rejected, P5 not adopted; P7/P8 rejected as in-sample (FILTER.md §7) |

## Files

| Path | What |
|---|---|
| `FILTER.md` | the filter (machine-readable block + reasons), evidence rules, expected sources, wrong versions, change log. v1.0.0 committed before any code (85730d3) |
| `js3/filter.py`, `js3/evidence.py` | filter decision and claim labeling (both read FILTER.md) |
| `audit.py`, `labels/audit_sheet.csv`, `reports/audit_key.json`, `reports/AUDIT.md` | reject audit |
| `reports/FALSE-FRIENDS.md` | words that matched for the wrong reason |
| `measure_rules.py`, `reports/rule-changes/` | the measurement behind every add / cut / reject |
| `shortlist.py`, `prompts/justify.txt`, `reports/SHORTLIST.md`, `reports/shortlist.json`, `reports/claude/shortlist/` | the source-grounded shortlist |
| `reports/SHORTLIST-NOTES.md` | relevance vs. entailment, the abstention rule, counterexamples |
| `mcp_server.py`, `mcp_client.py`, `mcp/`, `transcripts/`, `TOOL-EVALUATION.md` | tool server, client, transcripts, both evaluations |
| `experiments.py`, `prompts/relevance_*.txt`, `reports/claude/experiments/`, `SCORE-REPORT.md` | what moves the score |
| `SIGNOFF.md` | sign-off and driver's seat |
| `SOURCES.md`, `FRICTIONAL.md` | who did what, and the honest log |
| `data/corpus.jsonl`, `persona/`, `labels/js1_hand_labels.csv` | inputs (public postings, fictional persona, my JS1 labels) |

## Boundaries
Read-only, local. Nothing in this folder fetches from the web: the corpus came from JS2's allow-listed,
public endpoints (Greenhouse and Lever job-board APIs). The agent never applies, emails, messages, or
logs in. The tool server exposes one scoring tool and writes only its own transcripts. No real
résumé, contacts, or tracker is in this folder.
