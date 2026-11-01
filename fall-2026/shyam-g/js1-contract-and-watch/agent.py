"""Job-Search Agent 1: watch one board, judge new postings two ways.

Implements CONTRACT.md. Python 3.12, standard library only (pytest for tests).

  python agent.py run --board <token>                      # live fetch (allow-listed host only)
  python agent.py run --board <token> --from-file f.json --label seeded
  python agent.py run --board <token> --claude             # also ask Claude (a judgment)
"""
import argparse
import datetime as dt
import html
import json
import pathlib
import re
import subprocess
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).parent
ALLOWLIST_FILE = ROOT / "allowlist.txt"
STATE = ROOT / "state"
OUT_DIR = ROOT / "output"
ENDPOINT = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"

# CONTRACT section 4 leaves this open: HTML in `content` is stripped before matching.
# Greenhouse returns entity-escaped HTML, so "&lt;li&gt;SQL" would otherwise be the text.
STRIP_HTML = True

VERDICTS = ("relevant", "not_relevant")
RESUME_FIELDS = ("target_titles", "skills", "locations", "exclude_keywords")
POSTING_FIELDS = ("title", "content", "location")
CLAUDE_KEYS = {"posting_id", "verdict", "resume_fields", "posting_fields", "justification"}
MIN_SKILLS = 2


# ---------- fetching (allow-list enforced) ----------

def allowlist() -> set[str]:
    lines = ALLOWLIST_FILE.read_text(encoding="utf-8").splitlines()
    return {ln.strip().lower() for ln in lines if ln.strip() and not ln.startswith("#")}


