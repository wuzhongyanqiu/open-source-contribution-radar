import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from open_source_radar.config import load_config


class ConfigTest(unittest.TestCase):
    def test_loads_and_normalizes_config(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "radar.json"
            path.write_text(json.dumps({
                "discovery": {"queries": ["topic:agent"], "issue_queries": ["agent is:issue"], "excluded_owners": ["Example"]},
                "thresholds": {"project_score": 60, "contribution_score": 50},
                "account_audit": {"owner": "owner", "protected_repositories": ["Keep"]},
            }), encoding="utf-8")
            config = load_config(path)
        self.assertEqual(config.queries, ("topic:agent",))
        self.assertEqual(config.issue_queries, ("agent is:issue",))
        self.assertIn("example", config.excluded_owners)
        self.assertIn("keep", config.protected_repositories)
        self.assertEqual(config.project_score, 60)

    def test_requires_query(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "radar.json"
            path.write_text('{"discovery":{"queries":[]}}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must not be empty"):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
