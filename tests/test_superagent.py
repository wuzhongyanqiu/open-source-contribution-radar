from datetime import datetime, timezone
from pathlib import Path
import unittest

from open_source_radar.config import load_config
from open_source_radar.models import IssueCandidate, RepositoryCandidate
from open_source_radar.superagent import build_ticket_feed


class SuperagentFeedTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config(Path(__file__).parents[1] / "radar.json")
        self.now = datetime.now(timezone.utc)

    def candidate(self) -> RepositoryCandidate:
        return RepositoryCandidate(
            "example/agent", "https://github.com/example/agent", "", "Python", [],
            1000, 10, 1, self.now.isoformat(), self.now.isoformat(), "MIT", False, False,
            issues=[IssueCandidate(7, "Fix bounded bug", "https://github.com/example/agent/issues/7", ["help wanted"], "", "")],
            project_score=90, contribution_score=85,
        )

    def test_eligible_issue_becomes_observe_only_ticket(self) -> None:
        feed = build_ticket_feed([self.candidate()], self.config, self.now, scan_complete=True, errors=[])
        self.assertEqual(feed["mode"], "observe")
        self.assertEqual(len(feed["tickets"]), 1)
        ticket = feed["tickets"][0]
        self.assertEqual(ticket["thread"], "github:example/agent#7")
        self.assertIn("prepare_draft_pr", ticket["allowedActions"])
        self.assertIn("publish_draft_pr", ticket["requiresHuman"])
        self.assertIn("merge", ticket["requiresHuman"])

    def test_incomplete_scan_blocks_contribution_tickets(self) -> None:
        feed = build_ticket_feed(
            [self.candidate()], self.config, self.now,
            scan_complete=False, errors=[{"stage": "issue_search", "error": "rate limit"}],
        )
        self.assertEqual([item["kind"] for item in feed["tickets"]], ["collection_failure"])
        self.assertEqual(feed["tickets"][0]["state"], "blocked")
