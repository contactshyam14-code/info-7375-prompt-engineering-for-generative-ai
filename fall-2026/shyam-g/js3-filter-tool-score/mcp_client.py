"""A minimal MCP client, written from scratch: spawn a stdio server, then initialize -> initialized ->
tools/list -> (optional) tools/call ... Every line in both directions is saved with a timestamp.

  python mcp_client.py <transcript-name> --calls calls.json -- <server command...>

calls.json is a list of {"name": ..., "arguments": {...}} (or a raw {"method": ..., "params": ...}).
Transcript: transcripts/<transcript-name>.jsonl
"""
from __future__ import annotations

import datetime
import json
import pathlib
import subprocess
import sys
import threading

ROOT = pathlib.Path(__file__).resolve().parent


def main(argv: list[str]) -> int:
    name = argv[0]
    calls = []
    if "--calls" in argv:
        calls = json.loads(pathlib.Path(argv[argv.index("--calls") + 1]).read_text(encoding="utf-8"))
    cmd = argv[argv.index("--") + 1:]
    out_path = ROOT / "transcripts" / f"{name}.jsonl"
    out_path.parent.mkdir(exist_ok=True)
    out = out_path.open("w", encoding="utf-8")

    def log(direction, raw):
        out.write(json.dumps({"t": datetime.datetime.now().astimezone().isoformat(timespec="milliseconds"),
                              "dir": direction, "raw": raw}, ensure_ascii=False) + "\n")
        out.flush()

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding="utf-8", shell=sys.platform == "win32" and cmd[0] != sys.executable)
    threading.Thread(target=lambda: [log("server-stderr", l.rstrip()) for l in proc.stderr], daemon=True).start()
    next_id = [0]

    def send(method, params=None, notify=False):
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notify:
            next_id[0] += 1
            msg["id"] = next_id[0]
        raw = json.dumps(msg, ensure_ascii=False)
        log("client->server", raw)
        proc.stdin.write(raw + "\n")
        proc.stdin.flush()
        if notify:
            return None
        while True:
            line = proc.stdout.readline()
            if not line:
                log("note", "server closed stdout")
                return None
            line = line.strip()
            if not line:
                continue
            log("server->client", line)
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            if m.get("id") == msg["id"]:
                return m
            # a server request or notification interleaved: logged above, not answered

    init = send("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                               "clientInfo": {"name": "js3-handwritten-client", "version": "0.1.0"}})
    print("initialize ->", json.dumps((init or {}).get("result", init))[:400])
    send("notifications/initialized", notify=True)
    tl = send("tools/list", {})
    tools = ((tl or {}).get("result") or {}).get("tools", [])
    print(f"tools/list -> {len(tools)} tools: {[t['name'] for t in tools]}")
    for c in calls:
        if "method" in c:
            r = send(c["method"], c.get("params"))
        else:
            r = send("tools/call", {"name": c["name"], "arguments": c.get("arguments", {})})
        print(f"{c.get('method', 'tools/call ' + c.get('name', ''))} ->", json.dumps(r)[:300])
    proc.stdin.close()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    out.close()
    print("transcript:", out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
