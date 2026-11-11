"""Applicant-tracking-system providers: URL builders, HTTP, and parsers.

Two systems: Greenhouse and Lever. Both are public, read-only, no login.
Parsers normalize postings to the Greenhouse shape the JS1 rule already reads:
  {"id", "title", "location": {"name"}, "content", "absolute_url"}
"""
from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "js2-job-agent (course project; read-only)"


class Transient(Exception):
    """Timeout, connection reset, 429 or 5xx. A retry may succeed."""


class Permanent(Exception):
    """404, other 4xx, empty body, bad JSON, wrong shape. A retry will not help."""


# ---------- URLs ----------

def greenhouse_url(token: str) -> str:
    return f"https://boards-api.greenhouse.io/v1/boards/{urllib.parse.quote(token)}/jobs?content=true"


def lever_url(token: str) -> str:
    return f"https://api.lever.co/v0/postings/{urllib.parse.quote(token)}?mode=json"


# ---------- parsers ----------

def _load(body: bytes):
    if body is None or not body.strip():
        raise Permanent("empty response body")
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise Permanent(f"response is not JSON: {e}")


def parse_greenhouse(body: bytes) -> list[dict]:
    data = _load(body)
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise Permanent("greenhouse response has no 'jobs' list")
    return [{"id": str(j["id"]), "title": j.get("title") or "",
             "location": {"name": (j.get("location") or {}).get("name") or ""},
             "content": j.get("content") or "", "absolute_url": j.get("absolute_url")}
            for j in data["jobs"]]


def parse_lever(body: bytes) -> list[dict]:
    data = _load(body)
    if not isinstance(data, list):
        raise Permanent("lever response is not a list of postings")
    out = []
    for p in data:
        cats = p.get("categories") or {}
        content = " ".join(filter(None, [p.get("descriptionPlain") or p.get("description") or ""]
                                  + [lst.get("content", "") for lst in p.get("lists") or []]))
        out.append({"id": str(p["id"]), "title": p.get("text") or "",
                    "location": {"name": cats.get("location") or ""},
                    "content": content, "absolute_url": p.get("hostedUrl")})
    return out


PROVIDERS = {
    "greenhouse": (greenhouse_url, parse_greenhouse),
    "lever": (lever_url, parse_lever),
}


# ---------- HTTP (no policy here: the loop checks the policy before calling this) ----------

class _RefuseRedirects(urllib.request.HTTPRedirectHandler):
    """The policy checks only the URL the loop asked for. Following a redirect would reach a
    URL nobody checked, so every redirect is refused as a permanent failure."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Permanent(f"HTTP {code} redirect to {newurl} refused: policy checked only {req.full_url}")


_OPENER = urllib.request.build_opener(_RefuseRedirects)


def http_get(url: str, timeout: float) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    try:
        with _OPENER.open(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 429 or e.code >= 500:
            raise Transient(f"HTTP {e.code}")
        raise Permanent(f"HTTP {e.code}")
    except (socket.timeout, TimeoutError) as e:
        raise Transient(f"timeout after {timeout:.0f}s: {e}")
    except urllib.error.URLError as e:
        if isinstance(e.reason, (socket.timeout, TimeoutError)):
            raise Transient(f"timeout after {timeout:.0f}s")
        raise Transient(f"connection error: {e.reason}")
