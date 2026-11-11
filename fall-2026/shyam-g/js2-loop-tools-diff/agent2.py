"""Job-Search Agent 2: watch several boards in one bounded loop, under a permission policy.

  python agent2.py run                                   # live run over config/boards.json
  python agent2.py run --label live
  python agent2.py run --inject-empty formlabs --label SEEDED-empty    # finished-wrong-answer demo
  python agent2.py run --simulate-timeout spotify --label SIMULATED-timeout
  python agent2.py run --replay jobs/runs/<dir> --label replay          # offline, from saved raw
  python check.py jobs/runs/<dir>                        # the independent check

Every network call, read and write goes through js2.policy.Policy. Outputs go to jobs/ only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
import time

from js2.loop import Budget, run_loop
from js2.policy import Policy, PolicyViolation
from js2.providers import Permanent, Transient, http_get
from js2 import rule

ROOT = pathlib.Path(__file__).parent.resolve()
CONFIG = ROOT / "config"


def load_json(policy: Policy, rel: str):
    return json.loads(policy.read_bytes(rel))


# ---------- fetchers (each is labeled in the trace) ----------

def make_fetcher(args, policy: Policy, trace_notes: list):
    if args.replay:
        replay_dir = pathlib.Path(args.replay)
        index = json.loads(policy.read_bytes(replay_dir / "raw" / "index.json"))

        def fetch(url, timeout):
            meta = index.get(url)
            if meta is None:
                raise Permanent(f"REPLAY: no saved response for {url}")
            if meta.get("error_kind") == "transient":
                raise Transient(f"REPLAY of saved error: {meta['error']}")
            if meta.get("error_kind") == "permanent":
                raise Permanent(f"REPLAY of saved error: {meta['error']}")
            return policy.read_bytes(replay_dir / "raw" / meta["file"])
        trace_notes.append(f"REPLAY from {replay_dir.as_posix()}: no network calls")
    else:
        fetch = http_get

    def wrapped(url, timeout):
        for name in args.simulate_timeout or []:
            if f"/{name}/" in url or f"/{name}?" in url:
                raise Transient(f"SIMULATED timeout for {name} (--simulate-timeout)")
        body = fetch(url, timeout)
        for name in args.inject_empty or []:
            if f"/{name}/" in url or f"/{name}?" in url:
                trace_notes.append(f"SEEDED: real response for {name} replaced with an empty list")
                return b'{"jobs": []}' if "greenhouse" in url else b"[]"
        return body
    return wrapped


# ---------- run ----------

def approver_from(args):
    def approve(decision):
        if args.approve_overwrites:
            print(f"APPROVED by --approve-overwrites: {decision.reason}")
            return True
        print(f"NOT APPROVED (pass --approve-overwrites to allow): {decision.reason}")
        return False
    return approve


def run(args) -> int:
    policy = Policy.from_file(CONFIG / "policy.json", ROOT)
    for a in ("fetch_board", "read_file", "write_output"):
        d = policy.check_action(a)
        if not d.allowed:
            raise PolicyViolation(d.reason)
    budget = Budget.from_dict(load_json(policy, "config/budgets.json"))
    boards = load_json(policy, args.boards)["boards"]
    resume = rule.validate_resume(load_json(policy, "persona/jordan_rivera.json"))

    run_at = dt.datetime.now().astimezone()
    stamp = run_at.strftime("%Y-%m-%dT%H%M%S")
    run_dir = f"jobs/runs/{stamp}-{args.label}"
    notes: list[str] = []
    out = run_loop(boards, budget, policy, make_fetcher(args, policy, notes))
    approve = approver_from(args)

    # raw responses, saved before anything is interpreted
    index = {}
    for r in out["results"]:
        meta = {"board": r.board, "ats": r.ats, "status": r.status, "attempts": r.attempts}
        if r.body is not None:
            meta["file"] = f"{r.ats}-{r.board}.json"
            policy.write_bytes(f"{run_dir}/raw/{meta['file']}", r.body, approve)
        if r.error:
            meta["error"] = r.error
            meta["error_kind"] = "transient" if ("timeout" in r.error or "attempts" in r.error) else "permanent"
        index[r.url] = meta
    policy.write_text(f"{run_dir}/raw/index.json", json.dumps(index, indent=2), approve)

    # new postings per board (state updated only for boards observed ok)
    boards_report = []
    for r in out["results"]:
        entry = {"board": r.board, "ats": r.ats, "url": r.url, "status": r.status,
                 "count": r.count, "attempts": r.attempts, "error": r.error}
        if r.status == "ok":
            state_rel = f"jobs/state/seen-{r.ats}-{r.board}.json"
            seen = None
            if (ROOT / state_rel).exists():
                seen = set(json.loads(policy.read_bytes(state_rel))["seen_ids"])
            ids = [p["id"] for p in r.postings]
            new = [] if seen is None else [p for p in r.postings if p["id"] not in seen]
            entry["baseline"] = seen is None
            entry["new"] = [{"id": p["id"], "title": p["title"], "location": p["location"]["name"],
                             "url": p["absolute_url"], "rule_verdict": rule.judge_rule(resume, p),
                             "rule_label": "record (JS1 CONTRACT section 4)"} for p in new]
            entry["relevant_now"] = sum(rule.judge_rule(resume, p) == "relevant" for p in r.postings)
            if not args.no_state:
                policy.write_text(state_rel, json.dumps(
                    {"board": r.board, "ats": r.ats, "updated": run_at.isoformat(timespec="seconds"),
                     "seen_ids": sorted((seen or set()) | set(ids))}, indent=2), approve)
        boards_report.append(entry)

    report = {"run_at": run_at.isoformat(timespec="seconds"), "label": args.label,
              "labels_in_this_run": notes or ["live"], "exit_status": out["exit_status"],
              "exit_reason": out["exit_reason"], "requests": out["requests"],
              "elapsed_seconds": out["elapsed_seconds"], "budget": budget.__dict__,
              "boards": boards_report}
    policy.write_text(f"{run_dir}/report.json", json.dumps(report, indent=2), approve)
    policy.write_text(f"{run_dir}/trace.jsonl",
                      "".join(json.dumps(o) + "\n" for o in
                              [{"event": "run-labels", "labels": notes or ["live"]}] + out["observations"]),
                      approve)

    print(f"{report['run_at']}  label={args.label}  exit={out['exit_status']}  ({out['exit_reason']})")
    for n in notes:
        print(f"  ** {n}")
    for e in boards_report:
        extra = ""
        if e["status"] == "ok":
            extra = (" baseline (no earlier state)" if e["baseline"] else f" new={len(e['new'])}")
            extra += f" relevant_now={e['relevant_now']}"
        print(f"  {e['ats']:<10} {e['board']:<22} {e['status']:<15} count={e['count']}"
              f" attempts={e['attempts']}{extra}{'  error: ' + e['error'] if e['error'] else ''}")
    print(f"  requests={out['requests']}  elapsed={out['elapsed_seconds']}s  saved: {run_dir}/")
    print(f"  independent check:  python check.py {run_dir}")
    return {"finished": 0, "incomplete": 2, "budget_exhausted": 3, "error": 4}[out["exit_status"]]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--label", default="live")
    r.add_argument("--boards", default="config/boards.json")
    r.add_argument("--replay", help="run offline against a saved run folder")
    r.add_argument("--inject-empty", action="append", metavar="BOARD",
                   help="SEEDED: replace this board's real response with an empty list")
    r.add_argument("--simulate-timeout", action="append", metavar="BOARD",
                   help="SIMULATED: make every request to this board time out")
    r.add_argument("--no-state", action="store_true", help="do not update jobs/state (for demos)")
    r.add_argument("--approve-overwrites", action="store_true",
                   help="owner approval for overwriting existing files that the policy marks 'ask'")
    a = ap.parse_args(argv)
    try:
        return run(a)
    except PolicyViolation as e:
        print(f"POLICY VIOLATION, run stopped: {e}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    sys.exit(main())