def fetch(url: str) -> bytes:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if urllib.parse.urlparse(url).scheme != "https" or host not in allowlist():
        raise PermissionError(f"refused: host {host!r} is not on the allow-list")
    req = urllib.request.Request(url, headers={"User-Agent": "js1-job-agent (course project)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


# ---------- the rule (a record) ----------

def plain_text(s: str) -> str:
    if not STRIP_HTML:
        return s or ""
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    return html.unescape(s)


def matched(terms, text: str) -> list[str]:
    """Terms that appear as whole words/phrases, case-insensitive (CONTRACT section 4)."""
    text = text.lower()
    return [t for t in terms if re.search(r"(?<!\w)" + re.escape(t.lower()) + r"(?!\w)", text)]


def rule_checks(resume: dict, posting: dict) -> dict:
    title = posting.get("title") or ""
    location = (posting.get("location") or {}).get("name") or ""
    content = plain_text(posting.get("content") or "")
    return {
        "title": matched(resume["target_titles"], title),
        "location": matched(list(resume["locations"]) + ["remote"], location),
        "skills": sorted(set(matched(resume["skills"], content))),
        "exclusions": sorted(set(matched(resume["exclude_keywords"], title + "\n" + content))),
    }


def judge_rule(resume: dict, posting: dict) -> str:
    c = rule_checks(resume, posting)
    ok = c["title"] and c["location"] and len(c["skills"]) >= MIN_SKILLS and not c["exclusions"]
    return "relevant" if ok else "not_relevant"


def rule_justification(resume: dict, posting: dict) -> str:
    c = rule_checks(resume, posting)
    parts = [
        f"resume.target_titles vs posting.title: {c['title'] or 'no match'}",
        f"resume.locations(+remote) vs posting.location.name: {c['location'] or 'no match'}",
        f"resume.skills vs posting.content: {c['skills'] or 'none'} "
        f"({len(c['skills'])}/{MIN_SKILLS} needed)",
        f"resume.exclude_keywords vs posting.title+content: {c['exclusions'] or 'none'}",
    ]
    return "; ".join(parts)


# ---------- the watch ----------

def new_postings(seen_ids: set, response: dict, baseline: bool = False) -> list:
    if baseline:
        return []
    return [j for j in response.get("jobs", []) if str(j["id"]) not in seen_ids]


def load_seen(state: pathlib.Path = STATE) -> set[str] | None:
    f = state / "seen_ids.json"
    if not f.exists():
        return None
    return set(json.loads(f.read_text(encoding="utf-8"))["seen_ids"])


def save_seen(seen: set[str], board: str, run_at: str, state: pathlib.Path = STATE) -> None:
    state.mkdir(exist_ok=True)
    (state / "seen_ids.json").write_text(json.dumps(
        {"board": board, "updated": run_at, "seen_ids": sorted(seen)}, indent=2), encoding="utf-8")


# ---------- Claude (a judgment) ----------

PROMPT_FILE = ROOT / "prompts" / "baseline.txt"


def build_prompt(resume: dict, posting: dict, template_path: pathlib.Path = PROMPT_FILE) -> str:
    # Only the fields the rule uses go to Claude: no name, email or phone.
    profile = {k: resume[k] for k in RESUME_FIELDS}
    post = {
        "posting_id": str(posting["id"]),
        "title": posting.get("title"),
        "location": (posting.get("location") or {}).get("name"),
        "content": plain_text(posting.get("content") or "")[:6000],
    }
    return (template_path.read_text(encoding="utf-8")
            .replace("{{RESUME}}", json.dumps(profile, indent=2))
            .replace("{{POSTING}}", json.dumps(post, indent=2)))


def validate_claude(raw: str, posting_id: str, resume: dict) -> dict:
    try:
        out = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(f"not JSON: {e}")
    if not isinstance(out, dict) or set(out) != CLAUDE_KEYS:
        raise ValueError(f"keys must be exactly {sorted(CLAUDE_KEYS)}")
    if out["posting_id"] != str(posting_id):
        raise ValueError(f"posting_id {out['posting_id']!r} != {posting_id!r}")
    if out["verdict"] not in VERDICTS:
        raise ValueError(f"verdict {out['verdict']!r} not in {VERDICTS}")
    for key, allowed in (("resume_fields", set(RESUME_FIELDS) & set(resume)),
                         ("posting_fields", set(POSTING_FIELDS))):
        vals = out[key]
        if not isinstance(vals, list) or not vals:
            raise ValueError(f"{key} must be a non-empty list")
        bad = [v for v in vals if v not in allowed]
        if bad:
            raise ValueError(f"{key} names fields that do not exist: {bad}")
    if not isinstance(out["justification"], str) or not out["justification"].strip():
        raise ValueError("justification is empty")
    return out


def ask_claude(prompt: str, model: str | None = None) -> str:
    """One fresh, tool-less conversation via the Claude Code CLI (`claude -p`)."""
    cmd = ["claude", "-p", "--output-format", "text", "--tools", ""]
    if model:
        cmd += ["--model", model]
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                       shell=sys.platform == "win32", timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"claude exited {r.returncode}: {r.stderr.strip()[:300]}")
    return r.stdout.strip()


def claude_verdict(resume: dict, posting: dict, model: str | None = None) -> dict:
    raw = ask_claude(build_prompt(resume, posting), model)
    try:
        v = validate_claude(raw, str(posting["id"]), resume)
        return {"label": "Claude's judgment (not a fact)", "valid": True, **v}
    except ValueError as e:
        return {"label": "Claude's judgment (not a fact)", "valid": False,
                "rejected_because": str(e), "raw": raw}


# ---------- run ----------

def run(board: str, from_file: str | None, label: str, use_claude: bool, resume_path: str,
        model: str | None = None, state: pathlib.Path = STATE) -> dict:
    run_at = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    stamp = run_at[:19].replace(":", "")
    resume = json.loads(pathlib.Path(resume_path).read_text(encoding="utf-8"))

    if from_file:
        body = pathlib.Path(from_file).read_bytes()
        source = f"{label}: saved file {pathlib.Path(from_file).as_posix()}"
    else:
        url = ENDPOINT.format(board=urllib.parse.quote(board))
        body = fetch(url)
        source = f"live: {url}"
    (state / "raw").mkdir(parents=True, exist_ok=True)
    raw_path = state / "raw" / f"{stamp}-{board}-{label}.json"
    raw_path.write_bytes(body)
    response = json.loads(body)

    seen = load_seen(state)
    baseline = seen is None
    new = new_postings(seen or set(), response, baseline=baseline)
    results = []
    for p in new:
        rec = {
            "posting_id": str(p["id"]),
            "title": p.get("title"),
            "location": (p.get("location") or {}).get("name"),
            "url": p.get("absolute_url"),
            "rule_verdict": judge_rule(resume, p),
            "rule_label": "record (recomputable from CONTRACT section 4)",
            "justification": rule_justification(resume, p),
        }
        if use_claude:
            rec["claude"] = claude_verdict(resume, p, model)
        results.append(rec)

    all_ids = {str(j["id"]) for j in response.get("jobs", [])}
    report = {"run_at": run_at, "board": board, "source": source,
              "raw_saved": raw_path.relative_to(ROOT).as_posix(), "baseline": baseline,
              "postings_in_response": len(all_ids), "new": len(results), "results": results}
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / f"run-{stamp}-{label}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    # Ids are marked seen only after the report is on disk, so a crash cannot swallow new postings.
    save_seen((seen or set()) | all_ids, board, run_at, state)
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--board", required=True, help="Greenhouse board token")
    r.add_argument("--from-file", help="use a saved response instead of fetching")
    r.add_argument("--label", default="live", help="tag for this run, e.g. live or seeded")
    r.add_argument("--resume", default=str(ROOT / "persona" / "jordan_rivera.json"))
    r.add_argument("--claude", action="store_true", help="also get Claude's judgment")
    r.add_argument("--model", help="Claude model alias passed to `claude -p`")
    r.add_argument("--state", default=str(STATE), help="state folder (seen ids + raw responses)")
    a = ap.parse_args(argv)
    rep = run(a.board, a.from_file, a.label, a.claude, a.resume, a.model, pathlib.Path(a.state).resolve())
    print(f"{rep['run_at']}  board={rep['board']}  {rep['source']}")
    print(f"raw saved: {rep['raw_saved']}  postings: {rep['postings_in_response']}  "
          f"baseline: {rep['baseline']}  new: {rep['new']}")
    for x in rep["results"]:
        line = f"  [{x['posting_id']}] {x['title']} | {x['location']}\n    RULE (record): {x['rule_verdict']}"
        if "claude" in x:
            c = x["claude"]
            line += (f"\n    CLAUDE (judgment, not fact): {c['verdict']}" if c["valid"]
                     else f"\n    CLAUDE output REJECTED: {c['rejected_because']}")
        print(line + f"\n    why: {x['justification']}")


if __name__ == "__main__":
    main()
