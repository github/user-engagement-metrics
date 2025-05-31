"""
Test suite for the GitHub User Engagement Metrics module.

This module contains unit tests for all the functions in the user_engagement_metrics.py
module, including API interactions, file operations, and data processing logic.
"""

import json
import time
from unittest.mock import MagicMock

import pytest
import user_engagement_metrics


@pytest.fixture(autouse=True)
def patch_globals(tmp_path, monkeypatch):
    """
    Fixture to patch global file paths to use temporary test directories.

    This automatically runs for all tests, ensuring that tests don't use
    or modify the real data files.

    Args:
        tmp_path: pytest fixture providing a temporary directory
        monkeypatch: pytest fixture for modifying objects
    """
    # Patch file paths to use test dir
    monkeypatch.setattr(
        user_engagement_metrics, "USERNAMES_FILE", str(tmp_path / "usernames.txt")
    )
    monkeypatch.setattr(
        user_engagement_metrics, "OUTPUT_FILE", str(tmp_path / "user_results.jsonl")
    )
    monkeypatch.setattr(
        user_engagement_metrics,
        "CHECKPOINT_FILE",
        str(tmp_path / "completed_usernames.txt"),
    )
    yield


def test_safe_get_rate_limit(monkeypatch):
    """
    Test that safe_get handles GitHub API rate limits correctly.

    This test verifies that when a rate limit response is received,
    the function waits and retries the request.
    """
    m_resp = MagicMock()
    m_resp.status_code = 403
    m_resp.headers = {
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": str(int(time.time()) + 1),
    }
    m_resp.json.return_value = {}

    call_count = {"count": 0}

    def fake_requests_get(*_a, **_kw):
        """Fake requests.get to simulate rate limiting."""
        call_count["count"] += 1
        # simulate second call as success
        if call_count["count"] > 1:
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {"ok": True}
            resp.headers = {}
            return resp
        return m_resp

    monkeypatch.setattr(user_engagement_metrics.requests, "get", fake_requests_get)
    resp = user_engagement_metrics.safe_get("url")
    assert resp.json() == {"ok": True}
    assert call_count["count"] == 2


def test_get_user_profile(monkeypatch):
    """
    Test that get_user_profile correctly calls the GitHub API and processes the result.
    """
    monkeypatch.setattr(
        user_engagement_metrics,
        "safe_get",
        lambda url: MagicMock(json=lambda: {"login": "foo"}),
    )
    assert user_engagement_metrics.get_user_profile("foo") == {"login": "foo"}


def test_get_user_repos(monkeypatch):
    """
    Test that get_user_repos correctly handles API pagination.
    """
    # Simulate 2 pages, then empty
    responses = [[{"id": 1}, {"id": 2}]]

    def safe_get(_url, _params=None):
        return MagicMock(json=lambda: responses.pop(0))

    monkeypatch.setattr(user_engagement_metrics, "safe_get", safe_get)
    repos = user_engagement_metrics.get_user_repos("foo")
    assert repos == [{"id": 1}, {"id": 2}]


def test_get_starred_repos_count_no_link(monkeypatch):
    """
    Test that get_starred_repos_count works correctly when no pagination Link header is present.
    """
    m_resp = MagicMock()
    m_resp.headers = {}
    m_resp.json.return_value = [1, 2, 3]
    monkeypatch.setattr(user_engagement_metrics, "safe_get", lambda *a, **k: m_resp)
    assert user_engagement_metrics.get_starred_repos_count("foo") == 3


def test_get_starred_repos_count_with_link(monkeypatch):
    """
    Test that get_starred_repos_count correctly parses the Link header for total count.
    """
    m_resp = MagicMock()
    m_resp.headers = {
        "Link": '<https://api.github.com/user/123/starred?page=42>; rel="last"'
    }
    m_resp.json.return_value = [1]
    monkeypatch.setattr(user_engagement_metrics, "safe_get", lambda *a, **k: m_resp)
    assert user_engagement_metrics.get_starred_repos_count("foo") == 42


def test_get_orgs(monkeypatch):
    """
    Test that get_orgs correctly processes the API response.
    """
    monkeypatch.setattr(
        user_engagement_metrics,
        "safe_get",
        lambda url: MagicMock(json=lambda: [{"login": "acme"}]),
    )
    assert user_engagement_metrics.get_orgs("foo") == [{"login": "acme"}]


def test_search_user_contributions_commit(monkeypatch):
    """
    Test that search_user_contributions correctly handles commit searches.
    """
    m_resp = MagicMock()
    m_resp.json.return_value = {"total_count": 123}
    monkeypatch.setattr(
        user_engagement_metrics,
        "safe_get",
        lambda url, params=None, extra_headers=None: m_resp,
    )
    assert user_engagement_metrics.search_user_contributions("foo", "commit") == 123


def test_search_user_contributions_issue(monkeypatch):
    """
    Test that search_user_contributions correctly handles issue searches.
    """
    m_resp = MagicMock()
    m_resp.json.return_value = {"total_count": 99}
    monkeypatch.setattr(
        user_engagement_metrics,
        "safe_get",
        lambda url, params=None, extra_headers=None: m_resp,
    )
    assert user_engagement_metrics.search_user_contributions("foo", "issue") == 99


def test_load_completed_usernames(tmp_path, monkeypatch):
    """
    Test that load_completed_usernames correctly reads and processes the checkpoint file.
    """
    file_path = tmp_path / "completed_usernames.txt"
    file_path.write_text("a\nb\n\nc\n")
    monkeypatch.setattr(user_engagement_metrics, "CHECKPOINT_FILE", str(file_path))
    assert user_engagement_metrics.load_completed_usernames() == {"a", "b", "c"}


def test_append_completed_username(tmp_path, monkeypatch):
    """
    Test that append_completed_username correctly writes to the checkpoint file.
    """
    file_path = tmp_path / "completed_usernames.txt"
    monkeypatch.setattr(user_engagement_metrics, "CHECKPOINT_FILE", str(file_path))
    user_engagement_metrics.append_completed_username("dude")
    assert file_path.read_text().strip() == "dude"


def test_append_result(tmp_path, monkeypatch):
    """
    Test that append_result correctly writes results to the output file.
    """
    file_path = tmp_path / "user_results.jsonl"
    monkeypatch.setattr(user_engagement_metrics, "OUTPUT_FILE", str(file_path))
    user_engagement_metrics.append_result({"foo": "bar"})
    assert json.loads(file_path.read_text()) == {"foo": "bar"}
