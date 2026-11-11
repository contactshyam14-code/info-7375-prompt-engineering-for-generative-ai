"""The bounded agent loop (Chapter 4).

One pass over the configured boards. Every step is recorded as an observation.
The loop ends in exactly one of four exits:

  finished          every board was observed successfully
  incomplete        the loop reached the end, but at least one board failed (no value invented)
  budget_exhausted  a board, request or time budget stopped the loop early
  error             the loop could not continue as designed (policy denial, unexpected exception)

"Finished" means the loop ran to the end without failures. It does NOT mean the answer is
right: an empty-but-valid response still finishes. check.py is the independent check.
"""
from __future__ import annotations

import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Callable

from .policy import Policy
from .providers import PROVIDERS, Permanent, Transient

EXITS = ("finished", "incomplete", "budget_exhausted", "error")


@dataclass(frozen=True)
class Budget:
    max_boards: int
    max_requests: int
    max_seconds: float
    max_retries_per_board: int
    retry_backoff_seconds: float
    request_timeout_seconds: float

    @classmethod
    def from_dict(cls, d: dict) -> "Budget":
        return cls(**{k: d[k] for k in cls.__dataclass_fields__})


@dataclass
class BoardResult:
    board: str
    ats: str
    url: str
    status: str = "pending"      # ok | error | denied | repeat-skipped | not-attempted
    count: int | None = None     # None means "unknown"; never 0 for a failure
    attempts: int = 0
    error: str | None = None
    postings: list = field(default_factory=list)
    body: bytes | None = None


def normalize_action(method: str, url: str) -> tuple[str, str]:
    """Repeat rule: two actions are "the same" if method and normalized URL match."""
    p = urllib.parse.urlsplit(url)
    query = urllib.parse.urlencode(sorted(urllib.parse.parse_qsl(p.query, keep_blank_values=True)))
    path = p.path.rstrip("/") or "/"
    return method.upper(), urllib.parse.urlunsplit(
        (p.scheme.lower(), (p.hostname or "").lower(), path, query, ""))


def run_loop(boards: list[dict], budget: Budget, policy: Policy,
             http_get: Callable[[str, float], bytes],
             clock: Callable[[], float] = time.monotonic,
             sleep: Callable[[float], None] = time.sleep) -> dict:
    start = clock()
    obs: list[dict] = []
    results: list[BoardResult] = []
    requests = 0
    seen_actions: set[tuple[str, str]] = set()
    exit_status: str | None = None
    exit_reason = ""

    def note(event: str, board: str | None = None, **detail):
        obs.append({"t": round(clock() - start, 3), "event": event, "board": board, **detail})

    note("loop-start", budget=budget.__dict__, boards=[b["board"] for b in boards])

    for i, b in enumerate(boards):
        name, ats = b["board"], b["ats"]
        if ats not in PROVIDERS:
            note("config-error", name, detail=f"unknown ATS {ats!r}")
            exit_status, exit_reason = "error", f"unknown ATS {ats!r} for board {name}"
            break
        url_fn, parse_fn = PROVIDERS[ats]
        r = BoardResult(board=name, ats=ats, url=url_fn(name))

        if i >= budget.max_boards:
            exit_status, exit_reason = "budget_exhausted", f"max_boards={budget.max_boards} reached"
            note("budget-exhausted", name, budget="max_boards")
            break

        action = normalize_action("GET", r.url)
        if action in seen_actions:
            r.status = "repeat-skipped"
            note("repeat-skipped", name, url=r.url, detail="same (method, normalized URL) already done")
            results.append(r)
            continue
        seen_actions.add(action)

        d = policy.check_request(r.url, "GET")
        note("policy", name, url=r.url, verdict=d.verdict, reason=d.reason)
        if not d.allowed:
            r.status, r.error = "denied", d.reason
            results.append(r)
            exit_status, exit_reason = "error", f"policy denied a configured board ({name}); escalate to owner"
            break

        while True:
            if requests >= budget.max_requests:
                exit_status, exit_reason = "budget_exhausted", f"max_requests={budget.max_requests} reached"
                note("budget-exhausted", name, budget="max_requests")
                break
            remaining = budget.max_seconds - (clock() - start)
            if remaining <= 0:
                exit_status, exit_reason = "budget_exhausted", f"max_seconds={budget.max_seconds} reached"
                note("budget-exhausted", name, budget="max_seconds")
                break
            requests += 1
            r.attempts += 1
            timeout = min(budget.request_timeout_seconds, remaining)
            note("request", name, url=r.url, attempt=r.attempts, request_no=requests,
                 timeout=round(timeout, 1))
            try:
                r.body = http_get(r.url, timeout)
                r.postings = parse_fn(r.body)
                r.count, r.status = len(r.postings), "ok"
                note("observed", name, count=r.count, bytes=len(r.body))
                if r.count == 0:
                    note("warning", name, detail="valid but EMPTY response; 0 is not verified")
                break
            except Transient as e:
                note("transient-error", name, attempt=r.attempts, error=str(e))
                if r.attempts <= budget.max_retries_per_board:
                    note("retry", name, after_seconds=budget.retry_backoff_seconds)
                    sleep(budget.retry_backoff_seconds)
                    continue
                r.status, r.error = "error", f"gave up after {r.attempts} attempts: {e}"
                note("board-failed", name, error=r.error)
                break
            except Permanent as e:
                r.status, r.error = "error", str(e)
                note("board-failed", name, error=r.error, detail="permanent: no retry")
                break
            except Exception as e:  # unexpected: stop and escalate, do not guess
                r.status, r.error = "error", f"unexpected {type(e).__name__}: {e}"
                note("unexpected-exception", name, error=r.error)
                exit_status, exit_reason = "error", r.error
                break

        results.append(r)
        if exit_status:
            break

    # boards the loop never reached are reported, not dropped
    done = {r.board for r in results}
    for b in boards:
        if b["board"] not in done:
            url_fn = PROVIDERS.get(b["ats"], (lambda t: "", None))[0]
            results.append(BoardResult(board=b["board"], ats=b["ats"], url=url_fn(b["board"]),
                                       status="not-attempted"))

    if exit_status is None:
        failed = [r.board for r in results if r.status not in ("ok", "repeat-skipped")]
        if failed:
            exit_status, exit_reason = "incomplete", f"failed boards: {failed}"
        else:
            exit_status, exit_reason = "finished", "all boards observed"
    note("loop-exit", exit_status=exit_status, reason=exit_reason, requests=requests)
    return {"exit_status": exit_status, "exit_reason": exit_reason, "requests": requests,
            "elapsed_seconds": round(clock() - start, 3), "results": results, "observations": obs}
