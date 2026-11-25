# My agent as a tool (Chapter 8): the server, its transcripts, and two evaluations

## 1. What I built
`mcp_server.py` is a Model Context Protocol server written from scratch: Python standard library
only, stdio, JSON-RPC 2.0, one message per line. It handles `initialize`, `notifications/initialized`,
`ping`, `tools/list`, and `tools/call`. It offers **one** tool, `score_posting`, which runs the
FILTER.md filter on one posting (by id from the local corpus, or caller-supplied text) and returns
the decision, score, matched words, the three gate-claim labels, and the abstention verdict.
`mcp_client.py` is a client written from scratch that spawns any stdio server and saves every line,
in both directions, with a timestamp.

## 2. Transcripts (real, 2026-11-23, both directions, unedited)

| File | Client | Server | What happened |
|---|---|---|---|
| `transcripts/own-server-handwritten-client.jsonl` | my `mcp_client.py` | mine | initialize → initialized → tools/list → 7 calls: 2 good calls, a path-traversal id, an extra `write_to` argument, an unknown tool `apply_to_job`, `resources/list`, `ping` |
| `transcripts/own-server-handwritten-client.server-side.jsonl` | (same session) | mine | the server's own log of the same session, as a cross-check that both sides saw the same lines |
| `transcripts/own-server-claude-code-client.jsonl` | **Claude Code 2.1.316** (`claude -p`, only my server, only my tool allowed) | mine | server-side log: Claude Code's discovery probe, initialize, tools/list, two `tools/call` |
| `transcripts/claude-client-answer.json` | (same session) | — | Claude's final answer, prompt, command, timestamp 2026-11-23T13:54 ET |
| `transcripts/e5-tools-condition/*.jsonl` | Claude Code, 10 sessions of experiment E5 | mine | Claude called the tool in **2 of 10** sessions (8311099, 8335610) |
| `transcripts/other-claude-mcp-serve-list.jsonl` | my client | `claude mcp serve` (Claude Code 2.1.316) | initialize + tools/list (32 tools) |
| `transcripts/other-claude-mcp-serve-calls.jsonl` | my client | `claude mcp serve` | Read inside my folder, Read of `C:/Windows/win.ini`, Glob, an unknown tool |

What the Claude Code transcript showed that I didn't expect:
- **The first message was not `initialize`.** Claude Code sent `server/discover` with a `_meta` protocol
  version of `2026-07-28`. My server answered `-32601 Method not found`, and Claude Code fell back to `initialize`.
- Claude Code asked for protocol version `2025-11-25`. My server doesn't list that version, so it answered
  with its own `2025-06-18`. Claude Code accepted the downgrade and carried on.
- Claude Code declared client capabilities (`roots`, `elicitation`) that my server never uses.
- Each `tools/call` carried `_meta` with a `claudecode/toolUseId` and a `progressToken`. My server ignores both.

## 3. Evaluation of my own server, as if someone else wrote it

**Declared vs. actual**

| It declares | What it actually does | Checked by |
|---|---|---|
| one tool, `score_posting` | one tool. `apply_to_job` → `-32602 Unknown tool` | transcript id 7; `test_errors` |
| `readOnlyHint: true`, `destructiveHint: false`, `openWorldHint: false` | It reads FILTER.md and `data/corpus.jsonl`. It **writes**: every session appends a transcript file to `transcripts/`. The description says so, but the read-only annotation is only true about postings and the filter, not about the disk | source review; `test_server_has_no_network_or_write_capability_in_source` |
| "No network access" | no network module is imported (static check). I did **not** watch its traffic at runtime | `test_server_has_no_network...` (static only) |
| input schema with `additionalProperties: false` | enforced in code: `write_to` → `isError: true` | transcript id 6; `test_errors` |
| a `posting_id` refers to the local corpus | an id is only a dictionary key, so `../../persona/jordan_rivera.json` is just "no posting", never a file path | transcript id 5; `test_errors` |
| "scores; does not decide what is worth applying to" | true in what it returns (the caveat field). But in E5, Claude called the tool on 8335610, got `keep`, and still answered `not_relevant`. A client can ignore the caveat in either direction | `reports/claude/experiments/E5_tools_score_posting/8335610.json` |
| protocol version negotiation | it answers with the client's version if it supports it, otherwise `2025-06-18`. It never checks that the client then accepts | Claude Code transcript; `test_unknown_version_gets_servers_version` |

