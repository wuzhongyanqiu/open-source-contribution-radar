from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import AccountRepository, RepositoryCandidate


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_discovery_report(path: Path, candidates: list[RepositoryCandidate], thresholds: tuple[int, int]) -> None:
    project_threshold, contribution_threshold = thresholds
    lines = [
        "# Open-source contribution radar",
        "",
        f"Generated: {datetime.now().astimezone().isoformat()}",
        "",
        "Only candidates meeting both configured thresholds are eligible for agent review. Eligibility is not permission to publish.",
        "",
    ]
    for index, candidate in enumerate(candidates, 1):
        eligible = is_eligible(candidate, project_threshold, contribution_threshold)
        lines.extend([
            f"## {index}. [{candidate.full_name}]({candidate.url})",
            "",
            f"- Decision: {'ELIGIBLE_FOR_REVIEW' if eligible else 'OBSERVE'}",
            f"- Project score: {candidate.project_score}/100",
            f"- Contribution score: {candidate.contribution_score}/100",
            f"- Language: {candidate.language or 'unknown'}; stars: {candidate.stars}; forks: {candidate.forks}",
            f"- License: {candidate.license_id or 'unknown'}; last push: {candidate.pushed_at or 'unknown'}",
            f"- Signals: {'; '.join(candidate.reasons)}",
            "",
        ])
        for issue in candidate.issues[:5]:
            lines.append(f"- [#{issue.number} {issue.title}]({issue.url}) ({', '.join(issue.labels)})")
        if candidate.issues:
            lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_account_report(path: Path, owner: str, repositories: list[AccountRepository]) -> None:
    lines = [
        f"# GitHub account audit: {owner}",
        "",
        f"Generated: {datetime.now().astimezone().isoformat()}",
        "",
        "Recommendations are read-only. `delete_candidate` never authorizes deletion.",
        "",
        "| Recommendation | Repository | Visibility | Last push | Evidence |",
        "| --- | --- | --- | --- | --- |",
    ]
    order = {"delete_candidate": 0, "archive": 1, "review": 2, "keep": 3}
    repositories.sort(key=lambda item: (order.get(item.recommendation, 9), item.name.lower()))
    for repository in repositories:
        visibility = "private" if repository.private else "public"
        evidence = "; ".join(repository.reasons).replace("|", "\\|")
        lines.append(
            f"| {repository.recommendation} | [{repository.name}]({repository.url}) | {visibility} | "
            f"{repository.pushed_at or 'unknown'} | {evidence} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def is_eligible(candidate: RepositoryCandidate, project_threshold: int, contribution_threshold: int) -> bool:
    return (
        candidate.project_score >= project_threshold
        and candidate.contribution_score >= contribution_threshold
        and bool(candidate.issues)
        and bool(candidate.license_id)
        and candidate.license_id != "NOASSERTION"
    )
