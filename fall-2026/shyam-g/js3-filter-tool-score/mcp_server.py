"""A minimal Model Context Protocol tool server, written from scratch (stdio, JSON-RPC 2.0,
one JSON message per line). Standard library only.

It offers ONE capability: `score_posting`. It scores one posting with the filter in FILTER.md and
labels the three gate claims (role, location, experience) against the posting's own text.

What it can touch (by construction, not by declaration):
  reads   FILTER.md and data/corpus.jsonl (both in this folder)
  writes  transcripts/server-<timestamp>.jsonl in this folder: a copy of every message in both
          directions. This is the only write, and it is said in the tool description.
  network none. It imports no socket or HTTP module.
It cannot apply, email, message, log in, fetch, or change any file outside transcripts/.

Run:  python mcp_server.py            (speaks MCP on stdin/stdout)
"""
from __future__ import annotations

import datetime
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from js3.evidence import gate_claims, verdict  # noqa: E402
from js3.filter import decide, load_corpus, load_rules  # noqa: E402

PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
SERVER_INFO = {"name": "js3-score-posting", "version": "0.1.0"}
MAX_FIELD = 50_000

TOOL = {
    "name": "score_posting",
    "title": "Score one job posting against FILTER.md",
    "description": (
        "Score ONE job posting for the fictional persona Jordan Rivera, using the filter in FILTER.md. "
        "Give either posting_id (a posting from the local corpus collected 2026-11-10 from formlabs, "
        "spotify, palantir) or title+location+content. Returns the filter decision "
        "(keep/reject/cannot_tell), the score and threshold, the matched words, and a "
        "supported/contradicted/insufficient label for the role, location and experience claims, "
        "plus the abstention verdict ('relevant' / 'not relevant' / 'I cannot tell'). The output is a "
        "keyword filter's opinion, not a judgment that the job is worth applying to. Read-only with "
        "respect to postings and the filter; the server appends a transcript of this session to its "
        "own transcripts/ folder. No network access."),
    "inputSchema": {
        "type": "object",
        "properties": {
            "posting_id": {"type": "string", "description": "id of a posting in the local corpus"},
            "title": {"type": "string"},
            "location": {"type": "string"},
            "content": {"type": "string", "description": "posting text (plain text)"},
        },
        "additionalProperties": False,
    },
    "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True,
                    "openWorldHint": False},
}


class Transcript:
    def __init__(self) -> None:
        # JS3_TRANSCRIPT_DIR lets the tests send their transcripts to a temp folder
        d = pathlib.Path(os.environ.get("JS3_TRANSCRIPT_DIR") or ROOT / "transcripts")
        d.mkdir(exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S%f")
        self.path = d / f"server-{stamp}.jsonl"

    def log(self, direction: str, raw: str) -> None:
        rec = {"t": datetime.datetime.now().astimezone().isoformat(timespec="milliseconds"),
               "dir": direction, "raw": raw}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


_corpus: dict | None = None


def corpus() -> dict:
    global _corpus
    if _corpus is None:
        _corpus = {p["id"]: p for p in load_corpus()}
    return _corpus


def tool_error(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": True}


def score_posting(args: dict) -> dict:
    if not isinstance(args, dict):
        return tool_error("arguments must be an object")
    extra = set(args) - set(TOOL["inputSchema"]["properties"])
    if extra:
        return tool_error(f"unknown argument(s): {sorted(extra)}")
    for k, v in args.items():
        if not isinstance(v, str):
            return tool_error(f"{k} must be a string")
        if len(v) > MAX_FIELD:
            return tool_error(f"{k} is longer than {MAX_FIELD} characters")
    if "posting_id" in args:
        p = corpus().get(args["posting_id"].strip())
        if p is None:
            return tool_error(f"no posting with id {args['posting_id']!r} in the local corpus "
                              "(the server never fetches from the web)")
        source = "local corpus (collected 2026-11-10)"
    elif "title" in args:
        p = {"id": "(caller-supplied)", "title": args.get("title", ""),
             "location": args.get("location", ""), "content": args.get("content", "")}
        source = "caller-supplied text (not verified against any board)"
    else:
        return tool_error("give posting_id, or title (+ location, content)")
    rules = load_rules()
    d = decide(p, rules)
    g = gate_claims(p, rules)
    result = {"posting_id": p["id"], "title": p["title"], "location": p["location"], "source": source,
              "filter_version": rules["version"], "decision": d["decision"], "reason": d["reason"],
              "score": d["score"], "threshold": d["threshold"], "matched": d["checks"],
              "gate_claims": g, "verdict": verdict(g),
              "caveat": "Keyword filter output. Whether this job is worth the candidate's time is the "
                        "candidate's judgment."}
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=1)}],
            "structuredContent": result, "isError": False}


def handle(msg: dict) -> dict | None:
    """Return a response object, or None for notifications."""
    mid = msg.get("id")
    method = msg.get("method")
    is_notification = "id" not in msg
    if msg.get("jsonrpc") != "2.0" or not isinstance(method, str):
        return None if is_notification else err(mid, -32600, "Invalid Request")
    params = msg.get("params") or {}
    if method == "initialize":
        asked = params.get("protocolVersion")
        version = asked if asked in SUPPORTED_VERSIONS else PROTOCOL_VERSION
        return ok(mid, {"protocolVersion": version, "capabilities": {"tools": {"listChanged": False}},
                        "serverInfo": SERVER_INFO,
                        "instructions": "One read-only tool: score_posting. It scores; it does not decide "
                                        "what is worth applying to."})
    if method == "notifications/initialized" or method.startswith("notifications/"):
        return None
    if method == "ping":
        return ok(mid, {})
    if method == "tools/list":
        return ok(mid, {"tools": [TOOL]})
    if method == "tools/call":
        name = params.get("name")
        if name != TOOL["name"]:
            return err(mid, -32602, f"Unknown tool: {name}")
        try:
            return ok(mid, score_posting(params.get("arguments") or {}))
        except Exception as e:  # a tool failure is a result, not a protocol error
            return ok(mid, tool_error(f"internal error: {type(e).__name__}: {e}"))
    if is_notification:
        return None
    return err(mid, -32601, f"Method not found: {method}")


def ok(mid, result) -> dict:
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def err(mid, code, message) -> dict:
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}


def main() -> None:
    tr = Transcript()
    stdin = open(sys.stdin.fileno(), "r", encoding="utf-8", newline="\n", closefd=False)
    stdout = open(sys.stdout.fileno(), "w", encoding="utf-8", newline="\n", closefd=False)
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        tr.log("client->server", line)
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            resp = err(None, -32700, "Parse error")
        else:
            if isinstance(msg, list):
                resp = err(None, -32600, "Batches are not supported")
            elif not isinstance(msg, dict):
                resp = err(None, -32600, "Invalid Request")
            else:
                resp = handle(msg)
        if resp is not None:
            out = json.dumps(resp, ensure_ascii=False)
            tr.log("server->client", out)
            stdout.write(out + "\n")
            stdout.flush()


if __name__ == "__main__":
    main()
