# Permission policy: boundary-test table

> **Fill in "Predicted" and commit BEFORE you run the tests.** Then write the tests in
> `tests/test_boundary.py` yourself and fill in "Actual" from the pytest output.
> If Actual ≠ Predicted, don't edit the prediction. Explain it in "Notes".

Required by the assignment: ≥10 cases, including an off-list host, `..`, the prefix trick
(`jobs-evil` beside `jobs`), a symlink, read vs. write, and a write that needs approval.

Policy under test: `js2/policy.py`, configured by `config/policy.json`.
Verdicts: `allow`, `deny`, `ask` (needs owner approval).

| # | Category | Input | Predicted | Test name | Actual | Notes |
|---|---|---|---|---|---|---|
| 1 | host on allow-list | GET `https://boards-api.greenhouse.io/v1/boards/acme/jobs` | allow | `test_01_allowed_host` | PASSED (matches) | |
| 2 | host off allow-list | GET `https://example.com/jobs` | deny | `test_02_off_list_host` | PASSED (matches) | |
| 3 | lookalike host | GET `https://boards-api.greenhouse.io.evil.com/x` | deny | `test_03_lookalike_host` | PASSED (matches) | |
| 4 | non-GET method | POST `https://api.lever.co/v0/postings/acme` | deny | `test_04_post_denied` | PASSED (matches) | |
| 5 | `..` escape | write `jobs/../config/policy.json` | deny | `test_05_dotdot_escape` | PASSED (matches) | |
| 6 | prefix trick `jobs-evil` | write `jobs-evil/out.json` (sibling of `jobs/`) | deny | `test_06_prefix_trick_jobs_evil` | PASSED (matches) | |
| 7 | symlink escape | write `jobs/link.json`, a symlink to a file outside the project | deny | `test_07_symlink_escape` | PASSED (matches) | |
| 8 | read inside project | read `config/budgets.json` | allow | `test_08_read_inside_project` | PASSED (matches) | |
| 9 | read outside project | read `/etc/hosts` | deny | `test_09_read_outside_project` | PASSED (matches) | |
| 10 | same path: read vs write | read `config/budgets.json`, then write `config/budgets.json` | allow, then deny | `test_10_same_path_read_then_write` | PASSED (matches) | |
| 11 | overwrite needing approval (not approved) | overwrite existing `jobs/report.json`, approved=False | ask | `test_11_overwrite_not_approved` | PASSED (matches) | |
| 12 | overwrite needing approval (approved) | overwrite existing `jobs/report.json`, approved=True | allow | `test_12_overwrite_approved` | PASSED (matches) | |
| 13 | forbidden action (apply / email / login) | action `email` (repeat for `apply` and `login`) | deny | `test_13_forbidden_actions[email/apply/login]` | PASSED (matches) | |
| 14 | `state/` ambiguity | overwrite existing `state/seen.json`, then write `state/seen.txt` | allow, then ask | `test_14_state_ambiguity` | **FAILED**: `state/seen.json` → deny (not allow) | My prediction was wrong: `state/` in my input is at the project root, not `jobs/state/`, so it is outside the write folder and denied. The `state/*.json` exception only applies inside `jobs/`. I kept my prediction unchanged. |

Predictions committed at: commit `92c6a6d`, time 14:50 ET, 2026-11-10

Tests written by Claude Code at my request after that commit (see SOURCES.md); each asserts my prediction as written.

Test run:
```
python -m pytest tests -q
```
First run 2026-11-10: **20 passed, 5 failed**. Full output: `evidence/04-pytest-first-run.txt`.
Boundary failure: row 14. Loop failures (GATE section 6): 6.1 status `error` not `bad_name`; 6.2 `ok` not `ok_empty`;
6.3 `error` not `failed` (request count of 2 was correct); 6.6c the redirect WAS followed to an unchecked host.
