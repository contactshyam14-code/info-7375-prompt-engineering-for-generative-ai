"""Use Claude Code itself as a real MCP client of my server.

  python mcp/claude-client.py
Runs `claude -p` with ONLY my server configured (--strict-mcp-config), only my tool allowed, and
built-in tools off. The server's own transcript (transcripts/server-*.jsonl) records every message
Claude Code sent and every reply. Claude's final answer is saved to transcripts/claude-client-answer.json.
"""
import datetime, json, pathlib, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parent.parent
cfg = {"mcpServers": {"js3": {"command": sys.executable, "args": [str(ROOT / "mcp_server.py")]}}}
cfg_path = pathlib.Path(tempfile.gettempdir()) / "js3-mcp-config.json"
cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
prompt = ("Use the score_posting tool on posting_id 8249069 and on posting_id 8311099. For each, report the "
          "filter decision, the score, and the verdict exactly as the tool returned them, then say in one "
          "sentence what the tool cannot tell you about whether the job is worth applying to.")
cwd = pathlib.Path(tempfile.gettempdir()) / "js3-claude-cwd"; cwd.mkdir(exist_ok=True)
cmd = ["claude", "-p", "--output-format", "json", "--mcp-config", str(cfg_path), "--strict-mcp-config",
       "--tools", "", "--allowedTools", "mcp__js3__score_posting"]
asked = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                   shell=sys.platform == "win32", cwd=str(cwd), timeout=600)
out = {"asked_at": asked, "command": cmd, "prompt": prompt, "returncode": r.returncode,
       "stdout": r.stdout, "stderr": r.stderr[-2000:]}
(ROOT / "transcripts" / "claude-client-answer.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
try:
    print(json.loads(r.stdout).get("result"))
except Exception:
    print(r.stdout[:2000], r.stderr[:2000])
