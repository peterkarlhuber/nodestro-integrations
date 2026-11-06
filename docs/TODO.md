# TODO: nodestro-integrations

> Open work for this repository: release blockers, known bugs, security follow-ups, technical debt and planned improvements.
> GitHub issues are the source of truth for details; this file is the entry point and summary.
>
> **Last full review:** 2026-11-06 against `master` at `11a8271` (TODO abatement round).

## Summary

| Priority | Count |
|---|---|
| P0 Critical | 0 |
| P1 High | 0 |
| P2 Medium | 0 |
| P3 Low | 1 |
| P4 Optional | 3 |

**Release blockers:** None. No entry blocks the frozen desktop candidate v0.2.0-preview.1 or the next preview;
every entry below is not a release blocker. None needs an external security review.

The package (local OCR of scanned PDFs) is small and well covered: no TODO markers or
skipped tests in the code, real-OCR tests that CI cannot skip, a dependency audit and SHA-pinned actions. What remains
is hardening for the server profile, the first macOS and Windows CI runs and documented limits of OCR itself.

## Priorities and statuses

- **P0 Critical**: data loss, security exposure, or broken core function; blocks any release.
- **P1 High**: blocks a planned release or a promised capability, or a significant risk.
- **P2 Medium**: real defect or gap with a workaround; schedule soon.
- **P3 Low**: minor defect, polish, or small debt.
- **P4 Optional**: improvement idea; not a defect.

Statuses: `Open`, `In progress` (PR linked), `Blocked` (names the blocker), `Needs decision` (owner decision pending),
`Needs external review`, `Accepted risk` (deliberately not fixed; reason stated).

## Release blockers and critical items

None known.

## Security

### INT-001 · Resource hardening of OCR for many parallel documents

- **Priority:** P3 Low · **Status:** Needs decision · **Refs:** identified in this inventory; backend audit
  2026-11-03 (ORK2-05, re-verified in round 3)
- **What:** Limits apply per document (pages, pixels, time, one thread per tesseract call). How many documents are
  recognized at the same time in one process is not bounded here, and behavior under parallel load in the server
  profile is not measured. The per-page pixel bound itself could be exceeded (a page larger than the limit even at
  1 dpi was rendered anyway, 193 Mpx, about 750 MB for poppler); since the 2026-11-03 fix such pages are refused,
  so the per-document memory bound now holds, but parallel documents still multiply it.
- **Next step:** Decide whether the bound belongs in this package or in the runtime's knowledge and input-file
  handling, then add it with a test and document it under "Limits".
- **Depends on:** possibly nodestro-runtime (where OCR is called)

## Bugs and reliability

None known.

## Architecture and modularity

None known.

## Performance

None known.

## Features and enhancements

None known.

## Tests and quality assurance

None known.

## Platform coverage

## Documentation

None known.

## Technical debt

None known.

## Later optimizations

None known.

## Accepted risks

### INT-004 · OCR programs run with the current user's rights

- **Priority:** P4 Optional · **Status:** Accepted risk · **Refs:** README "Security and privacy"
- **What:** poppler and tesseract parse untrusted PDFs as system programs, without a shell, with a reduced environment,
  in a private temporary folder and within the limits; they are not otherwise sandboxed.
- **Reason:** These are maintained system packages; isolating them would need the container sandbox. Keeping them
  updated is the operator's job and is documented. Re-evaluate before any production server deployment.
- **Re-evaluated 2026-11-03:** still acceptable for the desktop. For the server profile the risk is resource
  exhaustion more than code execution: there is no address-space limit for the programs (RLIMIT_AS on POSIX) and no
  bound on parallel documents (INT-001). Before a server deployment, add RLIMIT_AS for poppler and tesseract or run
  OCR in the container sandbox.

### INT-005 · OCR quality limits (multi-column order, poor scans)

- **Priority:** P4 Optional · **Status:** Accepted risk · **Refs:** README "Quality"
- **What:** Multi-column pages follow tesseract's layout analysis; poor scans, small print and handwriting give
  errors. Uncertain words are marked and the runtime asks the reader to check important passages.
- **Reason:** Inherent to OCR; documented for users.

### INT-006 · Python dependencies not watched by Dependabot

- **Priority:** P4 Optional · **Status:** Accepted risk · **Refs:** `.github/dependabot.yml`, `.github/workflows/ci.yml`
- **What:** Dependabot updates only GitHub Actions; the Nodestro dependencies are pinned by Git commit.
- **Reason:** Pins move with the platform's pin cascade, and the blocking `pip-audit` step in CI catches known
  vulnerabilities. The original reason (private Git URLs) no longer applies now that all repositories are public
  (the comment in `dependabot.yml` says so since 2026-11-03); a pip ecosystem entry can be re-evaluated now that CI
  no longer needs a token.

## Cross-repository dependencies

| This repo item | Other repo | Other item | Relation |
|---|---|---|---|
| (pointer) | nodestro-studio | ST-052 (Dependabot policy: weekly groups, cooldown, manual merge; auto-merge prerequisites) | Full entry in studio |
| INT-001 | nodestro-runtime | pointer row in its cross-repo table (no RT entry; this entry owns the topic) | The bound may belong where the runtime calls OCR. |

## CI access to private repositories

Keep the repository secret `NODESTRO_READ`; do not delete it. CI currently installs the sibling repositories anonymously
because they are public, and does not need the secret. When the repositories become private, CI authenticates again
with this read-only secret, passed only in the environment of the install steps (never in a global Git configuration,
a log or an image layer).

## Maintaining this file

- Add an entry when work is identified but not done in the current PR. Use the next free ID; IDs are never reused.
- Link a GitHub issue for anything concrete enough to be picked up; keep details in the issue, not here.
- When an item is finished, delete its entry in the PR that completes it and mention the ID in the PR description.
  Git history is the record; do not keep ticked checklists.
- Accepted risks stay listed with their reason until the risk is removed or re-evaluated.
- Re-review the whole file before each release and update the "Last full review" line.
- Security issues that are not yet fixed are described only in general terms here. Report details privately
  (GitHub private vulnerability reporting), never in this file or in public issues.
