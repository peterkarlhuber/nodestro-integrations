# TODO: nodestro-integrations

> Open work for this repository: release blockers, known bugs, security follow-ups, technical debt and planned improvements.
> GitHub issues are the source of truth for details; this file is the entry point and summary.
>
> **Last full review:** 2026-11-01 against `master` at `204c95c`.

## Summary

| Priority | Count |
|---|---|
| P0 Critical | 0 |
| P1 High | 0 |
| P2 Medium | 0 |
| P3 Low | 3 |
| P4 Optional | 4 |

**Release blockers:** None for this repository.

The package (local OCR of scanned PDFs) is small and well covered: no TODO markers or
skipped tests in the code, real-OCR tests that CI cannot skip, a dependency audit and SHA-pinned actions. What remains
is hardening for the server profile, platform coverage and documented limits of OCR itself.

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

- **Priority:** P3 Low · **Status:** Needs decision · **Refs:** identified in this inventory
- **What:** Limits apply per document (pages, pixels, time, one thread per tesseract call). How many documents are
  recognized at the same time in one process is not bounded here, and behavior under parallel load in the server
  profile is not measured.
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

### INT-002 · OCR untested on macOS, Windows and Python 3.11/3.12

- **Priority:** P3 Low · **Status:** Open · **Refs:** README "Installation", integrations quality round 2026-10-30
- **What:** CI runs Ubuntu with Python 3.10 and 3.13 only. The Homebrew and Windows install paths are documented but
  never run; Windows output decoding was fixed without a real Windows run. Load behavior in the server profile is not
  measured (see INT-001).
- **Next step:** Run the real-OCR tests once on macOS and Windows (or add CI jobs) and record the result in the README.

## Documentation

None known.

## Technical debt

### INT-007 · CI requires the `NODESTRO_READ` token although the dependencies are public

- **Priority:** P3 Low · **Status:** Open · **Refs:** #36, backend audit D-08 residual
- **What:** The CI install steps exit when the `NODESTRO_READ` secret is missing and still call the components
  private. All Nodestro repositories and orkexa are public now, so runs without secrets (Dependabot, forks) fail early.
- **Next step:** Install the git dependencies anonymously, make the token optional or remove it, fix the comments.
- **Depends on:** none; the same change is tracked in nodestro-api #50, nodestro-sdk #47, nodestro-server #25,
  nodestro-desktop #17 and nodestro-studio #85.

## Later optimizations

### INT-003 · Faster detection of the main language

- **Priority:** P4 Optional · **Status:** Open · **Refs:** README "Limits", integrations quality round 2026-10-30
- **What:** Reading the first page once per installed language costs about 4 s per document with all six languages.
- **Next step:** Measure a cheaper probe (e.g. a crop of the first page or tesseract's script detection) against the
  accent-preservation tests before changing anything.

## Accepted risks

### INT-004 · OCR programs run with the current user's rights

- **Priority:** P4 Optional · **Status:** Accepted risk · **Refs:** README "Security and privacy"
- **What:** poppler and tesseract parse untrusted PDFs as system programs, without a shell, with a reduced environment,
  in a private temporary folder and within the limits; they are not otherwise sandboxed.
- **Reason:** These are maintained system packages; isolating them would need the container sandbox. Keeping them
  updated is the operator's job and is documented. Re-evaluate before any production server deployment.

### INT-005 · OCR quality limits (multi-column order, poor scans)

- **Priority:** P4 Optional · **Status:** Accepted risk · **Refs:** README "Quality"
- **What:** Multi-column pages follow tesseract's layout analysis; poor scans, small print and handwriting give
  errors. Uncertain words are marked and the runtime asks the reader to check important passages.
- **Reason:** Inherent to OCR; documented for users.

### INT-006 · Python dependencies not watched by Dependabot

- **Priority:** P4 Optional · **Status:** Accepted risk · **Refs:** `.github/dependabot.yml`, `.github/workflows/ci.yml`
- **What:** Dependabot updates only GitHub Actions; the private Nodestro dependencies are pinned by Git commit.
- **Reason:** Dependabot cannot read the private Git URLs; pins move with the platform's pin cascade, and the blocking
  `pip-audit` step in CI catches known vulnerabilities.

## Cross-repository dependencies

| This repo item | Other repo | Other item | Relation |
|---|---|---|---|
| INT-001 | nodestro-runtime | pointer in its cross-repo table | The bound may belong where the runtime calls OCR. |
| INT-007 | all component repositories | `NODESTRO_READ` CI change (api #50, sdk #47, runtime #75, server #25, desktop #17, studio #85) | Same change everywhere |

## Maintaining this file

- Add an entry when work is identified but not done in the current PR. Use the next free ID; IDs are never reused.
- Link a GitHub issue for anything concrete enough to be picked up; keep details in the issue, not here.
- When an item is finished, delete its entry in the PR that completes it and mention the ID in the PR description.
  Git history is the record; do not keep ticked checklists.
- Accepted risks stay listed with their reason until the risk is removed or re-evaluated.
- Re-review the whole file before each release and update the "Last full review" line.
- Security issues that are not yet fixed are described only in general terms here. Report details privately
  (GitHub private vulnerability reporting), never in this file or in public issues.
