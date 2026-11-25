"""Measure one proposed rule change before it goes into FILTER.md.

  python measure_rules.py '<json patch>' [name] [--base path/to/FILTER.md]
e.g. python measure_rules.py '{"require_role_word": true}' P1

Reports (a) every posting in the corpus whose decision changes, and (b) agreement with each set of
labels that exists: JS1 dev labels (labels/js1_hand_labels.csv, split=dev) and my audit hand verdicts
(labels/audit_sheet.csv). JS1 held-out labels are NOT used here; they're kept for SCORE-REPORT.md.
Writes reports/rule-changes/<name>.json.
"""
import copy, csv, json, pathlib, sys
from js3.filter import decide, load_corpus, load_rules

ROOT = pathlib.Path(__file__).resolve().parent

def labels():
    out = {}
    for r in csv.DictReader((ROOT / "labels" / "js1_hand_labels.csv").open(encoding="utf-8")):
        if r["split"] == "dev":
            out.setdefault("js1_dev", {})[r["posting_id"]] = r["hand_label"].strip() == "relevant"
    sheet = ROOT / "labels" / "audit_sheet.csv"
    if sheet.exists():
        for r in csv.DictReader(sheet.open(encoding="utf-8")):
            if r["owner_verdict"] in ("relevant", "not_relevant"):
                out.setdefault("audit_hand", {})[r["posting_id"]] = r["owner_verdict"] == "relevant"
    return out

def agree(rules, corpus, lab):
    return {k: sum((decide(corpus[i], rules)["decision"] == "keep") == v for i, v in L.items()) / len(L)
            for k, L in lab.items()} | {k + "_n": len(L) for k, L in lab.items()}

def main(patch_json: str, name: str, base_path=None):
    base = load_rules(base_path) if base_path else load_rules()
    new = copy.deepcopy(base)
    for k, v in json.loads(patch_json).items():
        if isinstance(v, dict) and set(v) <= {"add", "remove"}:
            new[k] = [t for t in new[k] if t not in v.get("remove", [])] + v.get("add", [])
        else:
            new[k] = v
    corpus = {p["id"]: p for p in load_corpus()}
    changed = []
    for i, p in corpus.items():
        a, b = decide(p, base), decide(p, new)
        if a["decision"] != b["decision"]:
            changed.append({"id": i, "title": p["title"], "location": p["location"],
                            "before": a["reason"], "after": b["reason"]})
    lab = labels()
    res = {"patch": json.loads(patch_json), "base_version": base["version"],
           "changed_decisions": changed, "agreement_before": agree(base, corpus, lab),
           "agreement_after": agree(new, corpus, lab)}
    d = ROOT / "reports" / "rule-changes"; d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{name}: {len(changed)} decisions change")
    for c in changed: print(f"  {c['before']:>24} -> {c['after']:<24} {c['title']} | {c['location']}")
    print("  agreement before:", res["agreement_before"]); print("  agreement after: ", res["agreement_after"])

if __name__ == "__main__":
    args = sys.argv[1:]
    base_path = None
    if "--base" in args:
        i = args.index("--base"); base_path = args[i + 1]; del args[i:i + 2]
    main(args[0], args[1] if len(args) > 1 else "change", base_path)
