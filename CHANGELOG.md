# Changelog

## Unreleased

### Runtime pin: PostgreSQL read performance (2026-11-01)

- Pin of `nodestro-runtime` at `d141b8f` (before: `6eacec1`): the PostgreSQL store checks pooled connections only
  after they sat idle, retries reads on a lost connection, and its find indexes are partial (migration 0006).

### Runtime pin: backend audit fixes (2026-11-01)

- Pin of `nodestro-runtime` at `6eacec1` (before: `58cec5c`): fixes from the internal backend audit (bounded sandbox
  output, run integrity across processes, PostgreSQL connection pool, resume side-effect journal, provider failure
  codes; see the runtime CHANGELOG).

### Runtime pin: MCP re-review fixes R-1, R-2 (2026-11-01)

- Pin of `nodestro-runtime` at `58cec5c` (before: `f71086a`): a per-call approval also covers the tool's
  classification (a reclassification while a call waits makes the approval stale), and the tool name `memory` is
  reserved for the agent's memory tool.

### Runtime pin: MCP security fixes (2026-11-01)

- Pin of `nodestro-runtime` at `f71086a` (before: `c86781b`): fixes from the independent MCP review (per-call
  approvals hold in agent tests and the tool panel, no credentials in server addresses, response size limit) and the
  offline worker fix F5. No change in this package.

### Runtime pin: one continue of a paused run across processes (2026-11-01)

- Pin of `nodestro-runtime` at `c86781b` (before: `26c86ef`): a paused run is queued again by compare-and-set, so a
  decision and the deadline sweeps of several workers continue it exactly once. No change in this package.

### Runtime pin: runs paused at a tool approval (2026-11-01)

- Pin of `nodestro-runtime` at `26c86ef` (before: `6ac4ae3`): with the new switch
  `NODESTRO_TOOL_APPROVAL_CHECKPOINTS` (default off) a tool call that waits for a person pauses the run and
  continues it after the decision without asking the model again (AO M6b). No change in this package.

### Runtime pin: security fix for stale tools in server workers (2026-11-01)

- Pin of `nodestro-runtime` at `6ac4ae3` (before: `081705d`): every process sees tool changes and deletions made by
  another process, and a tool an agent holds refuses to run once its version is no longer the current approved one
  (S-2 pilot finding F1). No change in this package.

### Runtime pin: dynamic teams and approvals inside teams (2026-11-01)

- Pin of `nodestro-runtime` at `081705d` (before: `1bc3924`): orchestrators wait for approvals inside their teams
  instead of cancelling them, and can assemble their team, run teams in parallel and fill team forms (AO M6b, all
  opt-in). Orchestration records are protocol version 2. No change in this package.

### Runtime pin: MCP resources (2026-11-01)

- Pin of `nodestro-runtime` at `1bc3924` (before: `2d55242`): a connected MCP service's listed resources can be read
  through one approved tool, `resources/read` (MCP WP-10). No change in this package.

### Runtime pin: warnings before unattended starts (2026-11-01)

- Pin of `nodestro-runtime` at `2d55242` (before: `a13f894`): `tool_preflight.unattended_tool_issues` warns before a
  schedule, batch, test series or published API whose tool calls the per-call approval rules would refuse (S-2, R1).
  No change in this package.

### Runtime pin: legacy exemption fix (2026-10-31)

