# TODO: nodestro-integrations

> Open work for this repository: release blockers, known bugs, security follow-ups, technical debt and planned improvements.
> GitHub issues are the source of truth for details; this file is the entry point and summary.
>
> **Last full review:** 2026-11-06 against master at a0018e0 (TODO abatement round)

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
is the accepted risk that the OCR programs run unsandboxed (bounded in memory on Linux and in parallel documents
since round 4) and documented limits of OCR itself.

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

None known.

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

### INT-007 · OCR discovery is refused on Windows and on unclosed interpreter directories (runtime R1)

- **Priority:** P3 Low · **Status:** Open · **Refs:** nodestro-runtime PR #226 (`docs/extension-isolation.md`,
  "Trust boundary of the host import (R1)"), this repository's CI step "Close the interpreter directories"
- **What:** The runtime now imports this package as a trusted host integration only when it is installed next to
  `nodestro_runtime` and the import path is closed (no user site, no entry writable by another user). Windows has no
  such check yet, so the trusted import is locked there and OCR is unavailable. A machine or CI runner with a
  writable interpreter prefix or an existing `~/.local` user site on the path is refused the same way; CI closes the
  runner's interpreter directories first.
- **Decided 2026-11-27 (owner, option b):** the lock on Windows is the intended behavior while the trust assumptions
  cannot be proven there. The Windows real-OCR test asserts the refusal (reason, no import, no OCR text).
- **Open:** an ACL check of the import path on Windows in the runtime; then lift the lock and restore the Windows
  expectation of `test_real_ocr_through_knowledge_and_run_inputs`. Not a release blocker: no Windows desktop is built.
- **Review 2026-11-27:** M2 done (programs only from closed `PATH` folders, no `LD_*`/`DYLD_*`; Windows does not
  check them, as above). L5: the CI step "The runtime discovers the installed integration" (wheel job) proves only
  that a normal wheel install next to the runtime is discovered and imported from its verified files (R2's path);
  it does not prove R1. R1 is covered by the runtime's `tests/test_trusted_integrations.py` (forged copies, foreign
  `RECORD`s, real pip, open import paths) and, end to end, by the Windows refusal assertion of the real-OCR test.
  On macOS, Homebrew folders writable by the `admin` group make OCR find no program until `chmod g-w` (README).
- **Re-review 2026-11-27 (runtime N1 to N5):** the runtime accepts only allowlisted `.pth` files (setuptools'
  `distutils-precedence.pth`), so an environment with an editable install, a uv or virtualenv venv
  (`_virtualenv.pth`), coverage or pytest-cov refuses the trusted import and OCR is unavailable there. This
  repository's CI installs the package as a wheel into the runner's interpreter or a `python -m venv`, without such
  files; the studio's components jobs run this suite with the studio installed as a wheel.
- **Third review 2026-11-27 (runtime NEW-1, NEW-2):** a file named by two distributions' `RECORD`s and a loaded or
  importable `sitecustomize`/`usercustomize` also refuse the trusted import. A Python that ships a `sitecustomize`
  (some distribution and sandbox builds) has no OCR through the runtime; the hosted runners' Pythons have none.

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
  exhaustion more than code execution.
- **Hardened 2026-11-07:** on Linux every program call starts with an address space limit (`RLIMIT_AS`, 2 GiB,
  `NODESTRO_OCR_PROGRAM_BYTES`), and one process recognizes at most two documents at a time (`NODESTRO_OCR_PARALLEL`;
  INT-001 is done). macOS does not enforce `RLIMIT_AS` and Windows has no such limit, so there only the per-document
  bounds apply. What stays accepted: the programs parse untrusted PDFs with the user's rights and are not isolated.
  Run OCR in the container sandbox if a server deployment needs more than that.

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
| (done 2026-11-20, W0-1) | nodestro-api, nodestro-studio | nodestro-api `scripts/studio_lock.sh` (same copy) | A master push of a merge commit reads the paired studio branch's lock while that branch is still ahead of the studio master (lock lag), else the master lock; `test_studio_lock.py` (curl stub). Keep the copies identical |
| (in review 2026-11-20, Welle 1) | nodestro-api, nodestro-sdk, nodestro-runtime | `scripts/studio_lock.sh` (same copy), `GH_TOKEN` on each lock step | The lock-lag compare request uses the read-only workflow token; an API error reads the master lock with a "Lock lag unknown" warning naming the HTTP status (404: branch gone, no warning). `tests/test_studio_lock.py`. Keep the copies identical |
| INT-007 (2026-11-27, N-22) | nodestro-runtime, nodestro-studio | runtime R1 trust boundary (PR #226), studio CI step "Close the interpreter directories" | OCR discovery depends on the runtime's location pin and closed import path; keep the CI steps in both repositories alike |
| (pointer) | nodestro-studio | ST-052 (Dependabot policy: weekly groups, cooldown, manual merge; auto-merge prerequisites) | Full entry in studio |

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
