"""Permission-policy boundary tests: one test per row of BOUNDARY-TESTS.md.

AUTHORSHIP (disclosed in SOURCES.md): written by Claude Code on 2026-11-10 at the owner's
request, AFTER the owner committed the predictions (commit 92c6a6d, 14:50). Each test
asserts the owner's Predicted column exactly as written, and no assertion was changed to fit the
code. Where a test is red, the code and the prediction disagree. That is a finding to explain
in BOUNDARY-TESTS.md "Notes", not a test to weaken.
"""
import pytest

from js2.policy import PolicyViolation


# 1. host on allow-list: predicted allow
def test_01_allowed_host(policy):
    assert policy.check_request("https://boards-api.greenhouse.io/v1/boards/acme/jobs").verdict == "allow"


# 2. host off allow-list: predicted deny
def test_02_off_list_host(policy):
    assert policy.check_request("https://example.com/jobs").verdict == "deny"


# 3. lookalike host: predicted deny
def test_03_lookalike_host(policy):
    assert policy.check_request("https://boards-api.greenhouse.io.evil.com/x").verdict == "deny"


# 4. non-GET method: predicted deny
def test_04_post_denied(policy):
    assert policy.check_request("https://api.lever.co/v0/postings/acme", method="POST").verdict == "deny"


# 5. ".." escape: predicted deny
def test_05_dotdot_escape(policy):
    assert policy.check_write("jobs/../config/policy.json").verdict == "deny"


# 6. prefix trick: jobs-evil is a sibling of jobs: predicted deny
def test_06_prefix_trick_jobs_evil(policy):
    assert policy.check_write("jobs-evil/out.json").verdict == "deny"


# 7. symlink inside jobs/ pointing to a file outside the project: predicted deny
def test_07_symlink_escape(policy, project, make_symlink, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "target.json"
    outside.write_text("{}")
    make_symlink(project / "jobs" / "link.json", outside)
    assert policy.check_write("jobs/link.json").verdict == "deny"


# 8. read inside project: predicted allow
def test_08_read_inside_project(policy):
    assert policy.check_read("config/budgets.json").verdict == "allow"


# 9. read outside project: predicted deny
def test_09_read_outside_project(policy):
    assert policy.check_read("/etc/hosts").verdict == "deny"


# 10. same path, read vs write: predicted allow, then deny
def test_10_same_path_read_then_write(policy):
    assert policy.check_read("config/budgets.json").verdict == "allow"
    assert policy.check_write("config/budgets.json").verdict == "deny"


# 11. overwrite needing approval, not approved: predicted ask
def test_11_overwrite_not_approved(policy, project):
    target = project / "jobs" / "report.json"
    target.write_text("original")
    assert policy.check_write("jobs/report.json").verdict == "ask"
    with pytest.raises(PolicyViolation):
        policy.write_text("jobs/report.json", "new", approver=lambda d: False)
    assert target.read_text() == "original"


# 12. overwrite needing approval, approved: predicted allow
def test_12_overwrite_approved(policy, project):
    target = project / "jobs" / "report.json"
    target.write_text("original")
    d = policy.write_text("jobs/report.json", "new", approver=lambda d: True)
    assert d.verdict == "allow"
    assert target.read_text() == "new"


# 13. forbidden actions: predicted deny for email, apply, login
@pytest.mark.parametrize("action", ["email", "apply", "login"])
def test_13_forbidden_actions(policy, action):
    assert policy.check_action(action).verdict == "deny"


# 14. state/ ambiguity: overwrite existing state/seen.json -> predicted allow,
#     then write state/seen.txt -> predicted ask. Paths taken exactly as written in the table.
def test_14_state_ambiguity(policy, project):
    (project / "state").mkdir()
    (project / "state" / "seen.json").write_text("{}")
    assert policy.check_write("state/seen.json").verdict == "allow"
    assert policy.check_write("state/seen.txt").verdict == "ask"