Gaps a reviewer would flag: no batching (refused with `-32600`); no `resources` or `prompts`; no
cancellation or progress; one process per session, so the corpus loads each time. The filter
file is re-read on every call, which means **a change to FILTER.md changes the tool's answers
between sessions with no code change and nothing "trained"** (see SCORE-REPORT.md section 4).

**What a compatible client is not entitled to**
- To assume the annotations are true. `readOnlyHint` is a hint the server writes about itself. Mine
  is only partly true (it writes transcripts), and nothing in the protocol verifies it.
- To treat the score as a fact about the job. It's a keyword filter's opinion with documented
  false friends (FALSE-FRIENDS.md).
- To anything beyond the declared tool: no files, no listing of the corpus, no FILTER.md edits.
- To fresh data. The corpus is a snapshot from 2026-11-10, and the server can't tell whether a posting is still open.
- To any persona other than the fictional one. The server never sees a real résumé.

**My trust decision about my own server:** I trust it to run locally under Claude Code with only
`mcp__js3__score_posting` allowed, because the source is short enough that I read every line, and
the tests check the error paths and the absence of network or subprocess imports. I do **not**
trust its output for decisions (see the driver's seat in SIGNOFF.md). I haven't checked it on
untrusted input at scale (fuzzing), or its behavior under a malicious client that sends huge lines.

## 4. Evaluation of another server: `claude mcp serve` (Anthropic, Claude Code 2.1.316)
Source: the `claude` CLI already installed on this machine (`claude mcp serve` makes Claude Code
act as an MCP server). I did not download anything new for this. I evaluated it only through its
protocol behavior, not its source code, which I didn't read.

**Declared vs. actual**

| It declares | What it actually does | Evidence |
|---|---|---|
| `serverInfo: claude/tengu 2.1.316`, `tools.listChanged: true`, no `instructions` | 32 tools, including `Bash`, `PowerShell`, `Write`, `Edit`, `WebFetch`, `WebSearch`, `RemoteTrigger`, `PushNotification`, `PublishPlugin`, `CronCreate` | `other-claude-mcp-serve-list.jsonl` |
| **no annotations on any tool** (all `null`) | so even `Read` and `Glob` are not marked read-only, and `Bash` is not marked destructive. The client gets no hints at all | same |
| `Read`: "You can access any file directly" | true: it read `C:/Windows/win.ini`, outside the folder I started it in, **with no permission prompt**. The prompts the interactive CLI shows are not part of the MCP surface | `other-claude-mcp-serve-calls.jsonl` id 4 |
| `Glob` with pattern `*.md` | matched in subfolders too (`reports\AUDIT.md`), which is wider than the pattern suggests | same, id 5 |
| tool descriptions | written for Claude Code's own agent loop ("This tool runs Git Bash…", references to other Claude Code tools). Outside that loop, a different client gets instructions meant for another host | tools/list |
| unknown tool | `-32603` (internal error), where my server uses `-32602` (invalid params) | same, id 6 |

**What a compatible client is not entitled to:** to assume any tool is sandboxed to a folder; to
assume a tool without annotations is safe; to the interactive permission prompts (they don't
exist over this channel); to stable tool lists (`listChanged: true`).

**My trust decision:** I would **not** connect `claude mcp serve` to my job-search agent or to any
model acting on posting text. Posting text is untrusted input. A prompt injection in a posting
could reach `Bash`, `Write`, or `WebFetch` through this server with nothing to stop it. I'd only
use it with a client that enforces its own allow-list down to `Read`/`Glob`/`Grep`, and only in a
throwaway folder. I called only `Read` and `Glob` on it, and never `Bash`, `Write`, or any network
tool. That limit was my decision, not something the server enforced.

## 5. What I didn't check
- A runtime network capture of either server (my "no network" claim for my server is a static check).
- `claude mcp serve`'s source code, and whether it applies any permission settings from my user config.
- How my server behaves under concurrent clients, with very large lines, or with a client that never sends `initialized`.
