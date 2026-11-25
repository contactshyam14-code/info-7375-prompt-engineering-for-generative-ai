"""What moves the score (Chapter 9): change ONE object at a time, measure on held-out labels.

  python experiments.py filter          # E0-E2: the filter file and a setting (no Claude calls)
  python experiments.py claude          # E3-E5: prompt, context, tool list (real claude -p calls)
  python experiments.py report          # -> reports/SCORE-REPORT-data.md

Held-out labels: labels/js1_hand_labels.csv rows with split=heldout (10 postings I labeled for JS1 in
October, before any JS3 code existed). Dev rows (split=dev) are reported alongside but were the
only labels used to decide changes. All 20 postings are in the 2026-11-10 corpus.
Claude raw responses: reports/claude/experiments/<condition>/<id>.json (with timestamps).
"""
from __future__ import annotations

import concurrent.futures as cf
import copy
import csv
import datetime
import json
import pathlib
import re
import subprocess
import sys
import tempfile

from js3.claude_cli import ask_claude, NEUTRAL_CWD
from js3.filter import decide, load_corpus, load_rules

ROOT = pathlib.Path(__file__).resolve().parent
EXP = ROOT / "reports" / "claude" / "experiments"
OUT = ROOT / "reports" / "experiments.json"


def labels(split: str) -> dict[str, bool]:
    return {r["posting_id"]: r["hand_label"].strip() == "relevant"
            for r in csv.DictReader((ROOT / "labels" / "js1_hand_labels.csv").open(encoding="utf-8"))
            if r["split"] == split}


def metrics(pred: dict[str, bool | None], gold: dict[str, bool]) -> dict:
    tp = sum(1 for i, g in gold.items() if pred.get(i) is True and g)
    fp = sum(1 for i, g in gold.items() if pred.get(i) is True and not g)
    fn = sum(1 for i, g in gold.items() if pred.get(i) is not True and g)
    correct = sum(1 for i, g in gold.items() if (pred.get(i) is True) == g)
    invalid = sum(1 for i in gold if pred.get(i) is None)
    return {"n": len(gold), "correct": correct, "tp": tp, "fp": fp, "fn": fn, "invalid_or_missing": invalid}


def rules_at(rev: str) -> dict:
    """FILTER.md rules as of a git revision (so 'the filter file' is the object that changes)."""
    text = subprocess.run(["git", "show", f"{rev}:FILTER.md"], capture_output=True, text=True,
                          encoding="utf-8", cwd=ROOT, check=True).stdout
    tmp = pathlib.Path(tempfile.gettempdir()) / f"FILTER-{rev}.md"
    tmp.write_text(text, encoding="utf-8")
    return load_rules(tmp)


def run_filter() -> dict:
    corpus = {p["id"]: p for p in load_corpus()}
    cur = load_rules()
    v1 = rules_at("85730d3")
    t3 = copy.deepcopy(cur)
    t3["threshold"] = 3
    conds = {"E0 baseline: FILTER.md v" + cur["version"]: cur,
             "E1 filter file: FILTER.md v1.0.0 (85730d3) instead of v" + cur["version"]: v1,
             "E2 setting: threshold 4 -> 3 (else v" + cur["version"] + ")": t3}
    res = {}
    for name, r in conds.items():
        res[name] = {}
        for split in ("dev", "heldout"):
            gold = labels(split)
            pred = {i: decide(corpus[i], r)["decision"] == "keep" for i in gold}
            res[name][split] = metrics(pred, gold) | {"pred": pred}
    return res


# ---------- Claude conditions ----------

def persona_block() -> str:
    p = json.loads((ROOT / "persona" / "jordan_rivera.json").read_text(encoding="utf-8"))
    return json.dumps({k: p[k] for k in ("target_titles", "skills", "locations", "exclude_keywords")}, indent=1)


def posting_block(p: dict, context: str) -> str:
    d = {"posting_id": p["id"], "title": p["title"], "location": p["location"]}
    if context == "full":
        d["content"] = p["content"][:6000]
    return json.dumps(d, ensure_ascii=False, indent=1)


def prompt_for(cond: str, p: dict) -> str:
    name = "relevance_A.txt" if cond != "E3_prompt_B" else "relevance_B.txt"
    t = (ROOT / "prompts" / name).read_text(encoding="utf-8")
    context = "title_only" if cond == "E4_context_title_only" else "full"
    s = t.replace("{{RESUME}}", persona_block()).replace("{{POSTING}}", posting_block(p, context))
    if cond == "E5_tools_score_posting":
        s += ("\n\nYou have one tool, score_posting, which runs a keyword filter on a posting_id. "
              "You may call it before you answer. Your final reply must still be the JSON object only.")
    return s


