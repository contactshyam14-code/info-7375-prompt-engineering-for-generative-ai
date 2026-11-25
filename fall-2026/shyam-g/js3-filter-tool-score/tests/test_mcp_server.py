"""Protocol tests for mcp_server.py, run as a real subprocess over stdio."""
import json
import pathlib
import os
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent


def session(messages):
    lines = [m if isinstance(m, str) else json.dumps(m) for m in messages]
    p = subprocess.run([sys.executable, str(ROOT / "mcp_server.py")], input="\n".join(lines) + "\n",
                       capture_output=True, text=True, encoding="utf-8", timeout=60,
                       env=dict(os.environ, JS3_TRANSCRIPT_DIR=tempfile.mkdtemp(prefix="js3-test-")))
    return [json.loads(line) for line in p.stdout.splitlines() if line.strip()]


INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                   "clientInfo": {"name": "t", "version": "0"}}}


def test_initialize_list_call():
    out = session([INIT, {"jsonrpc": "2.0", "method": "notifications/initialized"},
                   {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                   {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                    "params": {"name": "score_posting", "arguments": {"posting_id": "8311099"}}}])
    assert [m["id"] for m in out] == [1, 2, 3]           # the notification gets no reply
    assert out[0]["result"]["protocolVersion"] == "2025-06-18"
    assert [t["name"] for t in out[1]["result"]["tools"]] == ["score_posting"]
    res = out[2]["result"]
    assert res["isError"] is False and res["structuredContent"]["posting_id"] == "8311099"


def test_unknown_version_gets_servers_version():
    m = dict(INIT, params=dict(INIT["params"], protocolVersion="1999-01-01"))
    assert session([m])[0]["result"]["protocolVersion"] == "2025-06-18"


def test_errors():
    out = session([
        INIT, "{not json",
        {"jsonrpc": "2.0", "id": 5, "method": "resources/list"},
        {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "apply_to_job", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 7, "method": "tools/call",
         "params": {"name": "score_posting", "arguments": {"posting_id": "../../persona/jordan_rivera.json"}}},
        {"jsonrpc": "2.0", "id": 8, "method": "tools/call",
         "params": {"name": "score_posting", "arguments": {"posting_id": "8311099", "write_to": "C:/x"}}}])
    by = {m.get("id"): m for m in out}
    assert by[None]["error"]["code"] == -32700
    assert by[5]["error"]["code"] == -32601
    assert by[6]["error"]["code"] == -32602
    assert by[7]["result"]["isError"] is True and "never fetches" in by[7]["result"]["content"][0]["text"]
    assert by[8]["result"]["isError"] is True


def test_server_has_no_network_or_write_capability_in_source():
    src = (ROOT / "mcp_server.py").read_text(encoding="utf-8")
    for bad in ("import socket", "urllib", "http.client", "requests", "subprocess", "os.remove", "shutil"):
        assert bad not in src
    # the only file opened for writing is the transcript under transcripts/
    assert src.count('open("a"') == 1 and 'ROOT / "transcripts"' in src
