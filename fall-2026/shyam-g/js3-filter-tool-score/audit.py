"""Reject audit (Chapter 7).

  python audit.py sample   # draw the audit sample (seed 7375); writes a BLIND sheet + a separate key
  python audit.py label    # label the sheet by hand, one posting at a time (no filter verdict shown)
  python audit.py report   # join hand verdicts to the key -> reports/AUDIT.md

The sheet (labels/audit_sheet.csv) never shows the filter's decision or score, so my hand
verdict can't be anchored on it. The key (reports/audit_key.json) holds the decisions.
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
import random
import sys

from js3.filter import decide, load_corpus, load_rules

ROOT = pathlib.Path(__file__).resolve().parent
SHEET = ROOT / "labels" / "audit_sheet.csv"
KEY = ROOT / "reports" / "audit_key.json"
SEED = 7375
N_RANDOM_REJECTS = 30        # assignment minimum
N_NONLOCATION_REJECTS = 10   # extra stratum: rejects that passed the location gate
SHEET_COLS = ["audit_id", "posting_id", "board", "title", "location", "url", "owner_verdict",
              "owner_note"]


def sample() -> None:
    rules = load_rules()
    corpus = load_corpus()
    dec = {p["id"]: decide(p, rules) for p in corpus}
    rejects = [p for p in corpus if dec[p["id"]]["decision"] == "reject"]
    kept = [p for p in corpus if dec[p["id"]]["decision"] == "keep"]
    rng = random.Random(SEED)
    rand_rej = rng.sample(rejects, N_RANDOM_REJECTS)
    taken = {p["id"] for p in rand_rej}
    nonloc = [p for p in rejects if dec[p["id"]]["reason"] != "reject:location" and p["id"] not in taken]
    nonloc_s = rng.sample(nonloc, min(N_NONLOCATION_REJECTS, len(nonloc)))
    taken |= {p["id"] for p in nonloc_s}
    t = rules["threshold"]
    # closest calls: passed every gate and scored within 1 of the threshold (either side),
    # or was rejected by a title/years rule while scoring at or above the threshold
    close = [p for p in corpus if p["id"] not in taken and (
        (dec[p["id"]]["reason"] in ("keep:score", "reject:score") and abs(dec[p["id"]]["score"] - t) <= 1)
        or (dec[p["id"]]["reason"] in ("reject:seniority_title", "reject:years") and dec[p["id"]]["score"] >= t))]
    taken |= {p["id"] for p in close}
    kept_s = [p for p in kept if p["id"] not in taken]   # few enough to take every one
    rows, key = [], {}
    strata = [("random_reject", rand_rej), ("nonlocation_reject", nonloc_s), ("close_call", close),
              ("kept", kept_s)]
    allp = [(s, p) for s, ps in strata for p in ps]
    rng.shuffle(allp)                       # mixed order: the sheet doesn't reveal the stratum
    for i, (s, p) in enumerate(allp, 1):
        aid = f"A{i:03d}"
        rows.append({"audit_id": aid, "posting_id": p["id"], "board": p["board"], "title": p["title"],
                     "location": p["location"], "url": p["url"], "owner_verdict": "", "owner_note": ""})
        d = dec[p["id"]]
        key[aid] = {"posting_id": p["id"], "stratum": s, "decision": d["decision"], "reason": d["reason"],
                    "score": d["score"], "filter_version": d["version"]}
    if SHEET.exists() and any(r.get("owner_verdict") for r in csv.DictReader(SHEET.open(encoding="utf-8"))):
        sys.exit(f"refusing to overwrite {SHEET}: it already has hand verdicts")
    SHEET.parent.mkdir(exist_ok=True)
    with SHEET.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SHEET_COLS)
        w.writeheader()
        w.writerows(rows)
    KEY.parent.mkdir(exist_ok=True)
    KEY.write_text(json.dumps({"seed": SEED, "filter_version": rules["version"],
                               "population": {"rejects": len(rejects), "kept": len(kept),
                                              "nonlocation_rejects": len(nonloc) + len(nonloc_s)},
                               "strata_sizes": {s: len(ps) for s, ps in strata}, "items": key},
                              indent=1), encoding="utf-8")
    print(f"sheet: {len(rows)} postings -> {SHEET}")
    print({s: len(ps) for s, ps in strata})


def label() -> None:
    corpus = {p["id"]: p for p in load_corpus()}
    rows = list(csv.DictReader(SHEET.open(encoding="utf-8")))
    print("Persona: Jordan Rivera (fictional). Entry-mid supply chain / procurement / planning / ops")
    print("analyst / project or product manager; Boston area or remote; <= 5 years.\n")
    print("r = relevant (worth Jordan's time), n = not relevant, u = unsure, s = skip, q = save & quit\n")
    try:
        for r in rows:
            if r["owner_verdict"]:
                continue
            p = corpus[r["posting_id"]]
            print("=" * 78)
            print(f"{r['audit_id']}  {p['title']}  |  {p['location']}  |  {p['board']}")
            print(p["url"])
            print("-" * 78)
            print(p["content"][:1800])
            if len(p["content"]) > 1800:
                print(f"... [{len(p['content']) - 1800} more chars at the URL]")
            while True:
                a = input("\nverdict [r/n/u/s/q]: ").strip().lower()
                if a in ("r", "n", "u", "s", "q"):
                    break
            if a == "q":
                break
            if a == "s":
                continue
            r["owner_verdict"] = {"r": "relevant", "n": "not_relevant", "u": "unsure"}[a]
            r["owner_note"] = input("note (optional): ").strip()
    finally:
        with SHEET.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=SHEET_COLS)
            w.writeheader()
            w.writerows(rows)
        done = sum(1 for r in rows if r["owner_verdict"])
        print(f"\nsaved {done}/{len(rows)} hand verdicts to {SHEET}")


# ---------- spreadsheet alternative to `label`: export a sheet to fill in, then import it ----------

EDIT = ROOT / "labels" / "audit_verdicts_edit.csv"
EDIT_COLS = ["audit_id", "board", "title", "location", "url", "verdict", "note"]
CODES = {"r": "relevant", "n": "not_relevant", "u": "unsure",
         "relevant": "relevant", "not_relevant": "not_relevant", "unsure": "unsure"}


def export() -> None:
    """Write labels/audit_verdicts_edit.csv (blind: no filter decision), prefilled with any saved verdicts."""
    if EDIT.exists():
        sys.exit(f"{EDIT} already exists; not overwriting your edits")
    rows = list(csv.DictReader(SHEET.open(encoding="utf-8")))
    back = {"relevant": "r", "not_relevant": "n", "unsure": "u", "": ""}
    with EDIT.open("w", newline="", encoding="utf-8-sig") as f:  # BOM so Excel reads UTF-8
        w = csv.DictWriter(f, fieldnames=EDIT_COLS)
        w.writeheader()
        for r in rows:
            w.writerow({"audit_id": r["audit_id"], "board": r["board"], "title": r["title"],
                        "location": r["location"], "url": r["url"],
                        "verdict": back[r["owner_verdict"]], "note": r["owner_note"]})
    print(f"wrote {EDIT}: fill the verdict column with r / n / u, then run: audit.py import")


def import_() -> None:
    """Copy verdicts from labels/audit_verdicts_edit.csv into labels/audit_sheet.csv."""
    edits = {e["audit_id"].strip(): e for e in csv.DictReader(EDIT.open(encoding="utf-8-sig"))}
    rows = list(csv.DictReader(SHEET.open(encoding="utf-8")))
    bad = [f"{k}: {e['verdict']!r}" for k, e in edits.items()
           if e["verdict"].strip().lower() not in CODES and e["verdict"].strip()]
    if bad:
        sys.exit("verdict must be r, n or u (or blank). Fix these rows:\n  " + "\n  ".join(bad))
    for r in rows:
        e = edits.get(r["audit_id"])
        if e is None:
            continue
        v = e["verdict"].strip().lower()
        r["owner_verdict"] = CODES.get(v, "")
        r["owner_note"] = e["note"].strip()
    with SHEET.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SHEET_COLS)
        w.writeheader()
        w.writerows(rows)
    done = sum(1 for r in rows if r["owner_verdict"])
    print(f"imported: {done}/{len(rows)} postings have a hand verdict in {SHEET}")
    missing = [r["audit_id"] for r in rows if not r["owner_verdict"]]
    if missing:
        print("still blank: " + ", ".join(missing))


# ---------- exact binomial (Clopper-Pearson) without scipy ----------

def _binom_cdf(k: int, n: int, p: float) -> float:
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    def solve(f, lo=0.0, hi=1.0):
        for _ in range(100):
            mid = (lo + hi) / 2
            if f(mid):
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2
    lower = 0.0 if k == 0 else solve(lambda p: 1 - _binom_cdf(k - 1, n, p) >= alpha / 2)
    upper = 1.0 if k == n else solve(lambda p: _binom_cdf(k, n, p) <= alpha / 2)
    return lower, upper


def report() -> None:
    key = json.loads(KEY.read_text(encoding="utf-8"))
    rows = list(csv.DictReader(SHEET.open(encoding="utf-8")))
    corpus = {p["id"]: p for p in load_corpus()}
    labeled = [r for r in rows if r["owner_verdict"]]
    out = ["# Reject audit: hand verdicts vs. the filter", "",
           f"Generated by `python audit.py report` from `labels/audit_sheet.csv` (my hand verdicts) and "
           f"`reports/audit_key.json` (the filter's decisions, filter v{key['filter_version']}, seed {key['seed']}).",
           f"Hand verdicts filled: **{len(labeled)} / {len(rows)}**.", ""]
    if not labeled:
        out.append("**No hand verdicts yet. Run `python audit.py label`.** No error figures are reported "
                   "until the owner has judged the postings.")
        (ROOT / "reports" / "AUDIT.md").write_text("\n".join(out) + "\n", encoding="utf-8")
        print("\n".join(out))
        return
    pop = key["population"]
    out += ["| Stratum | How drawn | n judged | Filter said | Hand: relevant | Hand: not | Unsure | Filter wrong |",
            "|---|---|---|---|---|---|---|---|"]
    how = {"random_reject": f"simple random sample of all {pop['rejects']} rejects",
           "nonlocation_reject": f"random sample of rejects that passed the location gate",
           "close_call": "every posting within 1 point of the threshold, or excluded by title/years "
                         "while scoring ≥ threshold",
           "kept": "every kept posting not already drawn above"}
    stats = {}
    for s in ("random_reject", "nonlocation_reject", "close_call", "kept"):
        rs = [r for r in labeled if key["items"][r["audit_id"]]["stratum"] == s]
        rel = sum(r["owner_verdict"] == "relevant" for r in rs)
        nr = sum(r["owner_verdict"] == "not_relevant" for r in rs)
        un = sum(r["owner_verdict"] == "unsure" for r in rs)
        wrong = [r for r in rs if r["owner_verdict"] != "unsure" and
                 (r["owner_verdict"] == "relevant") != (key["items"][r["audit_id"]]["decision"] == "keep")]
        stats[s] = (len(rs) - un, len(wrong), wrong)
        said = sorted({key["items"][r["audit_id"]]["decision"] for r in rs})
        out.append(f"| {s} | {how[s]} | {len(rs)} | {'/'.join(said)} | {rel} | {nr} | {un} | {len(wrong)} |")
    out += ["", "## What the random-reject sample can and cannot show", ""]
    n, k, _ = stats["random_reject"]
    if n:
        lo, hi = clopper_pearson(k, n)
        out += [f"- {k} of {n} randomly drawn rejects were wrong by my hand verdict (unsure excluded).",
                f"- 95% exact (Clopper-Pearson) interval for the false-reject share **among the "
                f"{pop['rejects']} rejects of this one corpus**: {lo:.1%} to {hi:.1%}.",
                f"- In postings: roughly {lo * pop['rejects']:.0f} to {hi * pop['rejects']:.0f} of the "
                f"{pop['rejects']} rejects could be relevant. This is a sample estimate, not a measured rate.",
                "- It does **not** describe other boards, other dates, or another persona. It is also "
                "dominated by easy location rejects (New York, London, D.C.), so it says little about the "
                "hard rejects. That's why the non-location stratum and the close calls are judged separately "
                "and are not pooled into the random-sample figure.",
                "- Every figure depends on my own hand verdicts being right. A second rater was not used."]
    for s in ("nonlocation_reject", "close_call", "kept"):
        n2, k2, _ = stats[s]
        if n2:
            lo, hi = clopper_pearson(k2, n2)
            out.append(f"- {s}: {k2}/{n2} wrong (95% exact interval {lo:.0%} to {hi:.0%}; "
                       f"{'not a random sample, so it does not generalize' if s == 'close_call' else 'small n'}).")
    out += ["", "## Every disagreement", "",
            "| audit_id | stratum | title | location | filter | reason | score | hand | note |",
            "|---|---|---|---|---|---|---|---|---|"]
    for s in stats:
        for r in stats[s][2]:
            it = key["items"][r["audit_id"]]
            p = corpus[r["posting_id"]]
            out.append(f"| {r['audit_id']} | {s} | {p['title']} | {p['location']} | {it['decision']} | "
                       f"{it['reason']} | {it['score']} | {r['owner_verdict']} | {r['owner_note']} |")
    (ROOT / "reports" / "AUDIT.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    {"sample": sample, "label": label, "report": report,
     "export": export, "import": import_}[sys.argv[1]]()
