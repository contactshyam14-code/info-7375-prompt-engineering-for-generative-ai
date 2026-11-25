"""One fresh, tool-less Claude conversation via the Claude Code CLI (`claude -p`), as in JS1.

It runs from an empty temp folder outside any git repo, not the project folder: run inside the project,
`claude -p` sees the git status and answers about the repo (observed 2026-11-23, see FRICTIONAL.md).
That is extra context, and Chapter 9 treats context as one of the things that changes behavior.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
NEUTRAL_CWD = pathlib.Path(tempfile.gettempdir()) / "js3-claude-cwd"   # outside any git repo


def ask_claude(prompt: str, extra_args: list[str] | None = None, cwd: pathlib.Path | None = None,
               timeout: int = 300) -> str:
    NEUTRAL_CWD.mkdir(exist_ok=True)
    cmd = ["claude", "-p", "--output-format", "text"] + (extra_args if extra_args is not None else ["--tools", ""])
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                       shell=sys.platform == "win32", timeout=timeout, cwd=str(cwd or NEUTRAL_CWD))
    if r.returncode != 0:
        raise RuntimeError(f"claude exited {r.returncode}: {r.stderr.strip()[:300]}")
    return r.stdout.strip()
