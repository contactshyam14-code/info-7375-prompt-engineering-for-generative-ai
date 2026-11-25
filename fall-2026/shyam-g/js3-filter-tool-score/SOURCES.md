# SOURCES

## Started from
- My Job-Search Agent 2 (`js2-loop-tools-diff/`): the raw responses of the real run
  `2026-11-10T213906-after-patch`, and its Greenhouse/Lever parsing (re-implemented in `build_corpus.py`).
- My Job-Search Agent 1 (`js1-contract-and-watch/`): the fictional persona, the relevance prompt
  (`prompts/relevance_A.txt` is JS1 `prompts/revision.txt` unchanged), the `claude -p` calling pattern,
  and my 20 hand labels (`labels/js1_hand_labels.csv`).
- Lectern (instructor's repo), the idea only: the filter is a document whose every added, cut, and
  rejected word is recorded and measured. No Lectern code was used.

## Public endpoints behind the corpus (fetched in JS2, read-only, no login)
- Greenhouse Job Board API `boards-api.greenhouse.io/v1/boards/formlabs/jobs?content=true`
- Lever Postings API `api.lever.co/v0/postings/{spotify,palantir}?mode=json`

## Protocol reference
- Model Context Protocol (JSON-RPC 2.0 over stdio): initialize / notifications/initialized /
  tools/list / tools/call, protocol version string 2025-06-18. Written from my knowledge of the spec,
  without an SDK. The other server evaluated is `claude mcp serve` from Claude Code 2.1.316 (Anthropic).

## What Claude contributed
**Claude Code (model Claude Opus 5.5), one session on 2026-11-23, at my request**, given the assignment
text and pointed at my JS1/JS2 folders:
- All code: `build_corpus.py`, `js3/filter.py`, `js3/evidence.py`, `js3/claude_cli.py`, `audit.py`,
  `measure_rules.py`, `shortlist.py`, `mcp_server.py`, `mcp_client.py`, `mcp/claude-client.py`, `experiments.py`.
- All tests in `tests/`. They assert rules written in FILTER.md, and FILTER.md v1.0.0 was committed
  before any code. But Claude wrote both the tests and the code, so they aren't independent.
- **FILTER.md v1.0.0 was drafted by Claude Code**, from the persona and my JS1/JS2 rules, and committed
  before the code. The v1.1.0/v1.2.0 changes (role-word rule, years extractor, evidence rules) were
  proposed and measured by Claude Code. I read them and made no edits of my own.
- `prompts/justify.txt` (justification prompt) and `prompts/relevance_B.txt` (one sentence changed from
  JS1's prompt, taken from FILTER.md's persona line).
- First drafts of README.md, TOOL-EVALUATION.md, SCORE-REPORT.md, SIGNOFF.md, FRICTIONAL.md,
  reports/FALSE-FRIENDS.md, reports/SHORTLIST-NOTES.md.

**Claude (via `claude -p`, Claude Code CLI 2.1.316, default model), real responses with timestamps:**
- 11 shortlist justifications, 2026-11-23 13:44 ET (`reports/claude/shortlist/`).
- 40 relevance verdicts for experiments E3–E5, 2026-11-23 13:56–13:58 ET (`reports/claude/experiments/`).
- 1 Claude Code session as an MCP client of my server, 2026-11-23 13:54 ET (`transcripts/claude-client-answer.json`).

**Mine:**
- The JS1 hand labels (October) and the persona.
- The 66 audit verdicts in `labels/audit_sheet.csv` (2026-11-25). Four (A026, A031, A052, A058) were
  changed after Claude Code flagged them as inconsistent with my checklist; Claude did not choose the new values.
- The claim spot-check labels in `reports/SHORTLIST-NOTES.md` §4 / `labels/spotcheck_edit.csv` (2026-11-25).
  Claude Code drew the 10 claims at random and wrote the summary of my disagreements; the labels are mine.
- The final sign-off decision, and the reasons in FRICTIONAL rows 1, 13 and 15 (my answers, worded by Claude Code).

## Accepted, modified, rejected
- Rejected (measured): P2 cut "staff", P3 cut "excel", P4 cut "intern" (FILTER.md §7).
- Not adopted: threshold 3 (E2), despite 10/10 on held-out, because those labels are contaminated and n = 10.
- Changed after Claude flagged them: 4 audit verdicts (my decision, my new values). I made no edits to Claude's code or drafts.
