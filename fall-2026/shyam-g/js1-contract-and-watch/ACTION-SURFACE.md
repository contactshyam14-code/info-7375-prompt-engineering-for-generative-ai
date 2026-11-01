# Action-surface comparison (Chapter 3)

Task: judge posting 8311099 (Formlabs, Strategy & Operations Analyst, Somerville, MA) against the
fictional persona under `prompts/baseline.txt`. Ways 1 and 2 were run on 2026-10-31; the output is in
`surface/runs.txt`. Both returned `relevant`, which matches the rule's record. Way 3 is written up from
its design and was **not** run as a free agent (see the last section).

| | 1. Paste into chat | 2. Give Claude a file to read | 3. Let an agent fetch and write its own state |
|---|---|---|---|
| How it ran | `claude -p --tools ""` with the posting in the prompt (`surface/1-paste-prompt.txt`) | `claude -p --tools Read --allowedTools Read`; the prompt names `surface/posting-8311099.json` | Claude with web fetch + file write tools, told to fetch the board, diff against `seen_ids.json`, and update it |
| Can read | only the prompt text I chose | the prompt, **plus any file the Read tool can open**, not just the one named | the network, the whole working tree, anything its tools reach |
| Can write | nothing | nothing | the state file, plus any other file its write tool can reach |
| Can send | nothing beyond its reply | nothing beyond its reply | HTTP requests to any host, unless a hook or permission rule blocks them |
| Authority needed | none: I chose every byte it sees | file-system read permission on my machine | network access + write access + trust that it does not touch other files |
| What could go wrong | I paste the wrong posting or a real résumé; the answer is unvalidated prose unless I run the validator | reads a file I did not intend (e.g. a real résumé on the same disk); the path is wrong and it judges something else | fetches a host outside the allow-list; rewrites or wipes `seen_ids.json`, so old postings come back as "new" or new ones are silently marked seen; nobody can recompute what happened; prompt injection in a posting body steers a tool call |

## Choice: the least autonomy that suffices

The **fetching and the state are plain code** (`agent.py`): an allow-listed `https` fetch, a raw
response saved as evidence, and a set difference on ids. None of that needs judgment, so none of it is
given to the model. **Claude gets surface 1 only**: one posting's text, the four rule-relevant résumé
fields (no name, email or phone; pinned by `test_prompt_never_contains_contact_details`), no tools,
and an output the validator either accepts or rejects.

Why not 2: reading a file adds no information the prompt doesn't already carry. It does add authority:
the Read tool is not scoped to the one file, and the real résumé lives on the same machine.

Why not 3: every part an agent would do with tools is deterministic and testable in code. Handing it
over trades a recomputable record for an unrecomputable one. It also puts the one thing the agent must
never get wrong, the seen-ids state, in the hands of the step whose output varies from run to run
(see `SAMPLING.md`).

## Not run
Way 3 was not executed as a free-running Claude agent. Giving it network and write access to show what
goes wrong is the risk the table describes. The comparison for Way 3 rests on its design, not on an
observed run.
