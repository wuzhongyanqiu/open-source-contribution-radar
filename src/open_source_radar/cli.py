from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

from .config import RadarConfig, load_config
from .github import GithubClient, GithubError
from .report import is_eligible, write_account_report, write_discovery_report, write_json
from .scoring import audit_repository, score_candidate


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Discover valuable open-source contribution opportunities")
    parser.add_argument("--config", type=Path, default=Path("radar.json"))
    parser.add_argument("--state-dir", type=Path, default=Path(".radar"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("scan", help="discover and score contribution candidates")
    audit = subparsers.add_parser("audit-account", help="audit owned repositories without changing them")
    audit.add_argument("--owner", default="")
    return parser


def _load_previous(path: Path) -> dict[str, dict[str, int]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    repositories = payload.get("repositories", {})
    return repositories if isinstance(repositories, dict) else {}


def _scan(config: RadarConfig, state_dir: Path, client: GithubClient) -> int:
    found = {}
    errors = []
    for query in config.queries:
        try:
            results = client.search_repositories(query, config.max_results_per_query)
        except GithubError as error:
            errors.append({"stage": "repository_search", "query": query, "error": str(error)})
            continue
        for candidate in results:
            owner = candidate.full_name.split("/", 1)[0].lower()
            if owner in config.excluded_owners or candidate.full_name.lower() in config.excluded_repositories:
                continue
            if candidate.archived or candidate.fork:
                continue
            found[candidate.full_name.lower()] = candidate
    discovered_issues = {}
    for query in config.issue_queries:
        try:
            results = client.search_issues(query, config.max_results_per_query)
        except GithubError as error:
            errors.append({"stage": "issue_search", "query": query, "error": str(error)})
            continue
        for full_name, issue in results:
            owner = full_name.split("/", 1)[0].lower()
            if owner in config.excluded_owners or full_name.lower() in config.excluded_repositories:
                continue
            issue_labels = {label.lower() for label in issue.labels}
            if issue_labels & config.excluded_issue_labels:
                continue
            key = full_name.lower()
            discovered_issues.setdefault(key, {})[issue.number] = issue
            if key not in found:
                try:
                    found[key] = client.get_repository(full_name)
                except GithubError as error:
                    errors.append({"stage": "repository", "repo": full_name, "error": str(error)})
                    continue
    for key, issues in discovered_issues.items():
        if key in found:
            found[key].issues = sorted(issues.values(), key=lambda item: item.updated_at, reverse=True)
    # Issue discovery must obey the same repository policy as repository search.
    found = {key: candidate for key, candidate in found.items() if not candidate.archived and not candidate.fork}
    previous = _load_previous(state_dir / "state.json")
    shortlist = sorted(found.values(), key=lambda item: (bool(item.issues), item.stars, item.pushed_at), reverse=True)[: config.max_candidates]
    candidates = []
    for candidate in shortlist:
        try:
            client.enrich(candidate)
        except GithubError as error:
            candidate.reasons.append(f"enrichment warning: {error}")
            errors.append({"stage": "enrichment", "repo": candidate.full_name, "error": str(error)})
        candidates.append(score_candidate(candidate, config, previous.get(candidate.full_name.lower())))
    candidates.sort(key=lambda item: (item.contribution_score, item.project_score, item.stars), reverse=True)
    stamp = datetime.now().astimezone().date().isoformat()
    reports = state_dir / "reports"
    write_discovery_report(
        reports / f"discovery-{stamp}.md",
        candidates,
        (config.project_score, config.contribution_score, config.minimum_stars),
        scan_complete=not errors,
        max_idle_days=config.stale_days,
    )
    eligible = [
        item for item in candidates
        if is_eligible(item, config.project_score, config.contribution_score, config.minimum_stars, max_idle_days=config.stale_days)
    ]
    status = ("PARTIAL" if candidates else "FAILED") if errors else ("SUCCESS" if eligible else "NO_CANDIDATES")
    generated = datetime.now(timezone.utc)
    payload = {"generated_at": generated.isoformat(), "status": status, "errors": errors,
               "eligible_count": len(eligible) if not errors else 0,
               "candidates": [item.to_dict() for item in candidates]}
    write_json(reports / f"discovery-{stamp}.json", payload)
    write_json(state_dir / "runs" / f"{generated.strftime('%Y%m%dT%H%M%S%fZ')}.json", payload)
    if not errors:
        write_json(state_dir / "state.json", {
            "updated_at": generated.isoformat(),
            "repositories": {item.full_name.lower(): {"stars": item.stars, "forks": item.forks} for item in candidates},
        })
    else:
        with (reports / f"discovery-{stamp}.md").open("a", encoding="utf-8") as report:
            report.write("\n## Incomplete scan — do not start contributions\n\n")
            for error in errors:
                report.write(f"- {error['stage']}: {error['error']}\n")
        print(f"{status}: {len(errors)} collection errors; previous complete baseline preserved")
    print(f"Scanned {len(candidates)} candidates; {len(eligible) if not errors else 0} eligible for agent review")
    print(reports / f"discovery-{stamp}.md")
    return 1 if errors else 0


def _audit(config: RadarConfig, state_dir: Path, client: GithubClient, owner: str) -> int:
    owner = owner or config.audit_owner
    if not owner:
        raise ValueError("account owner is required")
    repositories = [audit_repository(item, config) for item in client.list_account_repositories(owner)]
    stamp = datetime.now().astimezone().date().isoformat()
    reports = state_dir / "reports"
    write_account_report(reports / f"account-{owner}-{stamp}.md", owner, repositories)
    write_json(reports / f"account-{owner}-{stamp}.json", {"owner": owner, "generated_at": datetime.now(timezone.utc).isoformat(), "repositories": [item.to_dict() for item in repositories]})
    counts: dict[str, int] = {}
    for repository in repositories:
        counts[repository.recommendation] = counts.get(repository.recommendation, 0) + 1
    summary = ", ".join(f"{name}={value}" for name, value in sorted(counts.items()))
    print(f"Audited {len(repositories)} repositories: {summary}")
    print(reports / f"account-{owner}-{stamp}.md")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        config = load_config(args.config)
        client = GithubClient()
        if args.command == "scan":
            return _scan(config, args.state_dir, client)
        return _audit(config, args.state_dir, client, args.owner)
    except (GithubError, OSError, ValueError) as error:
        print(f"error: {error}")
        return 1
