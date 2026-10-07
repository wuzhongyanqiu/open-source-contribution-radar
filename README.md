# Open Source Contribution Radar

Open Source Contribution Radar finds actively maintained projects, explains why they are worth attention, and surfaces concrete issues that can become responsible contributions. It also audits a GitHub account for empty, abandoned, or low-signal repositories without deleting anything.

The project is deliberately conservative: discovery is automated, but public contribution is gated by repository policy, reproducible tests, and human-reviewable evidence. Scheduled agents may create at most one **Draft PR** per day. They may never merge, force-push, delete repositories, or submit bulk cosmetic changes.

## What it does

- Searches GitHub using configurable topics and minimum popularity signals.
- Scores relevance, maintenance activity, community health, popularity, and observed momentum.
- Finds open `good first issue` and `help wanted` tasks.
- Produces Markdown and JSON reports with an explanation for every score.
- Audits repositories owned by an account and recommends `keep`, `archive`, `review`, or `delete_candidate`.
- Keeps generated state and reports in `.radar/`, outside version control.

## Requirements

- Python 3.9+
- GitHub CLI (`gh`)
- An authenticated GitHub session: `gh auth status`

No GitHub token is read or stored by this project. All API access goes through the authenticated `gh` process.

## Usage

```bash
PYTHONPATH=src python3 -m open_source_radar scan
PYTHONPATH=src python3 -m open_source_radar audit-account --owner wuzhongyanqiu
```

Reports are written to `.radar/reports/`. Edit [`radar.json`](radar.json) to tune discovery queries, thresholds, exclusions, and protected repositories.

## Contribution workflow

The deterministic scanner stops at a ranked queue. An agent working from that queue must follow [`CONTRIBUTION_POLICY.md`](CONTRIBUTION_POLICY.md): inspect upstream instructions, verify that an issue is still available, work in isolation, run the repository's checks, and create a Draft PR with evidence. A failed gate means no PR.

## Account audit semantics

`delete_candidate` is evidence, not authorization. It is reserved for empty or one-commit repositories with no audience or unique content. `archive` is used for stale forks or completed historical work. The tool intentionally has no delete command.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
```

## License

MIT
