from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RadarConfig:
    queries: tuple[str, ...]
    issue_queries: tuple[str, ...]
    languages: tuple[str, ...]
    relevance_terms: tuple[str, ...]
    excluded_owners: frozenset[str]
    excluded_repositories: frozenset[str]
    excluded_issue_labels: frozenset[str]
    max_results_per_query: int
    max_candidates: int
    project_score: int
    contribution_score: int
    minimum_stars: int
    stale_days: int
    audit_owner: str
    protected_repositories: frozenset[str]


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ValueError(f"[{name}] must be a table")
    return value


def load_config(path: Path) -> RadarConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    discovery = _section(data, "discovery")
    thresholds = _section(data, "thresholds")
    audit = _section(data, "account_audit")
    queries = tuple(str(item).strip() for item in discovery.get("queries", []) if str(item).strip())
    if not queries:
        raise ValueError("discovery.queries must not be empty")
    return RadarConfig(
        queries=queries,
        issue_queries=tuple(str(item).strip() for item in discovery.get("issue_queries", []) if str(item).strip()),
        languages=tuple(str(item) for item in discovery.get("languages", [])),
        relevance_terms=tuple(str(item).lower() for item in discovery.get("relevance_terms", [])),
        excluded_owners=frozenset(str(item).lower() for item in discovery.get("excluded_owners", [])),
        excluded_repositories=frozenset(str(item).lower() for item in discovery.get("excluded_repositories", [])),
        excluded_issue_labels=frozenset(str(item).lower() for item in discovery.get("excluded_issue_labels", [])),
        max_results_per_query=max(1, min(100, int(discovery.get("max_results_per_query", 10)))),
        max_candidates=max(1, int(discovery.get("max_candidates", 30))),
        project_score=max(0, min(100, int(thresholds.get("project_score", 55)))),
        contribution_score=max(0, min(100, int(thresholds.get("contribution_score", 55)))),
        minimum_stars=max(0, int(thresholds.get("minimum_stars", 0))),
        stale_days=max(30, int(thresholds.get("max_repository_age_without_push_days", 180))),
        audit_owner=str(audit.get("owner", "")).strip(),
        protected_repositories=frozenset(str(item).lower() for item in audit.get("protected_repositories", [])),
    )
