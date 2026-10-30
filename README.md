# Nodestro Integrations

Optional extensions for [Nodestro](https://github.com/peterkarlhuber/nodestro-studio), built on the extension
contract of the [runtime](https://github.com/peterkarlhuber/nodestro-runtime) (`nodestro_runtime.extensions`,
contract 1). The studio installs this package; the runtime and the API work without it.

Part of the Nodestro platform; see
[PLATFORM.md](https://github.com/peterkarlhuber/nodestro-studio/blob/master/docs/PLATFORM.md) for the overview.

## Included

| Integration | Entry point | What it does |
| --- | --- | --- |
| `tesseract-ocr` | `nodestro_integrations.ocr:integration` | Local OCR of scanned PDFs (PDFs without a text layer) with poppler and tesseract, for knowledge files and run input files. |

## How the runtime finds it

Installing the package registers the entry point `tesseract-ocr` in the group `nodestro.integrations`.
`nodestro_runtime.extensions.discover()` loads it, and every `Workspace` (and with it the API and the studio) uses it.
Nothing is started and no network connection is opened: an integration is code the runtime calls.

- Package not installed: OCR is reported as unavailable; everything else works as before.
- Package installed, programs or language data missing: the integration is listed in
  `workspace.extensions.summary()`, but `workspace.settings().ocr_available` is `false` and scanned PDFs are stored
  without text.
- OCR is off by default; it runs only after the user turns it on (`ocr_enabled` in the workspace settings).
- `Workspace(data_dir, integrations=[])` uses no integrations; `integrations=[...]` uses exactly the given ones.

## Installation

The package is installed from Git, pinned to a commit, like the other Nodestro components (the studio does this
for you):

```bash
pip install "nodestro-integrations @ git+https://github.com/peterkarlhuber/nodestro-integrations.git@<commit>"
```

OCR also needs three programs on `PATH` and tesseract language data for at least one of Nodestro's languages:

| System | Command |
| --- | --- |
| Debian, Ubuntu (tested in CI) | `sudo apt-get install tesseract-ocr poppler-utils tesseract-ocr-deu tesseract-ocr-spa tesseract-ocr-fra tesseract-ocr-por tesseract-ocr-ita` |
| macOS (Homebrew, not tested in CI) | `brew install tesseract tesseract-lang poppler` |
| Windows (not tested) | tesseract from the [UB Mannheim builds](https://github.com/UB-Mannheim/tesseract/wiki) and poppler from [poppler-windows](https://github.com/oschwartz10612/poppler-windows); add both `bin` folders to `PATH`. |

The programs are `tesseract` (4 or newer; tested with 5.3), `pdftoppm` and `pdfinfo` (both from poppler). Check
with `tesseract --list-langs`: the languages used are `deu`, `eng`, `spa`, `fra`, `por` and `ita`, as far as they
are installed. `osd` (installed with tesseract on Debian, Ubuntu and Homebrew) lets tesseract turn pages that were
scanned sideways or upside down. `TESSDATA_PREFIX` points tesseract to another language data folder.

## The OCR

- Each page is rendered with `pdftoppm` at 200 dpi and recognized with `tesseract`; the text of each page follows a
  heading `## Page N`, paragraphs are separated by an empty line.
- Words recognized with a confidence below 60 % are marked `[?word]` and counted (`OcrResult.uncertain` of
  `OcrResult.words`). The runtime puts this count and a request to check important passages in front of the text.
- Language: the first page is read once in each installed language; the most confident reading decides the main
  language, which is put first for the remaining pages (`OcrResult.language`, for example `spa+deu+eng+fra+por+ita`).
  This keeps accents and special characters (`número`, `quantità`, `reçue`) that a fixed language order loses, and
  still reads documents that mix languages.
- At most 50 pages per document. For a longer document the text ends with
  `(Only the first 50 of N pages were recognised.)`, so neither a person nor an agent takes it for the whole document.
- Everything runs on this computer: no account, no network, no cloud service.

### Limits

These protect the computer from untrusted PDFs, including PDFs given directly to `TesseractOcr.recognize()`
without the runtime's upload checks:

| Limit | Value |
| --- | --- |
| Pages per document | 50 (`MAX_PAGES`) |
| Pixels per rendered page | 40 million (`MAX_PAGE_PIXELS`): A1 and smaller at 200 dpi, larger pages at a lower resolution |
| One program call | 300 s (`STEP_SECONDS`) |
| The whole document | 900 s (`MAX_SECONDS`) |
| Threads per tesseract call | 1 (`OMP_THREAD_LIMIT`, unless set), so parallel documents do not compete for every core |

Measured with tesseract 5.3 on one CPU core: about 1 s per A4 page, plus about 4 s per document for finding the
main language when all six languages are installed (about 1 s with two). The programs use about 150 MB for A4 pages
and up to about 700 MB for the largest pages.

### Quality

OCR makes mistakes, more so on poor scans, small print, handwriting, tables and unusual layouts. The confidence
marks show where tesseract was unsure; they do not prove that the other words are right. Multi-column pages are read
in the order tesseract's layout analysis finds, which is not always the reading order. Treat recognized text as
machine-generated and check important passages against the original.

### Errors

`recognize()` raises `nodestro_runtime.documents.DocumentError`:

| Code | When |
| --- | --- |
| `document.ocr_unavailable` | A program or the language data is missing. |
| `document.ocr_failed` | The PDF is damaged, not a PDF, password-protected or has no pages; a page cannot be rendered or recognized; a limit is exceeded. |

Messages name the file and the step (`scan.pdf: page 3 could not be rendered`) and never contain the output of the
programs. A valid PDF without recognizable text gives an empty text, not an error.

### Security and privacy

- The programs run without a shell, with fixed argument lists, from their full paths, in a temporary folder of
  their own (readable by the current user only) that is removed with all page images when the document is done or
  fails. The file name of the upload is used in messages only; the PDF is stored as `input.pdf`.
- They get a reduced environment: `PATH`, locale, temporary folders, `TESSDATA_PREFIX`, library and font settings
  and the variables Windows needs. API keys, tokens, proxy settings and other variables of the calling process are
  not passed on. This limits what a misbehaving program could leak; the programs still run with the rights of the
  current user, so a poppler or tesseract with a known vulnerability should be updated.
- The integration logs nothing and keeps no copy of a document; storing files and texts is the runtime's job.

## Writing an integration

An integration is a distribution with an entry point in the group `nodestro.integrations` that names an
`Integration` or a function returning one:

```toml
# pyproject.toml
[project.entry-points."nodestro.integrations"]
my-integration = "my_package:integration"
```

```python
from nodestro_runtime.extensions import Integration
from orkexa import Tool


@Tool
def word_count(text: str) -> int:
    """Count the words of a text.

    Args:
        text: The text to count.

    Returns:
        The number of words.
    """
    return len(text.split())


def integration() -> Integration:
    return Integration(
        name="my-integration",
        version="1.0.0",
        tools=[word_count],
        contract=1,  # the contract version this code was written for
        description="Counts words",
    )
```

- `tools` are trusted orkexa tools that run in the runtime's process and appear in the tool library like the
  built-in tools; tool names must be unique.
- `ocr` is an `OcrEngine`: a `name`, `available()` and `recognize(data, name)` returning an `OcrResult` or raising
  `DocumentError`. The runtime uses the first engine that is available.
- State `contract` explicitly: the default is the runtime's current version, so an integration that relies on it is
  never refused, even by a runtime whose contract it no longer fits.
- An integration that cannot be loaded is logged and left out; one written for another contract is refused. The
  runtime starts in either case.

## Development

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check . && mypy && pytest
```

Most tests simulate `pdfinfo`, `pdftoppm` and `tesseract` (one Python script plays all three) to cover page order,
the page limit, failures, timeouts, the environment and temporary files. The tests named `test_real_ocr_*` use the
real programs and the scans in `tests/data/`; they are skipped when the programs or languages are missing, except
with `NODESTRO_REQUIRE_REAL_OCR=1`, which CI sets so that they can never be skipped unnoticed.

CI needs the repository secret `NODESTRO_READ` (read access to orkexa and the Nodestro repositories); it is
available only to the steps that install the private dependencies.

## Provenance and license

The OCR comes from `backend/src/nodestro/documents.py` of `nodestro` 0.1 (15e2076); see
[PROVENANCE.md](PROVENANCE.md). MIT, see [LICENSE](LICENSE).
