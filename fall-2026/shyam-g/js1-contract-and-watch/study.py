"""Step 4 tooling: pick postings to label, sample Claude, run the prompt experiment.

  python study.py pick --raw state/raw/<file>.json          # writes labels/hand_labels.csv (hand_label blank)
  python study.py sample --n 4 --ids 1,2,3,4,5               # 5 postings x 4 fresh conversations
  python study.py experiment --prompt prompts/baseline.txt --split dev
"""
import argparse
import csv
import json
import pathlib
import random
from collections import Counter

import agent

ROOT = agent.ROOT
LABELS = ROOT / "labels" / "hand_labels.csv"
RESULTS = ROOT / "results"
RESUME = json.loads((ROOT / "persona" / "jordan_rivera.json").read_text(encoding="utf-8"))


def postings_from(raw_path: str) -> dict[str, dict]:
    jobs = json.loads(pathlib.Path(raw_path).read_text(encoding="utf-8"))["jobs"]
    return {str(j["id"]): j for j in jobs}


def read_labels() -> list[dict]:
    with LABELS.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def pick(raw_path: str, seed: int = 7375) -> None:
    """20 postings: every target-title hit (up to 10) plus random others; then a seeded dev/held-out split."""
    jobs = postings_from(raw_path)
    hits = [i for i, j in jobs.items() if agent.matched(RESUME["target_titles"], j["title"])]
    rng = random.Random(seed)
    hits = rng.sample(sorted(hits), min(10, len(hits)))
    others = rng.sample(sorted(set(jobs) - set(hits)), 20 - len(hits))
    chosen = hits + others
    rng.shuffle(chosen)
    LABELS.parent.mkdir(exist_ok=True)
    with LABELS.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["posting_id", "split", "title", "location", "url", "hand_label", "hand_note"])
        for n, i in enumerate(chosen):
            j = jobs[i]
            w.writerow([i, "dev" if n < 10 else "heldout", j["title"],
                        (j.get("location") or {}).get("name"), j.get("absolute_url"), "", ""])
    print(f"wrote {LABELS.relative_to(ROOT)}: {len(chosen)} postings ({len(hits)} title hits). "
          "Fill hand_label (relevant/not_relevant) BEFORE running sample or experiment.")


def judge_many(jobs, ids, prompt_path, n, out_name):
    labels = {r["posting_id"]: r["hand_label"] for r in read_labels()}
    rows = []
    for i in ids:
        p = jobs[i]
        for k in range(n):
            raw = agent.ask_claude(agent.build_prompt(RESUME, p, pathlib.Path(prompt_path)))
            try:
                v = agent.validate_claude(raw, i, RESUME)["verdict"]
            except ValueError as e:
                v = f"INVALID: {e}"
            rows.append({"posting_id": i, "try": k + 1, "claude_verdict": v,
                         "rule_verdict": agent.judge_rule(RESUME, p), "hand_label": labels.get(i, ""),
                         "raw": raw})
            print(i, k + 1, "valid" if not v.startswith("INVALID") else "INVALID", flush=True)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / out_name).write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return rows


def summarize(rows):
    by = {}
    for r in rows:
        by.setdefault(r["posting_id"], []).append(r)
    print("\nposting_id | claude verdicts | agree w/ hand | rule | hand")
    for i, rs in by.items():
        c = Counter(r["claude_verdict"] for r in rs)
        hand = rs[0]["hand_label"]
        agree = sum(r["claude_verdict"] == hand for r in rs)
        print(f"{i} | {dict(c)} | {agree}/{len(rs)} | {rs[0]['rule_verdict']} | {hand or 'UNLABELED'}")
    labeled = [r for r in rows if r["hand_label"]]
    if labeled:
        ok = sum(r["claude_verdict"] == r["hand_label"] for r in labeled)
        print(f"\nClaude pass rate vs hand labels: {ok}/{len(labeled)}")
        rule_ok = len({r['posting_id'] for r in labeled if r["rule_verdict"] == r["hand_label"]})
        print(f"Rule pass rate vs hand labels: {rule_ok}/{len({r['posting_id'] for r in labeled})}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("pick"); a.add_argument("--raw", required=True)
    s = sub.add_parser("sample"); s.add_argument("--raw", required=True)
    s.add_argument("--ids", required=True); s.add_argument("--n", type=int, default=4)
    s.add_argument("--prompt", default=str(agent.PROMPT_FILE))
    e = sub.add_parser("experiment"); e.add_argument("--raw", required=True)
    e.add_argument("--prompt", required=True); e.add_argument("--split", choices=["dev", "heldout"], required=True)
    c = sub.add_parser("score"); c.add_argument("file", help="results/<file>.json; joins hand labels and prints pass rates")
    args = ap.parse_args()
    if args.cmd == "pick":
        return pick(args.raw)
    if args.cmd == "score":
        rows = json.loads((RESULTS / args.file).read_text(encoding="utf-8"))
        labels = {r["posting_id"]: r["hand_label"] for r in read_labels()}
        if any(not labels.get(r["posting_id"]) for r in rows):
            raise SystemExit("refused: some postings in this file have no hand label yet.")
        for r in rows:
            r["hand_label"] = labels[r["posting_id"]]
        (RESULTS / args.file).write_text(json.dumps(rows, indent=2), encoding="utf-8")
        return summarize(rows)
    jobs = postings_from(args.raw)
    # Claude's verdicts are saved but never printed here, so they cannot steer hand labeling.
    if args.cmd == "sample":
        judge_many(jobs, args.ids.split(","), args.prompt, args.n, "sampling.json")
    else:
        ids = [r["posting_id"] for r in read_labels() if r["split"] == args.split]
        name = f"experiment-{pathlib.Path(args.prompt).stem}-{args.split}.json"
        rows = judge_many(jobs, ids, args.prompt, 1, name)
    print(f"saved results/. Score after labeling: python study.py score <file>")


if __name__ == "__main__":
    main()