- Pin of `nodestro-runtime` at `a13f894` (before: `40e04b4`): the per-call tool approval activation step runs once,
  and removed tools lose their legacy exemption (S-2 security acceptance), plus MCP tools in releases (#51).
  Nothing changes in this package.

### Runtime pin: teams and orchestrator (2026-10-31)

- Pin of `nodestro-runtime` at `40e04b4` (before: `0aee6a9`): output contracts and capabilities (Adaptive
  Orchestration M3), the orchestrator node (M4) and pool selection by capability (M5), stdio MCP servers (#50).
  Nothing changes in this package.

### Runtime pin (2026-10-31)

- Pin of `nodestro-runtime` at `0aee6a9` (before: `8597544`), the platform's current runtime (per-call tool
  approvals S-2, MCP write gate and OAuth, budget reservations, run limits). Nothing changes in this package.

### Sandbox gateway security fixes (2026-10-31)

- Pin of `nodestro-runtime` at `8597544` (before: `b6b757b`): the sandbox gateway of Nodestro Local Docker parses
  request heads strictly (request smuggling fix, runtime PR #33) and refuses to start sandboxes when the Docker daemon
  cannot enforce resource limits (runtime PR #37). It also carries the tool approval work of runtime PRs #30 to #36.
  Nothing changes in this package.

### Flow kernel, loop connections and MCP tool provenance (2026-10-31)

- Pin of `nodestro-runtime` at `b6b757b` (before: `78d2899`): the engine runs on the `orkexa.flow` kernel (Orkexa
  `456b92f`) and supports loop connections with mandatory limits; MCP tools carry their provenance. Nothing changes
  in this package.

### Nodestro Local Docker and MCP tools (2026-10-31)

- Pin of `nodestro-runtime` at `78d2899` (before: `d2cb987`): the `local-container` profile and the sandbox gateway
  of Nodestro Local Docker, and the runtime side of MCP tools; nothing changes in this package.

### Strict price-mode error codes (2026-10-31)

- Pin of `nodestro-runtime` at `d2cb987` (before: `45e7774`): strict price-mode refusals get their own error codes;
  nothing changes in this package.

### Built-in Linux sandbox (2026-10-31)

- Pin of `nodestro-runtime` at `45e7774` (before: `272e2f6`): the built-in Linux sandbox (Landlock, seccomp and
  resource limits) that the desktop uses automatically for AI-generated tools; nothing changes in this package.

### Model pricing and cost reconciliation (2026-10-31)

- Pin of `nodestro-runtime` at `272e2f6` (before: `c6bc2e5`): the workspace's price catalog, automatic price
  updates, costs priced with the catalog and the strict price mode, and the comparison with the providers' bills
  (PRICING-1); nothing changes in this package.

### Runs stored as running (2026-10-31)

- Pin of `nodestro-runtime` at `c6bc2e5` (before: `51f0a6c`): a run executed by a worker is stored as `running`
  when it starts (plan step PR-12); nothing changes in this package.

### Server settings and tenant secrets (2026-10-31)

- Pin of `nodestro-runtime` at `51f0a6c` (before: `4104176`): server settings validation, encrypted tenant provider
  keys, container calls without bind mounts and an allowlist for tenant model endpoints (plan step PR-12); nothing
  changes in this package.

### Libraries in the Docker sandbox (2026-10-31)

- Pin of `nodestro-runtime` at `4104176` (before: `3a052d1`): an approved Python environment becomes a container image
  in the Docker sandbox (plan step PR-11); nothing changes in this package.

### Jobs and workers (2026-10-31)

- Pin of `nodestro-runtime` at `3a052d1` (before: `8eea1ea`): the job queue, run workers, reaper and run events of
  the server profile (plan step PR-10); nothing changes for the desktop.

### Server storage and identity (2026-10-31)

- Pin of `nodestro-runtime` at `8eea1ea` (before: `d6e75b7`): PostgreSQL storage, tenant workspaces and identity
  records for the server profile (plan steps PR-7 to PR-9); nothing changes for the desktop.

### Sandbox policy (2026-10-31)

- Pin of `nodestro-runtime` at `d6e75b7` (before: `e90c205`): the runtime with the sandbox policy and trust
  classes for tool code (ADR-0006).

### Storage seams (2026-10-31)

- Pin of `nodestro-runtime` at `e90c205` (before: `8ea9a5c`): the runtime with the `DocumentStore` protocol
  (`Store` stays as an alias). No code change here.

### Operating profiles (2026-10-31)

- Pin of `nodestro-runtime` at `8ea9a5c` (before: `ad75859`), the runtime with operating profiles that
  `nodestro-api` and `nodestro-examples` pin. No code change; integrations do not use the profile.

### Platform integration (2026-10-30)

- Pin of `nodestro-runtime` at `ad75859` (before: `b1bae2a`), the runtime the other components are tested with. Its OCR
  note now says "1 page" instead of "1 pages"; the OCR test expects the singular.

### OCR

- Resource limits for untrusted PDFs: each page is rendered on its own, at a lower resolution when 200 dpi would
  exceed 40 million pixels (a 25 KB PDF with a 120-inch page used to take 48 s and about 1.7 GB in `pdftoppm`), and
  the whole document has a time limit of 900 s next to the 300 s per program call (before: up to 300 s for each of
  50 pages).
- A page that `pdftoppm` does not render completely now fails the OCR instead of appearing as an empty page: poppler
  writes a 1x1 image and reports success for pages it cannot allocate, and missing or broken page images were
  ignored.
- `pdfinfo` is now required: it gives the page count and the page sizes. Without it a document longer than 50 pages
  could be cut short without the note about the missing pages. The crop box is rendered, as PDF viewers show it.
- Language: the first page is read in each installed Nodestro language and the most confident one is put first.
  With all six in a fixed order tesseract lost accents (`Albaran nümero` instead of `Albarán número`, `quantita`,
  `recue`, `vocés`).
- Rotated pages: tesseract runs with orientation detection (`--psm 1`); pages scanned sideways or upside down came
  out as unreadable text.
- Paragraphs are separated by an empty line; lines, `[?word]` marks and `## Page N` headings are unchanged.
- OCR is reported as unavailable when tesseract has none of the six languages or cannot list them, instead of
  falling back to `eng` that may not be installed; `tesseract_languages()` returns an empty string then.
- The programs get a reduced environment without API keys, tokens and other secrets of the calling process,
  `OMP_THREAD_LIMIT=1` unless set, and are started from their full paths in the temporary folder.
- Program output is decoded as UTF-8 (on Windows it was decoded with the ANSI code page, which garbled umlauts and
  accents).
- Clearer errors with the same codes: damaged, password-protected and empty PDFs, the page that failed, timeouts,
  no temporary space (an `OSError` used to escape as an unexpected error).
- The integration states contract 1 explicitly instead of taking the runtime's current version, so a future runtime
  with another contract refuses it instead of calling it.
- For a PDF with more than 50 pages, the recognized text says how many pages were recognized and how many the
  document has (`pdfinfo` from poppler), instead of silently leaving out the rest.

### Project

- Documentation, CI and all developer-facing text in English; the README covers installation per system, limits,
  quality, errors, security and writing an integration.
- Tests: simulated programs for page order, the page limit, failures, timeouts, temporary files, file names and the
  environment; real OCR of a rotated Spanish scan, damaged PDFs and the whole path through knowledge and run input
  files. CI installs all six languages and fails instead of skipping the real OCR tests.
- CI: the token `NODESTRO_READ` is only in the environment of the install steps (no global Git configuration),
  the tool versions are logged, the wheel is checked for its entry point after a clean installation.
- `nodestro-runtime` pinned to the current version; current CI actions (Node 24); checkout without stored
  credentials.

## 0.2.0 (2026-10-29)

- First version as a repository of its own: split from `nodestro` 0.1.0 (commit 15e2076, now `nodestro-legacy`)
  without new features or behavior changes. The origin of every file: PROVENANCE.md.
- Dependencies pinned to exact commits (orkexa `cbf6df3d6f727b96924f1ae66e60b469eeef58e6`); the tested combination
  is recorded in `nodestro-studio/platform/versions.json`.
- CI with the repository secret `NODESTRO_READ`.
