from __future__ import annotations

import base64
import json
import subprocess
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from .models import AccountRepository, IssueCandidate, RepositoryCandidate


class GithubError(RuntimeError):
    pass


class GithubClient:
    def __init__(self, executable: str = "gh") -> None:
        self.executable = executable

    def request(self, endpoint: str, fields: Optional[Dict[str, str]] = None) -> Any:
        command = [self.executable, "api", "--method", "GET", endpoint]
        for key, value in (fields or {}).items():
            command.extend(["-f", f"{key}={value}"])
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown gh error"
            raise GithubError(f"GitHub request failed for {endpoint}: {detail}")
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise GithubError(f"GitHub returned invalid JSON for {endpoint}") from error

    def search_repositories(self, query: str, limit: int) -> list[RepositoryCandidate]:
        payload = self.request(
            "search/repositories",
            {"q": query, "sort": "updated", "order": "desc", "per_page": str(limit)},
        )
        return [self._repository(item) for item in payload.get("items", [])]

    def get_repository(self, full_name: str) -> RepositoryCandidate:
        return self._repository(self.request(f"repos/{full_name}"))

    def search_issues(self, query: str, limit: int) -> list[tuple[str, IssueCandidate]]:
        payload = self.request(
            "search/issues",
            {"q": query, "sort": "updated", "order": "desc", "per_page": str(limit)},
        )
        results = []
        for item in payload.get("items", []):
            repository_url = str(item.get("repository_url") or "")
            marker = "/repos/"
            if marker not in repository_url:
                continue
            full_name = repository_url.split(marker, 1)[1]
            results.append((full_name, self._issue(item)))
        return results

    def enrich(self, candidate: RepositoryCandidate) -> RepositoryCandidate:
        owner, name = candidate.full_name.split("/", 1)
        root = self.request(f"repos/{quote(owner)}/{quote(name)}/contents")
        names = {str(item.get("name", "")).lower() for item in root if isinstance(item, dict)}
        candidate.has_contributing = any(name.startswith("contributing") for name in names) or ".github" in names
        candidate.has_ci = ".github" in names or any(name.startswith((".travis", "azure-pipelines")) for name in names)
        candidate.has_tests = any(name in names for name in ("test", "tests", "spec", "specs"))
        return candidate

    def list_account_repositories(self, owner: str) -> list[AccountRepository]:
        authenticated = self.request("user")
        is_self = str(authenticated.get("login", "")).lower() == owner.lower()
        page = 1
        repositories: list[AccountRepository] = []
        while True:
            endpoint = "user/repos" if is_self else f"users/{quote(owner)}/repos"
            fields = {
                "sort": "pushed",
                "direction": "desc",
                "per_page": "100",
                "page": str(page),
            }
            fields["affiliation" if is_self else "type"] = "owner"
            payload = self.request(
                endpoint,
                fields,
            )
            repositories.extend(self._account_repository(item) for item in payload)
            if len(payload) < 100:
                return repositories
            page += 1

    def read_text_file(self, full_name: str, path: str) -> Optional[str]:
        try:
            payload = self.request(f"repos/{full_name}/contents/{quote(path)}")
        except GithubError:
            return None
        encoded = payload.get("content") if isinstance(payload, dict) else None
        if not encoded:
            return None
        return base64.b64decode(encoded).decode("utf-8", errors="replace")

    @staticmethod
    def _issue(item: dict[str, Any]) -> IssueCandidate:
        return IssueCandidate(
            number=int(item["number"]),
            title=str(item.get("title") or ""),
            url=str(item.get("html_url") or ""),
            labels=[str(value.get("name")) for value in item.get("labels", []) if value.get("name")],
            created_at=str(item.get("created_at") or ""),
            updated_at=str(item.get("updated_at") or ""),
        )

    @staticmethod
    def _repository(item: dict[str, Any]) -> RepositoryCandidate:
        license_value = item.get("license") or {}
        return RepositoryCandidate(
            full_name=str(item["full_name"]),
            url=str(item["html_url"]),
            description=str(item.get("description") or ""),
            language=str(item.get("language") or ""),
            topics=[str(topic) for topic in item.get("topics", [])],
            stars=int(item.get("stargazers_count") or 0),
            forks=int(item.get("forks_count") or 0),
            open_issues=int(item.get("open_issues_count") or 0),
            pushed_at=str(item.get("pushed_at") or ""),
            created_at=str(item.get("created_at") or ""),
            license_id=str(license_value.get("spdx_id") or ""),
            archived=bool(item.get("archived")),
            fork=bool(item.get("fork")),
        )

    @staticmethod
    def _account_repository(item: dict[str, Any]) -> AccountRepository:
        license_value = item.get("license") or {}
        return AccountRepository(
            name=str(item["name"]),
            url=str(item["html_url"]),
            description=str(item.get("description") or ""),
            private=bool(item.get("private")),
            fork=bool(item.get("fork")),
            archived=bool(item.get("archived")),
            size_kb=int(item.get("size") or 0),
            stars=int(item.get("stargazers_count") or 0),
            forks=int(item.get("forks_count") or 0),
            pushed_at=str(item.get("pushed_at") or ""),
            created_at=str(item.get("created_at") or ""),
            open_issues=int(item.get("open_issues_count") or 0),
            license_id=str(license_value.get("spdx_id") or ""),
            default_branch=str(item.get("default_branch") or "main"),
        )
