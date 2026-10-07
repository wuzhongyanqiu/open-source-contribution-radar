# Open Source Contribution Radar

This repository owns discovery, scoring, account auditing, and contribution safety policy. It does not own scheduler state or credentials.

## Development rules

- Keep discovery and scoring deterministic and explainable.
- Use `gh auth` for GitHub access; never read, print, or persist tokens.
- Generated reports and state belong under `.radar/` and must not be committed.
- Never add automatic repository deletion, force-push, merge, or non-draft PR behavior.
- A contribution candidate must have a clear upstream need, an acceptable license, recent maintainer activity, and a reproducible validation path.

## Verification

Run `python3 -m unittest discover -s tests -v` and `python3 -m compileall -q src tests` before committing.
