# Responsible contribution policy

Automated discovery is not permission to publish. Every upstream contribution must satisfy all gates below.

## Candidate gates

1. The repository is not archived and has an identifiable open-source license.
2. The default branch has recent maintainer activity.
3. `CONTRIBUTING`, `AGENTS.md`, security policy, CLA, DCO, and bot rules are read and followed.
4. The task addresses an existing issue, failing test, reproducible bug, or explicitly requested documentation gap.
5. The task is unassigned, not already covered by an open PR, and not marked unavailable.
6. The change can be explained narrowly and validated locally.

## Prohibited contributions

- Bulk typo, formatting, dependency-churn, or generated-documentation PRs.
- Drive-by rewrites without a maintainer request.
- Changes to security-sensitive targets without explicit authorization.
- License removal, provenance laundering, benchmark manipulation, or secret collection.
- Multiple simultaneous PRs to the same repository.

## Publication gates

- Work in an isolated clone or worktree.
- Run the upstream checks closest to the change and record exact results.
- Review the full diff for generated files, secrets, unrelated changes, and attribution.
- Use the language and PR template required by upstream.
- Create a Draft PR only. Never merge or mark ready automatically.
- Stop after one Draft PR per scheduled run.
