# Review packet (Chapter 6): refuse HTTP redirects

> Sections 1–5 were filled in by Claude Code from the commits and real outputs listed.
> Sections 6–8 are mine.

## 1. The defect
`js2/providers.py` fetched with `urllib.request.urlopen`, which follows redirects automatically.
The policy (`check_request`) checks only the first URL. A 301/302 from an allowed host would
make the agent fetch a URL on a host the policy never checked. GATE.md section 6, wrong version 6,
had already named this case ("redirect to an unlisted host").

Reproduced by `tests/test_loop.py::test_6_6c_redirect_to_unlisted_host_not_followed`. That test
starts two local servers: A answers 302 → B, and B counts hits. Before the patch, B got 1 hit.

## 2. The test, written before the patch
- Test: `tests/test_loop.py::test_6_6c_redirect_to_unlisted_host_not_followed` (asserts B gets 0 hits)
- Committed red, before any patch: `c64bf5c`
- Red run, 2026-11-10 (`evidence/04-pytest-first-run.txt`):
```
FAILED tests/test_loop.py::test_6_6c_redirect_to_unlisted_host_not_followed
E           AssertionError: redirect was followed to a host the policy never checked
E           assert 1 == 0
```

## 3. What I asked Claude Code (2026-11-10)
Claude Code asked: "Should I patch the redirect hole as your review-packet change?" My reply, word
for word: "Lets continue". The scope Claude stated, which I accepted: only the redirect, in one file.

## 4. The diff, read as a change in behavior (commit `23888ac`)
```diff
+class _RefuseRedirects(urllib.request.HTTPRedirectHandler):
+    def redirect_request(self, req, fp, code, msg, headers, newurl):
+        raise Permanent(f"HTTP {code} redirect to {newurl} refused: policy checked only {req.full_url}")
+
+_OPENER = urllib.request.build_opener(_RefuseRedirects)
 ...
-        with urllib.request.urlopen(req, timeout=timeout) as r:
+        with _OPENER.open(req, timeout=timeout) as r:
```
**Before:** any 3xx was followed silently, and the board was reported `ok` with whatever the
second host returned.
**After:** any 3xx raises `Permanent`. The loop records the board as a failure with the redirect
target in the error text, and it does not retry (per the GATE error policy, a permanent failure
isn't retried). No count is invented.

## 5. Did it stay in scope?
One code file, `js2/providers.py`: 12 lines added, 1 changed. (Commit 23888ac also added the
after-patch evidence files, `evidence/05` and one run folder. Those are output, not code.) The loop, the policy, the tests and the
config are untouched. After the patch (`evidence/05-pytest-after-redirect-patch.txt`): 21 passed,
4 failed. The 4 still failing are the same GATE naming differences as before (6.1, 6.2, 6.3, row
14). The patch didn't touch them. Live run after the patch, 2026-11-10 21:39 ET
(`jobs/runs/2026-11-10T213906-after-patch/`): formlabs 250, spotify 86, palantir 304, the 404
board still `count=None`.

## 6. Commands I ran myself
Run by me on 2026-11-10 in the evening, after the patch (23888ac), in js2-loop-tools-diff:
```
> .\.venv\Scripts\python.exe -m pytest tests -q
FAILED tests/test_boundary.py::test_14_state_ambiguity - AssertionError: assert 'deny' == 'allow'
FAILED tests/test_loop.py::test_6_1_404_is_bad_name_not_zero - AssertionError: assert 'error' == 'bad_name'
FAILED tests/test_loop.py::test_6_2_empty_list_is_ok_empty_one_request - AssertionError: assert 'ok' == 'ok_empty'
FAILED tests/test_loop.py::test_6_3_503_retried_once_then_failed - AssertionError: assert 'error' == 'failed'
4 failed, 21 passed in 1.45s

> git show 23888ac --stat
commit 23888acd606269410f9cdb51d0c19300024b0c08
Date:   Tue Nov 10 21:39:27 2026 -0500

    Review patch: refuse HTTP redirects so no unchecked URL is fetched (test_6_6c red -> green)

 evidence/05-pytest-after-redirect-patch.txt        | 106 +++++++++++++++++++++
 .../raw/greenhouse-formlabs.json                   |   1 +
 .../2026-11-10T213906-after-patch/raw/index.json   |  31 ++++++
 .../raw/lever-palantir.json                        |   1 +
 .../raw/lever-spotify.json                         |   1 +
 .../runs/2026-11-10T213906-after-patch/report.json | 100 +++++++++++++++++++
 .../runs/2026-11-10T213906-after-patch/trace.jsonl |  15 +++
 js2/providers.py                                   |  13 ++-
 8 files changed, 267 insertions(+), 1 deletion(-)
(output of this command pasted by Claude Code; same command, same commit)
```
test_6_6c is not in the failure list, so it passed. The 4 failures are the GATE naming
differences that existed before the patch.

## 7. Decision: accept / revise / reject
Decision: Accept.

Evidence:
- Before the patch, test_6_6c failed: the second server got 1 hit (commit c64bf5c, evidence/04).
- After the patch, test_6_6c passed (commit 23888ac, evidence/05, and my own run in section 6).
- Scope: only js2/providers.py changed (12 lines added, 1 changed). The loop, policy, tests and config were not touched.
- No new failures: the same 4 tests failed before and after, for the GATE naming reasons.
- The live run after the patch still fetched all 3 real boards and reported the 404 board with count=None.
- I accept this because without the patch a board that redirects to another site would be counted as a hit on a second server, and the patch fixes that (test_6_6c now passes) with a small change confined to providers.py and no new failures.

## 8. One case my test would still miss
A redirect between two pages on the same allowed host (for example, Greenhouse moving a board
to a new path) is now refused too, and the board is marked failed. My test only checks a
redirect to a different host, so it doesn't tell me whether refusing same-host redirects is
too strict.