# Changelog

## Unreleased

- README: extension contract 2 (nodestro-runtime ADR-0001, NAL-A1): `(ToolSpec, Tool)` pairs, author-stated
  capability shown only, limits applied. The integrations here keep contract 1; no code change.

- Pins nodestro-runtime 979c11c (runtime #150 and #145, tests only: botocore 1.44's default retry mode in the Bedrock
  test, rollback snapshot tools for TABRION QA-13), so the platform components job is green again.
- Pins nodestro-runtime 2b8690e (runtime #148, RT-067: agent steps answer at the tool-round limit and after a
  thinking overflow instead of failing, `NodeRun.limits_handled`, `IncompleteResponseError` causes; orkexa 840add4
  (orkexa #71): on Ollama only the latest thinking is sent back, the root cause of the local max_tokens and tool-loop
  failures since 2026-11-06).
- Pins nodestro-runtime f5da80d (runtime #143: TABRION JQ-1..JQ-3, RT2-03, writes are never repeated after a lost connection; no schema change, no public signature change; Axentra 9c4666f with the B-06-1 log redaction, axentra #61). Pin wave W7 (TABRION JQ-4).
- Pins nodestro-runtime 81b0f55 (runtime #140: MUP-ONA B6, the knowledge base, file store and memory run on orkexa's `orkexa.backends.postgres` (orkexa 792a041); `pg_generic` and `sqlcheck_rules` are removed, the tenant SQL check runs on `orkexa.testing.sqlcheck`, and a start check refuses a deviating knowledge schema with `storage.schema_mismatch`; no DDL, no schema change).
- Pins nodestro-runtime df4aeb3 (runtime #139: the B4 SQL rendering tests skip without psycopg, for the desktop profile; behavior unchanged).
- Pins nodestro-runtime 76f9cb2 (runtime #137/#138: MUP-ONA B4, the tenant SQL rule engine as `sqlcheck_rules`, the generic PostgreSQL part `pg_generic` with a statement catalog and a partition guard (`partition.missing`); behavior unchanged).
- Pins nodestro-runtime d9c3d6e (runtime #136: MUP-ONA B2, orkexa 028faa1 with the SQLite backends in `orkexa.backends.sqlite`; #135 Axentra 60d83b3 with the A8 fixes; #134 PostgreSQL reindex switch under load; #133 real-daemon image tests).
- Pins nodestro-runtime 099f4d4 (runtime #130/#131/#132: MUP-ONA B1 orkexa conformance suite with orkexa b3d6fae, B3 PostgreSQL ranking drift fixes and bounded reindex switch, new error `agent.VectorError` and query limit `query.too_long`; sandbox gateway keeps attached streams alive).
- At most two documents per process are recognized at the same time (`NODESTRO_OCR_PARALLEL`, 1 to 64); others
  wait within their 900 s. On Linux each poppler and tesseract call starts with a 2 GiB address space limit
  (`RLIMIT_AS`, `NODESTRO_OCR_PROGRAM_BYTES`); a program that needs more fails the page (INT-001, INT-004).
- Pins nodestro-runtime de56875 (runtime #127: MUP-ONA A1, PDF text read in a separate process with page, character, time and memory limits, new code `document.too_complex`; B0, one Axentra commit for every extra; orkexa f89102c).
- Pins nodestro-runtime f26dac4 (runtime #128: the legacy fixture restore test skips without psycopg instead of erroring; includes MUP-ONA A11 runtime #123; TODO abatement round 4).
- Pins nodestro-runtime 5f8c0f0 (runtime #126: a busy sandbox image build stays `checking` (LD-020), Bedrock region in usage, registry facts before a download, `pgvector_status()`; includes the price-table date fix of runtime #125; TODO abatement round 4).
- Pins nodestro-runtime b29b738 (runtime #121: semantic reindex as a server job, RT-046; TODO abatement round 3).
- CI runs the tests on Python 3.12 too, and the real-OCR tests on macOS (Homebrew) and Windows (Chocolatey, with
  the Nodestro languages from tessdata_fast at a pinned commit, SHA-256 checked) in a CI job that passed on both and is blocking (INT-002).
  The README says that a `TESSDATA_PREFIX` folder also needs tesseract's `configs/tsv`.
- Cheaper ways to find the main language were measured and rejected; the README "Limits" section records why
  (INT-003).
- Pin nodestro-runtime 57b40d2 (runtime #116: strict offline mode refuses cloud models outside runs too, orchestrator effort only where the model takes one (RT-004), expired budget decisions end a run `failed`, semantic index `unavailable` without sqlite-vec). Nothing changes in this package.
- Pin nodestro-runtime 40c8c06 (runtime #113, backend audit round 3: key-figure checks, event-loop safety, cancel of local model requests, `reindex_required`, catalog `license_source`; orkexa e9c2147, axentra 0a1d1cc). No change to this package.
- Pin nodestro-runtime c6f0240 (runtime #112: orkexa 22f2910, Ollama runtime for another platform than the host's, for the portable export). Nothing changes in this package.
- Pin nodestro-runtime 2f1de71 (runtime #108: checked key figures, `table_totals`; #109 and #110: orkexa 6e61862, local Ollama agents with a structured result call their tools and answer in the conversation's language; a calculator echo backs no checked value). Nothing changes in this package.
- Pin nodestro-runtime 7cb9b4b (runtime #107: a local judge answers without thinking in the CPU saving mode, longer
  request timeout for local model servers).
- Pin nodestro-runtime 3006ce0 (runtime #106: CPU saving mode, local model hints, `recommend(require=)`, evidence-weighted hybrid search).
- Pin nodestro-runtime 7b9f4f7 (local models, embeddings and semantic knowledge search, runtime #99, #101, #102;
  orkexa 9b06a5e, #42; 2026-11-03). Nothing changes in this package.
- A page above `MAX_PAGE_PIXELS` even at the lowest resolution (1 dpi, `MIN_DPI`) is refused with
  `document.ocr_failed` (`<name>: page N is too large to render`) instead of being rendered beyond the limit; the
  resolution also accounts for poppler rounding up to whole pixels (audit ORK2-05).
- Pin nodestro-runtime 140d479 (backend audit round 2, runtime #96: OPS2-01 migration backup lock, RT2-01..08, keyset run listing, budget request labels; orkexa bc8c4ed, #40; Axentra a872242; 2026-11-03). Nothing changes in this package.
- Pin nodestro-runtime bcfea7f (security review round 4 Lows R4-3 to R4-7, runtime #95; real-engine resolve tests
  and orkexa 0861c1b, #94; Axentra 2767a2e; 2026-11-02). Nothing changes in this package.
- Pin nodestro-runtime 96f14ef (static tenant SQL check round-3 gaps, #89; tool generation jobs stopped on tenant
  suspension, NF-1; Axentra f3ed8d2; runtime #93; 2026-11-02). Nothing changes in this package.
- Pin nodestro-runtime 958be1d (R-1 source builds only on the desktop and R-5 container shape checks, runtime #90; MCP
  container deadline 15 minutes, #91; adopting AI-generated tools on the desktop, R-4, #92; 2026-11-02). Nothing
  changes in this package.
- Pin nodestro-runtime 51262a2 (Python 3.11 minimum, orkexa dec66eb; runtime #88; 2026-11-02).
- Python 3.11 is now the minimum (3.10 reached end of life in October 2026): `requires-python`, classifiers, ruff
  `py311`, mypy 3.11, CI matrix 3.11/3.13.
- Pin nodestro-runtime 0369132 (security re-review Lows, Axentra 024da57; runtime #87; 2026-11-02). Nothing changes
  in this package.
- Pin nodestro-runtime 50edcf7 (Axentra migration completion: security review fixes, M12 cleanup, Axentra a8ea5d5;
  runtime #86; 2026-11-02). Nothing changes in this package.
- Pin nodestro-runtime bf9af7d (Docker sandbox security review fixes, runtime #85; 2026-11-02). Nothing changes in
  this package.
- Pin nodestro-runtime 64895e6 (run budget decisions, BUDGET-1, runtime #84; 2026-11-02): an attended run whose next
  model request does not fit its budget pauses for a decision instead of failing. Nothing changes in this repository.
- Pin nodestro-runtime b608f90 (Docker-first sandbox plan R1-R4, runtime #83; 2026-11-02). Nothing changes in this
  package.
- Pin nodestro-runtime 95dbdfa (Axentra platform services in the server profile, off by default; runtime #79;
  2026-11-02). Nothing changes here: this package never imports Axentra.
- Pin nodestro-runtime 7fd8761 (automatic sandbox selection, runtime #78; 2026-11-02).

### Runtime pin: live run chat fix (LRC-1, 2026-11-01)

- Pins `nodestro-runtime` `a42b672` (before `d20991f`): questions to a team leader are answered with any provider.

### Runtime pin: live run chat and steering (LRC-1, 2026-11-01)

- Pins `nodestro-runtime` `d20991f` (master merge of runtime #67; before `ac96c6f`): `nodestro_runtime.run_chat` (questions and instructions to
  an orchestrator while it runs). Nothing else changes here.

### Runtime pin: Amazon Bedrock (branch only, 2026-11-01)

- Pin of `nodestro-runtime` at `ac96c6f` (before: `d141b8f`) on the Bedrock branch, so the platform's pins agree
  (the runtime adds the `bedrock` provider; nothing here changes).

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
