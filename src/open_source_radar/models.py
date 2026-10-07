from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class IssueCandidate:
    number: int
    title: str
    url: str
    labels: list[str]
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RepositoryCandidate:
    full_name: str
    url: str
    description: str
    language: str
    topics: list[str]
    stars: int
    forks: int
    open_issues: int
    pushed_at: str
    created_at: str
    license_id: str
    archived: bool
    fork: bool
    has_contributing: bool = False
    has_ci: bool = False
    has_tests: bool = False
    issues: list[IssueCandidate] = field(default_factory=list)
    project_score: int = 0
    contribution_score: int = 0
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["issues"] = [issue.to_dict() for issue in self.issues]
        return value


@dataclass
class AccountRepository:
    name: str
    url: str
    description: str
    private: bool
    fork: bool
    archived: bool
    size_kb: int
    stars: int
    forks: int
    pushed_at: str
    created_at: str
    open_issues: int
    license_id: str
    default_branch: str
    recommendation: str = "review"
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
