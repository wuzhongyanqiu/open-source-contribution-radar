import json
import unittest
from unittest.mock import patch

from open_source_radar.github import GithubClient, GithubError


class GithubClientTest(unittest.TestCase):
    def test_github_templates_do_not_claim_contributing_or_ci(self) -> None:
        candidate = GithubClient._repository({"full_name": "example/project", "html_url": "https://github.com/example/project"})
        client = GithubClient()
        client.request = lambda endpoint: ([{"name": ".github", "type": "dir"}] if endpoint.endswith("/contents") else [{"name": "ISSUE_TEMPLATE", "type": "dir"}])
        client.enrich(candidate)
        self.assertFalse(candidate.has_ci)
        self.assertFalse(candidate.has_contributing)

    def test_actual_workflow_and_contributing_files_are_detected(self) -> None:
        candidate = GithubClient._repository({"full_name": "example/project", "html_url": "https://github.com/example/project"})
        client = GithubClient()
        def request(endpoint):
            if endpoint.endswith("/contents"):
                return [{"name": ".github", "type": "dir"}]
            if endpoint.endswith("/.github"):
                return [{"name": "CONTRIBUTING.md", "type": "file"}, {"name": "workflows", "type": "dir"}]
            return [{"name": "tests.yml", "type": "file"}]
        client.request = request
        client.enrich(candidate)
        self.assertTrue(candidate.has_ci)
        self.assertTrue(candidate.has_contributing)

    def test_incomplete_search_is_not_an_empty_success(self) -> None:
        client = GithubClient()
        client.request = lambda *args, **kwargs: {"incomplete_results": True, "items": []}
        for method in [client.search_repositories, client.search_issues]:
            with self.assertRaisesRegex(GithubError, "incomplete"):
                method("test", 5)

    @patch("open_source_radar.github.subprocess.run")
    def test_request_uses_get_and_parses_json(self, run) -> None:
        run.return_value.returncode = 0
        run.return_value.stdout = json.dumps({"ok": True})
        run.return_value.stderr = ""
        result = GithubClient(search_interval_seconds=0).request("search/repositories", {"q": "topic:agent"})
        self.assertEqual(result, {"ok": True})
        command = run.call_args.args[0]
        self.assertEqual(command[:4], ["gh", "api", "--method", "GET"])
        self.assertIn("q=topic:agent", command)

    @patch("open_source_radar.github.subprocess.run")
    def test_request_redacts_nothing_because_no_token_is_passed(self, run) -> None:
        run.return_value.returncode = 1
        run.return_value.stdout = ""
        run.return_value.stderr = "rate limit"
        with self.assertRaisesRegex(GithubError, "rate limit"):
            GithubClient(search_interval_seconds=0).request("search/repositories")
        self.assertNotIn("token", " ".join(run.call_args.args[0]).lower())

    def test_account_audit_uses_authenticated_endpoint_for_self(self) -> None:
        client = GithubClient()
        calls = []

        def request(endpoint, fields=None):
            calls.append((endpoint, fields))
            if endpoint == "user":
                return {"login": "owner"}
            return []

        client.request = request
        self.assertEqual(client.list_account_repositories("owner"), [])
        self.assertEqual(calls[1][0], "user/repos")
        self.assertEqual(calls[1][1]["affiliation"], "owner")

    def test_global_issue_search_extracts_repository(self) -> None:
        client = GithubClient()
        client.request = lambda endpoint, fields=None: {"items": [{
            "number": 7,
            "title": "Fix parser",
            "html_url": "https://github.com/example/project/issues/7",
            "repository_url": "https://api.github.com/repos/example/project",
            "labels": [{"name": "good first issue"}],
            "created_at": "2026-10-01T00:00:00Z",
            "updated_at": "2026-10-02T00:00:00Z",
        }]}
        results = client.search_issues("agent is:issue", 5)
        self.assertEqual(results[0][0], "example/project")
        self.assertEqual(results[0][1].number, 7)


if __name__ == "__main__":
    unittest.main()
