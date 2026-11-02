from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from .config import RadarConfig
from .models import RepositoryCandidate
from .report import is_eligible


def _ticket_id(thread: str) -> str:
    digest = hashlib.sha256(thread.encode("utf-8")).hexdigest()[:16]
    return f"contribution-{digest}"


def build_ticket_feed(
    candidates: list[RepositoryCandidate],
    config: RadarConfig,
    generated_at: datetime,
    *,
    scan_complete: bool,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create a read-only Super-agent inbox from the deterministic scan."""
    tickets: list[dict[str, Any]] = []
    if not scan_complete:
        tickets.append({
            "id": _ticket_id("open-source-radar:incomplete-scan"),
            "project": "open-source-contribution-radar",
            "thread": "scan:open-source-contribution-radar",
            "source": "open-source-radar",
            "kind": "collection_failure",
            "state": "blocked",
            "priority": "high",
            "title": "开源贡献扫描不完整",
            "summary": f"本轮有 {len(errors)} 个采集错误，禁止启动贡献任务。",
            "worker": "collection-diagnosis",
            "evidence": [f"{item.get('stage', 'unknown')}: {item.get('error', 'unknown')}" for item in errors[:8]],
            "allowedActions": ["inspect_scan_evidence", "prepare_local_fix"],
            "requiresHuman": ["publish_change", "contact_maintainer"],
        })
    else:
        for candidate in candidates:
            if not is_eligible(
                candidate,
                config.project_score,
                config.contribution_score,
                config.minimum_stars,
                max_idle_days=config.stale_days,
                now=generated_at,
            ):
                continue
            for issue in candidate.issues:
                thread = f"github:{candidate.full_name}#{issue.number}"
                tickets.append({
                    "id": _ticket_id(thread),
                    "project": "open-source-contribution-radar",
                    "thread": thread,
                    "source": "open-source-radar",
                    "kind": "upstream_contribution",
                    "state": "candidate",
                    "priority": "high" if candidate.contribution_score >= 80 else "normal",
                    "title": f"{candidate.full_name} #{issue.number} {issue.title}",
                    "summary": (
                        f"项目分 {candidate.project_score}，贡献分 {candidate.contribution_score}；"
                        "仅允许隔离验证和 Draft PR 候选。"
                    ),
                    "worker": "upstream-contribution",
                    "evidence": [candidate.url, issue.url],
                    "allowedActions": [
                        "inspect_upstream_policy",
                        "clone_isolated",
                        "prepare_scoped_change",
                        "run_upstream_checks",
                        "prepare_draft_pr",
                    ],
                    "requiresHuman": [
                        "publish_draft_pr",
                        "mark_pr_ready",
                        "merge",
                        "force_push",
                        "delete_repository",
                    ],
                })
    return {
        "schemaVersion": 1,
        "generatedAt": generated_at.isoformat(),
        "mode": "observe",
        "source": "open-source-contribution-radar",
        "tickets": tickets,
    }
