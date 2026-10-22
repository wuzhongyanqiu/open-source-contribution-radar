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
