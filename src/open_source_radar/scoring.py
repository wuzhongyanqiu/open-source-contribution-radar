from __future__ import annotations

from datetime import datetime, timezone
from math import log10
from typing import Dict, Optional

from .config import RadarConfig
from .models import AccountRepository, RepositoryCandidate


def _days_since(value: str, now: datetime) -> int:
    if not value:
        return 10_000
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return max(0, (now - parsed).days)


def score_candidate(
    candidate: RepositoryCandidate,
    config: RadarConfig,
    previous: Optional[Dict[str, int]] = None,
    now: Optional[datetime] = None,
) -> RepositoryCandidate:
    now = now or datetime.now(timezone.utc)
    previous = previous or {}
    text = " ".join([candidate.full_name, candidate.description, *candidate.topics]).lower()
    matched = sorted({term for term in config.relevance_terms if term in text})
    relevance = min(25, len(matched) * 6 + (5 if candidate.language in config.languages else 0))
    age_days = _days_since(candidate.pushed_at, now)
    activity = 20 if age_days <= 7 else 16 if age_days <= 30 else 11 if age_days <= 90 else 5 if age_days <= 180 else 0
    popularity = min(20, round(log10(max(1, candidate.stars)) * 6))
    community = min(
        20,
        (5 if candidate.license_id and candidate.license_id != "NOASSERTION" else 0)
        + (5 if candidate.has_contributing else 0)
        + (4 if candidate.has_ci else 0)
        + (3 if candidate.has_tests else 0)
        + (3 if candidate.open_issues else 0),
    )
    star_delta = max(0, candidate.stars - int(previous.get("stars", candidate.stars)))
    fork_delta = max(0, candidate.forks - int(previous.get("forks", candidate.forks)))
    momentum = min(15, star_delta * 2 + fork_delta * 3)
    candidate.project_score = min(100, relevance + activity + popularity + community + momentum)
    candidate.contribution_score = min(
        100,
        activity
        + community
        + min(30, len(candidate.issues) * 10)
        + min(15, popularity)
        + (10 if matched else 0),
    )
    candidate.reasons = [
        f"relevance {relevance}/25" + (f" ({', '.join(matched[:4])})" if matched else ""),
        f"activity {activity}/20 ({age_days} days since push)",
        f"popularity {popularity}/20 ({candidate.stars} stars)",
        f"community {community}/20",
        f"momentum {momentum}/15",
        f"{len(candidate.issues)} unassigned contribution issues",
    ]
    return candidate


def audit_repository(
    repository: AccountRepository,
    config: RadarConfig,
    now: Optional[datetime] = None,
) -> AccountRepository:
    now = now or datetime.now(timezone.utc)
    age_days = _days_since(repository.pushed_at, now)
    protected = repository.name.lower() in config.protected_repositories
    reasons: list[str] = []
    if protected:
        repository.recommendation = "keep"
        reasons.append("protected by account policy")
    elif repository.archived:
        repository.recommendation = "keep"
        reasons.append("already archived")
    elif repository.size_kb == 0 and repository.stars == 0 and repository.forks == 0:
        repository.recommendation = "delete_candidate"
        reasons.append("empty repository with no audience")
    elif repository.fork and age_days > config.stale_days and repository.stars == 0:
        repository.recommendation = "archive"
        reasons.append(f"inactive fork; no push for {age_days} days")
    elif age_days > config.stale_days * 2 and repository.stars <= 1 and repository.forks == 0:
        repository.recommendation = "archive"
        reasons.append(f"inactive historical project; no push for {age_days} days")
    elif age_days > config.stale_days and repository.stars == 0 and repository.forks == 0:
        repository.recommendation = "review"
        reasons.append(f"no push for {age_days} days and no audience")
    else:
        repository.recommendation = "keep"
        reasons.append(f"active within {age_days} days or has demonstrated retained value")
    if not repository.description:
        reasons.append("missing description")
    if not repository.private and not repository.license_id and repository.name.lower() != config.audit_owner.lower():
        reasons.append("public repository has no detected license")
    repository.reasons = reasons
    return repository
