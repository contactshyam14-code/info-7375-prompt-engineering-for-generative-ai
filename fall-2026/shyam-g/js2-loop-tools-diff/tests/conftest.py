"""Test helpers only: fixtures, no assertions. Written by Claude Code on 2026-11-10.

The tests themselves (test_boundary.py, test_loop.py) are yours to write.
"""
import os
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from js2.policy import Policy  # noqa: E402
from js2.loop import Budget  # noqa: E402
from js2.providers import Permanent, Transient  # noqa: E402


@pytest.fixture
def project(tmp_path):
    """A throwaway project root containing jobs/ and a jobs-evil/ sibling."""
    (tmp_path / "jobs" / "state").mkdir(parents=True)
    (tmp_path / "jobs-evil").mkdir()
    (tmp_path / "config").mkdir()
    return tmp_path


@pytest.fixture
def policy(project):
    """The same shape as config/policy.json, rooted in the throwaway project."""
    return Policy(root=project,
                  allowed_hosts=["boards-api.greenhouse.io", "api.lever.co"],
                  allowed_methods=["GET"], write_root="jobs", read_root=".",
                  overwrite_without_approval=["state/*.json"],
                  allowed_actions=["fetch_board", "read_file", "write_output"],
                  forbidden_actions=["apply", "email", "message", "login", "submit_form", "post"])


@pytest.fixture
def make_symlink():
    """make_symlink(link, target). Skips the test if this OS/user cannot create symlinks."""
    def _make(link: pathlib.Path, target: pathlib.Path):
        try:
            os.symlink(target, link, target_is_directory=target.is_dir())
        except (OSError, NotImplementedError) as e:
            pytest.skip(f"cannot create symlinks here: {e}")
        return link
    return _make


@pytest.fixture
def budget():
    return Budget(max_boards=5, max_requests=8, max_seconds=60, max_retries_per_board=1,
                  retry_backoff_seconds=0, request_timeout_seconds=5)


@pytest.fixture
def fake_http():
    """fake_http({url_substring: response}) -> http_get. A response is bytes, or an exception
    instance/class to raise (Transient('timeout'), Permanent('HTTP 404')). Records calls."""
    def _make(responses: dict):
        calls = []

        def http_get(url, timeout):
            calls.append(url)
            for key, resp in responses.items():
                if key in url:
                    if isinstance(resp, BaseException) or (isinstance(resp, type) and issubclass(resp, BaseException)):
                        raise resp
                    return resp
            raise Permanent(f"fake_http: no response configured for {url}")
        http_get.calls = calls
        return http_get
    return _make


__all__ = ["Transient", "Permanent"]
