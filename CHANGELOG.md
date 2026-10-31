# Changelog

## Unreleased

### Server settings and tenant secrets (2026-10-31)

- Pin of `nodestro-runtime` at `640ed68` (before: `4104176`): server settings validation, encrypted tenant provider
  keys and container calls without bind mounts (plan step PR-12); nothing changes in this package.

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
