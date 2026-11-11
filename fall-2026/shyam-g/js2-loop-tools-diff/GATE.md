# GATE — Job-Search Agent 2

Written by: Shyam Sundar Jayaraman Gopalakrishnan  Date: 11/10/2026

## 1. Exits
| Exit | When | What it reports |
|---|---|---|
| finished | Every board in the list got a final status (ok, ok_empty, bad_name, or failed) | Per-board status and job counts, plus totals |
| incomplete | Run stopped early for a non-budget reason (repeat rule, policy denial), so some boards were never tried | Boards done, boards not attempted, and the reason it stopped |
| budget_exhausted | Any budget in section 2 ran out | Which budget tripped, boards done vs. not attempted |
| error | Unexpected failure the policy doesn't cover (crash, unreadable config) | The error text and no job counts, because partial counts would mislead |

Why "finished" ≠ "succeeded": finished only means the loop reached the end of the list. Every board can 404 or time out and the run still finishes. The report must show per-board status and never a single "success" flag.

## 2. Budgets
| Budget | Value | Why this value |
|---|---|---|
| max boards per run | 5 | My watchlist size; raise it only when the list grows |
| max requests per run | 10 | 5 boards × (1 try + 1 retry), the worst case with no hidden extra calls |
| max seconds per run | 60 | A normal run takes a few seconds, so this is a stall guard |
| retries per board | 1 | One retry covers a blip; a second just delays a real failure |
| retry backoff | 2 s | Gives a flaky host a moment without slowing the run much |
| request timeout | 15 s | Four timeouts in a row hit the 60 s cap, so a dead network stops the run quickly |

Who may change them: only me, through a dated entry in section 7, with the config edit in the same commit.

## 3. Repeat rule
What counts as "the same" action: same method + same host + same board within one run.

What the loop does about a repeat: skip it and log "duplicate skipped". A retry after a failure is not a repeat, because the retry budget counts it. If the loop proposes duplicates 3 times, exit incomplete.

## 4. Error policy
| Failure | Stop / retry / escalate | Why |
|---|---|---|
| bad board name (404) | No retry. Mark bad_name, go to the next board | The name won't become valid in 2 seconds |
| empty response body | Retry once, then mark failed | A 200 with no body is likely a glitch, and a GET is safe to repeat. It is never counted as 0 jobs |
| valid but empty list | No retry. Mark ok_empty, report 0 jobs | This is a real answer: the board has no openings |
| timeout / 5xx | Retry once after 2 s, then mark failed | Transient, and a read-only GET is safe to repeat |
| policy denial | No retry. Exit incomplete and log it | Retrying a denial is trying to get around the rule |

What the loop never does on failure: report 0 jobs for a failed board, skip a board silently, or retry anything that isn't a GET.

## 5. Permission policy
- Hosts the agent may call: boards-api.greenhouse.io and api.lever.co only
- Methods: GET only
- Folders it may read: the project root (the config can't narrow this; see FRICTIONAL)
- Folders it may write: jobs/ only
- Writes that need my approval: overwriting any existing file, except state/*.json, which is the agent's own bookkeeping
- Never (no code path may exist): apply, email, message, login, submit_form, post

## 6. Wrong versions my tests must catch
1. Reports 0 jobs on a 404 → mock a 404; assert status bad_name, not a zero count.
2. Treats an empty list as an error and retries → mock `{"jobs": []}`; assert exactly 1 request and ok_empty.
3. Retries the wrong number of times → mock a permanent 503; assert exactly 2 requests, then failed.
4. Ignores the board budget → give 8 boards; assert it stops at 5 with budget_exhausted and lists the 3 untried.
5. Says "finished" when a budget tripped → trip max_seconds with a slow mock; assert exit is budget_exhausted.
6. Allows a POST, an unlisted host, or a redirect to an unlisted host → attempt each; assert a policy denial and no network call.
7. Drops a failed board from the report → fail one board of three; assert all three appear with statuses.

## 7. Amendments (dated)
- 11/10/2026: initial values for all budgets and policies.