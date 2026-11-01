# SOURCES

## Used
- Greenhouse Job Board API, public, no authentication:
  `https://boards-api.greenhouse.io/v1/boards/formlabs/jobs?content=true`. The postings belong to
  Formlabs; they are saved here only as evidence for the runs.
- Course kit (`kit-original/`): fixtures, `test_contract.py`, the replacement text for CONTRACT section 4,
  and the persona `jordan_rivera.json` (fictional).
- Python 3.12 standard library; pytest 9.2.0; Claude Code CLI (`claude -p`).

## What I wrote
- `CONTRACT.md`: Claude wrote the first draft; I rewrote it on 2026-10-30, before any code existed.
- On 2026-10-31, after the code existed, I decided on the amendments in CONTRACT section 8: keep
  Formlabs, strip HTML, and use the CLI instead of an API key.
- Hand labels and the labeling rule: **not completed** by the deadline. Claude did not fill them in.
- The choice of the one prompt revision: **not made** (it depends on the labels).
- The decision to sign the sign-off (2026-10-31, 23:28). The signature line itself was typed by Claude at my instruction.

## What Claude (Claude Code, Opus 5.5) contributed
- `agent.py`, `study.py`, `allowlist.txt`, `prompts/baseline.txt`, `tests/test_extra.py`, `tests/test_resume.py`, `build_submission.py`, written
  2026-10-31 against the pre-written tests.
- Probing candidate Greenhouse boards; Claude proposed Formlabs.
- The seeded "earlier" response (`seeded/formlabs-earlier-SEEDED.json`) and the two-run demo.
- Running Ways 1 and 2 of the action-surface comparison, and the first drafts of `ACTION-SURFACE.md`,
  `SAMPLING.md`, `EXPERIMENT.md`, `FRICTIONAL.md` and the README.
- The fill-ins in CONTRACT.md (token, HTML wording, CLI wording) and section 8, written at my direction.
- Claude's verdicts in `output/` and `results/` are model judgments, labeled as such.
