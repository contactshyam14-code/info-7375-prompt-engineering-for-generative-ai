"""Independent check of one run. Deliberately does NOT import js2: it shares no code with the agent.

  python check.py jobs/runs/<run-dir>

For every board it compares three numbers that come from three different places:
  agent  : the count the agent reported (report.json)
  raw    : a recount from the saved raw response, using this file's own parsing
  hand   : the count a human wrote in labels/hand_labels.csv BEFORE the run

and it checks that the exit status is consistent with the board statuses.
Exit code 0 only if every board is checked and nothing is flagged. UNCHECKED is not a pass.
"""
import csv
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent
LABELS = ROOT / "labels" / "hand_labels.csv"


def recount(ats: str, path: pathlib.Path):
    data = json.loads(path.read_bytes())
    if ats == "greenhouse":
        return len(data["jobs"])
    if ats == "lever":
        return len(data)
    raise ValueError(f"check.py does not know ATS {ats!r}")


def load_labels():
    if not LABELS.exists():
        sys.exit(f"refused: {LABELS} does not exist; label the boards by hand first")
    rows = [r for r in csv.DictReader(LABELS.open(encoding="utf-8")) if (r.get("board") or "").strip()]
    if not rows:
        sys.exit(f"refused: {LABELS} has no rows; label the boards by hand before checking")
    return {(r["ats"].strip(), r["board"].strip()): r for r in rows}


def main(run_dir: str) -> int:
    run = pathlib.Path(run_dir)
    report = json.loads((run / "report.json").read_text(encoding="utf-8"))
    index = json.loads((run / "raw" / "index.json").read_text(encoding="utf-8"))
    labels = load_labels()
    flags, unchecked = [], []

    print(f"run: {run.as_posix()}  label={report['label']}  agent exit={report['exit_status']}")
    print(f"run labels: {report['labels_in_this_run']}")
    print(f"{'board':<22} {'status':<15} {'agent':>6} {'raw':>6} {'hand':>6}  verdict")
    for b in report["boards"]:
        key = (b["ats"], b["board"])
        meta = index.get(b["url"], {})
        raw = recount(b["ats"], run / "raw" / meta["file"]) if meta.get("file") else None
        lab = labels.get(key)
        hand_txt = (lab or {}).get("hand_count", "").strip()
        tol = int((lab or {}).get("tolerance") or 0)
        verdicts = []

        if lab is None or not hand_txt:
            verdicts.append("UNCHECKED: no hand label" if lab is None else "UNCHECKED: hand_count is blank")
            unchecked.append(b["board"])
        elif hand_txt.upper() in ("N/A", "ERROR", "404"):
            if b["status"] == "ok":
                verdicts.append("FLAG: hand label says this board should fail, agent says ok")
            elif b["count"] is not None:
                verdicts.append("FLAG: failed board reported a count (invented value)")
            else:
                verdicts.append("ok: failure reported as failure, no count invented")
        else:
            hand = int(hand_txt)
            if b["status"] != "ok":
                verdicts.append(f"note: board failed ({b['error']}); hand count {hand} not observed")
            else:
                if raw is not None and b["count"] != raw:
                    verdicts.append(f"FLAG: agent count {b['count']} != raw recount {raw}")
                if abs(b["count"] - hand) > tol:
                    kind = ("FINISHED-WRONG: empty response reported as 0 jobs"
                            if b["count"] == 0 and hand > 0 else "FLAG: differs from hand label")
                    verdicts.append(f"{kind} (agent {b['count']}, hand {hand}, tolerance {tol})")
                if not verdicts:
                    verdicts.append("ok")
        flags += [f"{b['board']}: {v}" for v in verdicts if v.startswith(("FLAG", "FINISHED-WRONG"))]
        print(f"{b['board']:<22} {b['status']:<15} {str(b['count']):>6} {str(raw):>6} "
              f"{hand_txt or '-':>6}  {'; '.join(verdicts)}")

    statuses = [b["status"] for b in report["boards"]]
    if report["exit_status"] == "finished" and any(s not in ("ok", "repeat-skipped") for s in statuses):
        flags.append(f"exit says finished but board statuses are {statuses}")
    if report["exit_status"] == "incomplete" and all(s in ("ok", "repeat-skipped") for s in statuses):
        flags.append("exit says incomplete but every board is ok")

    print()
    if flags:
        print("INDEPENDENT CHECK: FAILED")
        for f in flags:
            print(f"  - {f}")
        if report["exit_status"] == "finished":
            print("  The agent finished cleanly. Its answer is still wrong.")
        return 1
    if unchecked:
        print(f"INDEPENDENT CHECK: INCOMPLETE (no hand label for {unchecked})")
        return 2
    print("INDEPENDENT CHECK: PASSED")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
