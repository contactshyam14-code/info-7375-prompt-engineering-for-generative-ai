"""The permission policy, enforced in code (Chapter 5).

Every fetch, read and write the agent makes goes through a Policy object. The policy is data
(config/policy.json); this module is the only place that decides. Nothing here asks a model.

Each check returns a Decision: verdict is "allow", "deny" or "ask" (needs the owner's approval).
"""
from __future__ import annotations

import fnmatch
import json
import pathlib
import urllib.parse
from typing import Callable, NamedTuple


class Decision(NamedTuple):
    verdict: str  # "allow" | "deny" | "ask"
    reason: str

    @property
    def allowed(self) -> bool:
        return self.verdict == "allow"


class PolicyViolation(PermissionError):
    """Raised when code tries to act without an "allow" decision."""


ALLOW, DENY, ASK = "allow", "deny", "ask"


class Policy:
    def __init__(self, root: pathlib.Path, allowed_hosts, allowed_methods, write_root: str,
                 read_root: str = ".", overwrite_without_approval=(), allowed_actions=(),
                 forbidden_actions=()):
        self.root = pathlib.Path(root).resolve()
        self.allowed_hosts = {h.strip().lower() for h in allowed_hosts}
        self.allowed_methods = {m.upper() for m in allowed_methods}
        self.write_root = (self.root / write_root).resolve()
        self.read_root = (self.root / read_root).resolve()
        self.overwrite_without_approval = list(overwrite_without_approval)
        self.allowed_actions = set(allowed_actions)
        self.forbidden_actions = set(forbidden_actions)

    @classmethod
    def from_file(cls, path: pathlib.Path, root: pathlib.Path) -> "Policy":
        cfg = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        return cls(root=root, allowed_hosts=cfg["allowed_hosts"],
                   allowed_methods=cfg["allowed_methods"], write_root=cfg["write_root"],
                   read_root=cfg.get("read_root", "."),
                   overwrite_without_approval=cfg.get("overwrite_without_approval", []),
                   allowed_actions=cfg.get("allowed_actions", []),
                   forbidden_actions=cfg.get("forbidden_actions", []))

    # ---------- actions ----------

    def check_action(self, name: str) -> Decision:
        """Named capabilities. Anything not explicitly allowed is denied."""
        if name in self.forbidden_actions:
            return Decision(DENY, f"action {name!r} is forbidden by policy")
        if name not in self.allowed_actions:
            return Decision(DENY, f"action {name!r} is not on the allowed-actions list")
        return Decision(ALLOW, f"action {name!r} allowed")

    # ---------- network ----------

    def check_request(self, url: str, method: str = "GET") -> Decision:
        method = (method or "").upper()
        if method not in self.allowed_methods:
            return Decision(DENY, f"method {method} not allowed (read-only agent)")
        try:
            parts = urllib.parse.urlsplit(url)
            port = parts.port
        except ValueError as e:
            return Decision(DENY, f"unparseable URL: {e}")
        if parts.scheme != "https":
            return Decision(DENY, f"scheme {parts.scheme!r} is not https")
        if "@" in parts.netloc:
            return Decision(DENY, "credentials or '@' in the URL authority")
        if port not in (None, 443):
            return Decision(DENY, f"port {port} not allowed")
        host = (parts.hostname or "").lower()
        if host not in self.allowed_hosts:  # exact match: no suffix or prefix matching
            return Decision(DENY, f"host {host!r} is not on the allow-list")
        return Decision(ALLOW, f"{method} {host} allowed")

    # ---------- files ----------

    def _resolve(self, path) -> pathlib.Path:
        p = pathlib.Path(path)
        if not p.is_absolute():
            p = self.root / p
        # resolve() collapses ".." and follows any symlinks that already exist on disk
        return p.resolve()

    def check_read(self, path) -> Decision:
        target = self._resolve(path)
        if not target.is_relative_to(self.read_root):
            return Decision(DENY, f"read of {target} is outside {self.read_root}")
        return Decision(ALLOW, f"read {target.relative_to(self.root).as_posix()} allowed")

    def check_write(self, path) -> Decision:
        target = self._resolve(path)
        # is_relative_to compares path components, so "jobs-evil" is NOT inside "jobs"
        if not target.is_relative_to(self.write_root) or target == self.write_root:
            return Decision(DENY, f"write to {target} is outside {self.write_root}")
        rel = target.relative_to(self.write_root).as_posix()
        if target.exists():
            if target.is_dir():
                return Decision(DENY, f"{rel} is a directory")
            if any(fnmatch.fnmatch(rel, pat) for pat in self.overwrite_without_approval):
                return Decision(ALLOW, f"overwrite of {rel} allowed without approval by policy")
            return Decision(ASK, f"overwrite of existing {rel} needs the owner's approval")
        return Decision(ALLOW, f"new file {rel} allowed")

    # ---------- enforcing helpers (the only way the agent touches disk) ----------

    def write_bytes(self, path, data: bytes,
                    approver: Callable[[Decision], bool] | None = None) -> Decision:
        d = self.check_write(path)
        if d.verdict == ASK:
            if approver is not None and approver(d):
                d = Decision(ALLOW, d.reason + " -> approved")
            else:
                d = Decision(DENY, d.reason + " -> not approved")
        if not d.allowed:
            raise PolicyViolation(d.reason)
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        # re-check after mkdir: a symlinked parent created in between must not slip through
        if not self._resolve(path).is_relative_to(self.write_root):
            raise PolicyViolation(f"write to {target} escaped {self.write_root} after mkdir")
        target.write_bytes(data)
        return d

    def write_text(self, path, text: str, approver=None) -> Decision:
        return self.write_bytes(path, text.encode("utf-8"), approver)

    def read_bytes(self, path) -> bytes:
        d = self.check_read(path)
        if not d.allowed:
            raise PolicyViolation(d.reason)
        return self._resolve(path).read_bytes()
