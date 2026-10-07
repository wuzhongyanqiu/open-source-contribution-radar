from datetime import datetime, timezone
import unittest

from open_source_radar.config import RadarConfig
from open_source_radar.models import AccountRepository, IssueCandidate, RepositoryCandidate
from open_source_radar.report import is_eligible
from open_source_radar.scoring import audit_repository, score_candidate


NOW = datetime(2026, 10, 8, tzinfo=timezone.utc)


def config() -> RadarConfig:
    return RadarConfig(
        queries=("topic:agent",),
        issue_queries=("agent is:issue",),
        languages=("Python",),
        relevance_terms=("agent", "evaluation"),
        excluded_owners=frozenset(),
        excluded_repositories=frozenset(),
        excluded_issue_labels=frozenset({"security"}),
        max_results_per_query=10,
        max_candidates=20,
        project_score=55,
        contribution_score=55,
        minimum_stars=50,
        stale_days=180,
        audit_owner="owner",
        protected_repositories=frozenset({"production"}),
    )


class ScoringTest(unittest.TestCase):
    def test_active_well_documented_candidate_scores_highly(self) -> None:
        candidate = RepositoryCandidate(
            full_name="example/agent-evaluation",
            url="https://github.com/example/agent-evaluation",
            description="Agent evaluation framework",
            language="Python",
            topics=["agent"],
            stars=1500,
            forks=100,
            open_issues=20,
            pushed_at="2026-10-07T00:00:00Z",
            created_at="2025-01-01T00:00:00Z",
            license_id="MIT",
            archived=False,
            fork=False,
            has_contributing=True,
            has_ci=True,
            has_tests=True,
            issues=[IssueCandidate(1, "Fix edge case", "https://example/1", ["good first issue"], "", "")],
        )
        result = score_candidate(candidate, config(), now=NOW)
        self.assertGreaterEqual(result.project_score, 65)
        self.assertGreaterEqual(result.contribution_score, 65)
        self.assertTrue(any("activity" in reason for reason in result.reasons))
        self.assertTrue(is_eligible(result, 55, 55))

    def test_candidate_without_issue_is_not_eligible(self) -> None:
        candidate = RepositoryCandidate(
            full_name="example/agent",
            url="https://github.com/example/agent",
            description="Agent framework",
            language="Python",
            topics=["agent"],
            stars=5000,
            forks=100,
            open_issues=10,
            pushed_at="2026-10-07T00:00:00Z",
            created_at="2025-01-01T00:00:00Z",
            license_id="MIT",
            archived=False,
            fork=False,
            has_contributing=True,
            has_ci=True,
            has_tests=True,
        )
        result = score_candidate(candidate, config(), now=NOW)
        self.assertFalse(is_eligible(result, 55, 55))

    def test_low_audience_candidate_is_not_eligible(self) -> None:
        candidate = RepositoryCandidate(
            full_name="example/tiny-agent",
            url="https://github.com/example/tiny-agent",
            description="Agent framework",
            language="Python",
            topics=["agent"],
            stars=4,
            forks=1,
            open_issues=3,
            pushed_at="2026-10-07T00:00:00Z",
            created_at="2026-01-01T00:00:00Z",
            license_id="MIT",
            archived=False,
            fork=False,
            has_contributing=True,
            has_ci=True,
            has_tests=True,
            issues=[IssueCandidate(1, "Add parser test", "https://example/1", ["good first issue"], "", "")],
        )
        result = score_candidate(candidate, config(), now=NOW)
        self.assertFalse(is_eligible(result, 55, 55, 50))

    def test_empty_repository_is_delete_candidate(self) -> None:
        repository = AccountRepository(
            name="empty",
            url="https://github.com/owner/empty",
            description="",
            private=True,
            fork=False,
            archived=False,
            size_kb=0,
            stars=0,
            forks=0,
            pushed_at="2024-01-01T00:00:00Z",
            created_at="2024-01-01T00:00:00Z",
            open_issues=0,
            license_id="",
            default_branch="main",
        )
        result = audit_repository(repository, config(), now=NOW)
        self.assertEqual(result.recommendation, "delete_candidate")

    def test_protected_repository_is_kept(self) -> None:
        repository = AccountRepository(
            name="production",
            url="https://github.com/owner/production",
            description="service",
            private=True,
            fork=False,
            archived=False,
            size_kb=0,
            stars=0,
            forks=0,
            pushed_at="2024-01-01T00:00:00Z",
            created_at="2024-01-01T00:00:00Z",
            open_issues=0,
            license_id="",
            default_branch="main",
        )
        result = audit_repository(repository, config(), now=NOW)
        self.assertEqual(result.recommendation, "keep")


if __name__ == "__main__":
    unittest.main()