def ask_with_tool(prompt: str) -> str:
    cfg = {"mcpServers": {"js3": {"command": sys.executable, "args": [str(ROOT / "mcp_server.py")]}}}
    cfg_path = pathlib.Path(tempfile.gettempdir()) / "js3-mcp-config.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    return ask_claude(prompt, ["--mcp-config", str(cfg_path), "--strict-mcp-config", "--tools", "",
                               "--allowedTools", "mcp__js3__score_posting"])


CLAUDE_CONDS = ["E3_prompt_A", "E3_prompt_B", "E4_context_title_only", "E5_tools_score_posting"]


def one(cond: str, p: dict) -> None:
    f = EXP / cond / f"{p['id']}.json"
    if f.exists():
        return
    prompt = prompt_for(cond, p)
    asked = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        raw = ask_with_tool(prompt) if cond == "E5_tools_score_posting" else ask_claude(prompt)
    except Exception as e:
        raw = f"ERROR: {e}"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"posting_id": p["id"], "condition": cond, "asked_at": asked,
                             "via": "claude -p (Claude Code CLI 2.1.316), fresh session, run from an empty temp dir",
                             "prompt": prompt, "raw_response": raw}, indent=1, ensure_ascii=False),
                 encoding="utf-8")
    print(cond, p["id"], "done", flush=True)


def run_claude() -> None:
    corpus = {p["id"]: p for p in load_corpus()}
    ids = list(labels("heldout"))
    jobs = [(c, corpus[i]) for c in CLAUDE_CONDS for i in ids]
    with cf.ThreadPoolExecutor(4) as ex:
        list(ex.map(lambda a: one(*a), jobs))


def parse_verdict(raw: str) -> bool | None:
    m = re.search(r"\{.*\}", raw or "", re.S)
    try:
        v = json.loads(m.group(0)).get("verdict")
    except Exception:
        return None
    return {"relevant": True, "not_relevant": False}.get(v)


def report() -> None:
    res = {"filter": run_filter(), "claude": {}}
    gold = labels("heldout")
    for c in CLAUDE_CONDS:
        pred, stamps = {}, []
        for i in gold:
            f = EXP / c / f"{i}.json"
            if f.exists():
                d = json.loads(f.read_text(encoding="utf-8"))
                pred[i] = parse_verdict(d["raw_response"])
                stamps.append(d["asked_at"])
        res["claude"][c] = metrics(pred, gold) | {"pred": pred, "asked": [min(stamps), max(stamps)] if stamps else None}
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    titles = {p["id"]: p["title"] for p in load_corpus()}
    L = ["# Experiment results (generated by `python experiments.py report`)", "",
         "Held-out = the 10 JS1 held-out labels; dev = the 10 JS1 dev labels. 'correct' counts agreement with my hand label.", "",
         "| Condition | Object changed | dev correct | held-out correct | held-out TP / FP / FN | invalid |",
         "|---|---|---|---|---|---|"]
    for name, r in res["filter"].items():
        h = r["heldout"]
        L.append(f"| {name} | {'—' if name.startswith('E0') else name.split(':')[0][3:]} | {r['dev']['correct']}/10 | "
                 f"**{h['correct']}/10** | {h['tp']} / {h['fp']} / {h['fn']} | 0 |")
    for c, r in res["claude"].items():
        L.append(f"| {c} | {c.split('_')[1]} | not run | **{r['correct']}/10** | {r['tp']} / {r['fp']} / {r['fn']} | "
                 f"{r['invalid_or_missing']} |")
    L += ["", "## Per-posting predictions on the held-out set (R = relevant, n = not, ? = invalid/missing)", "",
          "| posting | title | hand | " + " | ".join(list(res["filter"]) [:0] + ["E0", "E1", "E2"] + CLAUDE_CONDS) + " |",
          "|---|---|---|" + "---|" * (3 + len(CLAUDE_CONDS))]
    sym = lambda v: "?" if v is None else ("R" if v else "n")
    fkeys = list(res["filter"])
    for i, g in gold.items():
        row = [sym(res["filter"][k]["heldout"]["pred"][i]) for k in fkeys]
        row += [sym(res["claude"][c]["pred"].get(i)) for c in CLAUDE_CONDS]
        L.append(f"| {i} | {titles[i]} | {sym(g)} | " + " | ".join(row) + " |")
    L += ["", "Claude call windows: " + "; ".join(f"{c}: {r['asked']}" for c, r in res["claude"].items())]
    (ROOT / "reports" / "SCORE-REPORT-data.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    {"filter": lambda: print(json.dumps(run_filter(), indent=1)), "claude": run_claude, "report": report}[sys.argv[1]]()
