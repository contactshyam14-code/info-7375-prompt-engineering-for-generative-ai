"""Loop tests: one test per "wrong version" in GATE.md section 6 (commit 2f256e7).

AUTHORSHIP (disclosed in SOURCES.md): written by Claude Code on 2026-11-10 at the owner's
request. Each test asserts what GATE.md says the loop must do, including the status names
the owner chose (bad_name, ok_empty, failed). Where the code uses different behavior or names,
the test is red on purpose. Do not weaken it: fix the code, or amend GATE.md with a dated entry.
"""
import http.server
import threading

from js2.loop import Budget, run_loop
from js2.providers import Permanent, Transient, http_get

GH = b'{"jobs": [{"id": 1, "title": "Engineer", "location": {"name": "Boston"}, "content": ""}]}'
EMPTY_GH = b'{"jobs": []}'
NO_SLEEP = dict(sleep=lambda s: None)


def gh(name):
    return {"board": name, "ats": "greenhouse"}


# GATE 6.1: reports 0 jobs on a 404 -> must be status bad_name, not a zero count
def test_6_1_404_is_bad_name_not_zero(budget, policy, fake_http):
    out = run_loop([gh("nope")], budget, policy, fake_http({"/nope/": Permanent("HTTP 404")}), **NO_SLEEP)
    r = out["results"][0]
    assert r.count is None
    assert r.status == "bad_name"


# GATE 6.2: treats an empty list as an error and retries -> exactly 1 request, ok_empty
def test_6_2_empty_list_is_ok_empty_one_request(budget, policy, fake_http):
    http = fake_http({"/quiet/": EMPTY_GH})
    out = run_loop([gh("quiet")], budget, policy, http, **NO_SLEEP)
    assert len(http.calls) == 1
    assert out["results"][0].status == "ok_empty"


# GATE 6.3: wrong number of retries -> permanent 503 gives exactly 2 requests, then failed
def test_6_3_503_retried_once_then_failed(budget, policy, fake_http):
    http = fake_http({"/flaky/": Transient("HTTP 503")})
    out = run_loop([gh("flaky")], budget, policy, http, **NO_SLEEP)
    assert len(http.calls) == 2
    assert out["results"][0].count is None
    assert out["results"][0].status == "failed"


# GATE 6.4: ignores the board budget -> 8 boards stop at 5, budget_exhausted, 3 listed as untried
def test_6_4_board_budget(policy, fake_http):
    b = Budget(max_boards=5, max_requests=10, max_seconds=60, max_retries_per_board=1,
               retry_backoff_seconds=0, request_timeout_seconds=5)
    boards = [gh(f"b{i}") for i in range(8)]
    http = fake_http({f"/b{i}/": GH for i in range(8)})
    out = run_loop(boards, b, policy, http, **NO_SLEEP)
    assert out["exit_status"] == "budget_exhausted"
    assert len(http.calls) == 5
    untried = [r.board for r in out["results"] if r.status == "not-attempted"]
    assert untried == ["b5", "b6", "b7"]


# GATE 6.5: says "finished" when a budget tripped -> slow mock trips max_seconds
def test_6_5_time_budget_is_budget_exhausted(budget, policy):
    now = [0.0]

    def slow_http(url, timeout):
        now[0] += 40  # each request "takes" 40 s on a fake clock; budget is 60 s
        return GH
    out = run_loop([gh("a"), gh("b"), gh("c")], budget, policy, slow_http,
                   clock=lambda: now[0], **NO_SLEEP)
    assert out["exit_status"] == "budget_exhausted"


# GATE 6.6a: allows a POST -> policy denial
def test_6_6a_post_denied(policy):
    assert policy.check_request("https://api.lever.co/v0/postings/acme", method="POST").verdict == "deny"


# GATE 6.6b: allows an unlisted host -> policy denial
def test_6_6b_unlisted_host_denied(policy):
    assert policy.check_request("https://jobs.example.com/acme").verdict == "deny"


# GATE 6.6c: follows a redirect to an unlisted host -> must not reach the second host.
# Two local servers: A answers 302 -> B. B counts hits. B must get zero.
def test_6_6c_redirect_to_unlisted_host_not_followed():
    hits = {"b": 0}

    class B(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            hits["b"] += 1
            self.send_response(200); self.end_headers(); self.wfile.write(b'{"jobs": []}')

        def log_message(self, *a):
            pass

    srv_b = http.server.HTTPServer(("127.0.0.1", 0), B)

    class A(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(302)
            self.send_header("Location", f"http://127.0.0.1:{srv_b.server_port}/stolen")
            self.end_headers()

        def log_message(self, *a):
            pass

    srv_a = http.server.HTTPServer(("127.0.0.1", 0), A)
    for s in (srv_a, srv_b):
        threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        try:
            http_get(f"http://127.0.0.1:{srv_a.server_port}/jobs", timeout=5)
        except (Permanent, Transient):
            pass  # refusing the redirect with an error is acceptable
        assert hits["b"] == 0, "redirect was followed to a host the policy never checked"
    finally:
        srv_a.shutdown(); srv_b.shutdown()


# GATE 6.7: drops a failed board from the report -> all three boards appear with a status
def test_6_7_failed_board_still_reported(budget, policy, fake_http):
    http = fake_http({"/a/": GH, "/bad/": Permanent("HTTP 404"), "/c/": GH})
    out = run_loop([gh("a"), gh("bad"), gh("c")], budget, policy, http, **NO_SLEEP)
    assert [r.board for r in out["results"]] == ["a", "bad", "c"]
    assert all(r.status for r in out["results"])
