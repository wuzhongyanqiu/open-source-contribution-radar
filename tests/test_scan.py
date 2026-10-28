import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock

from open_source_radar.cli import _scan
from open_source_radar.config import load_config
from open_source_radar.github import GithubError


class ScanEvidenceTest(unittest.TestCase):
    def test_api_failure_preserves_baseline_and_retains_each_attempt(self):
        config = load_config(Path(__file__).parents[1] / "radar.json")
        client = Mock()
        client.search_repositories.side_effect = GithubError("rate limit")
        client.search_issues.return_value = []
        with TemporaryDirectory() as tmp:
            state = Path(tmp)
            original = '{"repositories":{"owner/repo":{"stars":100}}}'
            (state / "state.json").write_text(original)
            for _ in range(2):
                self.assertEqual(_scan(config, state, client), 1)
            self.assertEqual((state / "state.json").read_text(), original)
            attempts = list((state / "runs").glob("*.json"))
            self.assertEqual(len(attempts), 2)
            report = json.loads(attempts[0].read_text())
            self.assertEqual(report["status"], "FAILED")
            self.assertEqual(report["eligible_count"], 0)
            self.assertEqual(len(report["errors"]), len(config.queries))

    def test_successful_empty_search_is_not_a_network_failure(self):
        config = load_config(Path(__file__).parents[1] / "radar.json")
        client = Mock()
        client.search_repositories.return_value = []
        client.search_issues.return_value = []
        with TemporaryDirectory() as tmp:
            self.assertEqual(_scan(config, Path(tmp), client), 0)
            report = json.loads(next((Path(tmp) / "runs").glob("*.json")).read_text())
            self.assertEqual(report["status"], "NO_CANDIDATES")
            self.assertEqual(report["errors"], [])

    def test_issue_discovery_cannot_bypass_repository_exclusions(self):
        from open_source_radar.models import RepositoryCandidate, IssueCandidate
        config = load_config(Path(__file__).parents[1] / 'radar.json')
        issue = IssueCandidate(1, 'Fix bug', 'https://github.com/example/project/issues/1', [], '', '')
        client = Mock()
        client.search_repositories.return_value = []
        client.search_issues.return_value = [('wuzhongyanqiu/self', issue), ('example/archived', issue), ('example/fork', issue)]
        def repository(full_name):
            return RepositoryCandidate(full_name, 'https://github.com/' + full_name, '', '', [], 1000, 0, 1, '', '', 'MIT', full_name.endswith('archived'), full_name.endswith('fork'))
        client.get_repository.side_effect = repository
        with TemporaryDirectory() as tmp:
            self.assertEqual(_scan(config, Path(tmp), client), 0)
            result = json.loads(next((Path(tmp) / 'runs').glob('*.json')).read_text())
            self.assertEqual(result['candidates'], [])
        self.assertEqual(client.get_repository.call_count, 2)
        client.enrich.assert_not_called()

    def test_partial_scan_marks_high_score_candidates_blocked_in_markdown(self):
        from open_source_radar.models import RepositoryCandidate, IssueCandidate
        from open_source_radar.report import write_discovery_report
        from datetime import datetime, timezone
        candidate = RepositoryCandidate('example/agent', 'https://github.com/example/agent', '', 'Python', [], 1000, 0, 1,
            datetime.now(timezone.utc).isoformat(), '', 'MIT', False, False,
            issues=[IssueCandidate(1, 'Fix', '', [], '', '')], project_score=100, contribution_score=100)
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'partial.md'
            write_discovery_report(path, [candidate], (50, 50, 50), scan_complete=False)
            self.assertIn('BLOCKED_INCOMPLETE_SCAN', path.read_text())
            self.assertNotIn('ELIGIBLE_FOR_REVIEW', path.read_text())
