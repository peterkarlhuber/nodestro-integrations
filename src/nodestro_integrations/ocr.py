"""Local OCR for scanned PDFs with poppler (``pdfinfo``, ``pdftoppm``) and ``tesseract``.

Moved from Nodestro 0.1 (``nodestro/documents.py``). ``pdfinfo`` reads the page count and the
page sizes, ``pdftoppm`` renders one page at a time to PNG, and ``tesseract`` recognizes it in
the installed Nodestro languages. Words recognized with low confidence are marked ``[?word]``
and counted. All programs run on this computer with a reduced environment (no API keys or
other secrets of the calling process); no account, no network and no extra Python library is
needed. Without the programs or their language data the engine reports itself unavailable and
Nodestro shows OCR as not installed.

Limits that keep an untrusted PDF from exhausting the computer: at most :data:`MAX_PAGES`
pages, at most :data:`MAX_PAGE_PIXELS` pixels per rendered page (larger pages are rendered at
a lower resolution than :data:`DPI`), a timeout per program call and :data:`MAX_SECONDS` for
the whole document.

The engine is registered as the integration ``tesseract-ocr`` (entry point group
``nodestro.integrations``, see :mod:`nodestro_runtime.extensions`).
"""

from __future__ import annotations

import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

from nodestro_runtime.documents import DocumentError, OcrResult
from nodestro_runtime.extensions import Integration

from . import __version__

_OCR_UNCERTAIN = 60.0
#: Pages recognized at most per document (rendering and recognition take seconds per page).
MAX_PAGES = 50
#: Rendering resolution; enough for body text, and the resolution tesseract is trained for.
DPI = 200
#: Pixels of one rendered page at most (A1 fits at 200 dpi); larger pages get a lower resolution.
MAX_PAGE_PIXELS = 40_000_000
#: Seconds one program call may take.
STEP_SECONDS = 300
#: Seconds the whole document may take.
MAX_SECONDS = 900
#: Tesseract language codes of Nodestro's six languages, in the default order.
LANGUAGES = ("deu", "eng", "spa", "fra", "por", "ita")

#: Environment variables the programs get; everything else (API keys, tokens, credentials) stays out.
_ENV_NAMES = frozenset(
    {
        # Finding programs, libraries, language data, fonts and temporary files.
        "PATH",
        "HOME",
        "TMPDIR",
        "TEMP",
        "TMP",
        "TESSDATA_PREFIX",
        "LD_LIBRARY_PATH",
        "DYLD_LIBRARY_PATH",
        "DYLD_FALLBACK_LIBRARY_PATH",
        "FONTCONFIG_FILE",
        "FONTCONFIG_PATH",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_DATA_DIRS",
        # Locale and threads.
        "LANG",
        "LANGUAGE",
        "TZ",
        "OMP_THREAD_LIMIT",
        "OMP_NUM_THREADS",
        # Windows.
        "SYSTEMROOT",
        "WINDIR",
        "PATHEXT",
        "COMSPEC",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "PROGRAMDATA",
        "NUMBER_OF_PROCESSORS",
    }
)
_PAGE_SIZE = re.compile(r"^Page\s+(\d+)\s+size:\s+([0-9.]+)\s+x\s+([0-9.]+)\s+pts", re.MULTILINE)
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def program_environment() -> dict[str, str]:
    """The environment of the OCR programs: the variables they need, nothing else.

    ``OMP_THREAD_LIMIT`` defaults to 1, so that several documents recognized at the same time
    do not each claim every core (tesseract is not faster with more threads on one page).
    """
    environment = {
        name: value for name, value in os.environ.items() if name.upper() in _ENV_NAMES or name.startswith("LC_")
    }
    environment.setdefault("OMP_THREAD_LIMIT", "1")
    return environment


def _programs() -> dict[str, str] | None:
    """The full paths of the programs (``None`` when one is missing)."""
    found = {name: shutil.which(name) for name in ("tesseract", "pdftoppm", "pdfinfo")}
    return {name: path for name, path in found.items() if path is not None} if all(found.values()) else None


def _run(command: list[str], deadline: float, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a program without a shell; raises :class:`subprocess.TimeoutExpired` past the deadline.

    On a timeout :func:`subprocess.run` kills the program before raising.
    """
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise subprocess.TimeoutExpired(command, 0)
    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=min(STEP_SECONDS, remaining),
        check=False,
        env=program_environment(),
        cwd=cwd,
        stdin=subprocess.DEVNULL,
    )


def _languages(tesseract: str) -> list[str]:
    try:
        listed = _run([tesseract, "--list-langs"], time.monotonic() + 20)
    except (OSError, subprocess.SubprocessError):
        return []
    if listed.returncode != 0:
        return []
    # The first line names the folder ("List of available languages in ..."), then one code per line.
    installed = {line.strip() for line in listed.stdout.splitlines()[1:]}
    return [code for code in LANGUAGES if code in installed]


def tesseract_languages() -> str:
    """Installed tesseract languages among Nodestro's languages (``deu+eng`` …).

    Empty when tesseract is missing, cannot list its languages or has none of them.
    """
    tesseract = shutil.which("tesseract")
    return "+".join(_languages(tesseract)) if tesseract is not None else ""


def ocr_available() -> bool:
    """Whether OCR can run: tesseract, pdftoppm and pdfinfo are installed and so is one of the languages."""
    programs = _programs()
    return programs is not None and bool(_languages(programs["tesseract"]))


def _pdf_info(pdfinfo: str, source: Path, name: str, deadline: float) -> tuple[int, dict[int, tuple[float, float]]]:
    """The page count and the sizes in points of the first :data:`MAX_PAGES` pages."""
    try:
        info = _run([pdfinfo, "-f", "1", "-l", str(MAX_PAGES), source.name], deadline, cwd=source.parent)
    except subprocess.TimeoutExpired:
        raise DocumentError("document.ocr_failed", f"{name}: reading the PDF timed out", name=name) from None
    except (OSError, subprocess.SubprocessError):
        raise DocumentError("document.ocr_failed", f"{name}: pdfinfo could not be run", name=name) from None
    if info.returncode != 0:
        if "password" in info.stderr.lower():
            raise DocumentError("document.ocr_failed", f"{name}: the PDF is password-protected", name=name)
        raise DocumentError("document.ocr_failed", f"{name}: the PDF is damaged or not a PDF", name=name)
    pages: int | None = None
    for line in info.stdout.splitlines():
        key, _, value = line.partition(":")
        if key.strip() == "Pages" and value.strip().isdigit():
            pages = int(value.strip())
    if pages is None:
        raise DocumentError("document.ocr_failed", f"{name}: the page count could not be read", name=name)
    sizes = {int(number): (float(width), float(height)) for number, width, height in _PAGE_SIZE.findall(info.stdout)}
    return pages, sizes


def page_count(source: Path) -> int | None:
    """The number of pages from poppler's ``pdfinfo`` (``None`` when it is missing or fails)."""
    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo is None:
        return None
    try:
        return _pdf_info(pdfinfo, source, source.name, time.monotonic() + 60)[0]
    except DocumentError:
        return None


def _dpi(width: float, height: float) -> int:
    """The resolution for a page of ``width`` x ``height`` points: :data:`DPI` within :data:`MAX_PAGE_PIXELS`."""
    square_inches = (width / 72) * (height / 72)
    if square_inches <= 0:
        return DPI
    return max(1, min(DPI, int(math.sqrt(MAX_PAGE_PIXELS / square_inches))))


def _png_size(path: Path) -> tuple[int, int] | None:
    """Width and height from a PNG header (``None``: missing or not a PNG)."""
    try:
        with path.open("rb") as file:
            header = file.read(24)
    except OSError:
        return None
    if len(header) < 24 or not header.startswith(_PNG_SIGNATURE) or header[12:16] != b"IHDR":
        return None
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


def _rendered(path: Path, width: float, height: float, dpi: int) -> bool:
    """Whether ``path`` is the whole page (poppler writes a 1x1 image for pages it cannot allocate)."""
    size = _png_size(path)
    if size is None:
        return False
    expected = (math.ceil(width * dpi / 72), math.ceil(height * dpi / 72))
    return any(abs(size[0] - wide) <= 2 and abs(size[1] - high) <= 2 for wide, high in (expected, expected[::-1]))


def parse_tsv(tsv: str) -> tuple[str, int, int]:
    """Text from tesseract's TSV output with uncertain words marked ``[?word]``.

    Lines keep tesseract's reading order; paragraphs are separated by an empty line.
    Returns the text, the number of uncertain words and the number of words.
    """
    paragraphs: dict[tuple[str, str, str], dict[str, list[str]]] = {}
    uncertain = words = 0
    for row in tsv.splitlines():
        parts = row.split("\t")
        # Level 5 rows are words; the header and the page, block, paragraph and line rows are skipped.
        if len(parts) < 12 or parts[0] != "5":
            continue
        word = parts[11].strip()
        if not word:
            continue
        try:
            confidence = float(parts[10])
        except ValueError:
            confidence = -1.0
        words += 1
        if 0 <= confidence < _OCR_UNCERTAIN:
            uncertain += 1
            word = f"[?{word}]"
        paragraphs.setdefault((parts[1], parts[2], parts[3]), {}).setdefault(parts[4], []).append(word)
    text = "\n\n".join("\n".join(" ".join(line) for line in lines.values()) for lines in paragraphs.values())
    return text, uncertain, words


def _confidence(tsv: str) -> float:
    """The mean confidence of the recognized words (0 without words)."""
    values: list[float] = []
    for row in tsv.splitlines():
        parts = row.split("\t")
        if len(parts) >= 12 and parts[0] == "5" and parts[11].strip():
            try:
                value = float(parts[10])
            except ValueError:
                continue
            if 0 <= value <= 100:
                values.append(value)
    return sum(values) / len(values) if values else 0.0


def run_ocr(data: bytes, name: str) -> OcrResult:
    """Recognize the text of a scanned PDF with poppler and tesseract (all local).

    Raises :class:`~nodestro_runtime.documents.DocumentError`: ``document.ocr_unavailable``
    without the programs or their languages, ``document.ocr_failed`` for a damaged or
    password-protected PDF, a page that cannot be rendered or recognized, or a timeout.
    """
    programs = _programs()
    if programs is None:
        raise DocumentError("document.ocr_unavailable", "OCR needs tesseract, pdftoppm and pdfinfo installed")
    languages = _languages(programs["tesseract"])
    if not languages:
        raise DocumentError(
            "document.ocr_unavailable",
            f"OCR needs tesseract language data for one of {', '.join(LANGUAGES)} (see tesseract --list-langs)",
        )
    deadline = time.monotonic() + MAX_SECONDS
    temporary: tempfile.TemporaryDirectory[str] | None = None
    try:
        # A folder of its own (readable by this user only), removed with everything in it at the end.
        temporary = tempfile.TemporaryDirectory(prefix="nodestro-ocr-")
        folder = Path(temporary.name)
        source = folder / "input.pdf"
        source.write_bytes(data)
    except OSError:
        if temporary is not None:
            temporary.cleanup()
        raise DocumentError("document.ocr_failed", f"{name}: no temporary space for the PDF", name=name) from None
    with temporary:
        total, sizes = _pdf_info(programs["pdfinfo"], source, name, deadline)
        count = min(total, MAX_PAGES)
        if count == 0:
            raise DocumentError("document.ocr_failed", f"{name}: the PDF has no pages", name=name)
        texts: list[str] = []
        uncertain = words = 0
        for number in range(1, count + 1):
            step = f"page {number}"
            try:
                if number not in sizes:
                    raise DocumentError("document.ocr_failed", f"{name}: {step} has no size", name=name)
                width, height = sizes[number]
                dpi = _dpi(width, height)
                image = folder / f"page-{number}.png"
                pages = ["-f", str(number), "-l", str(number), "-r", str(dpi), "-cropbox", "-singlefile"]
                rendered = _run([programs["pdftoppm"], *pages, "-png", source.name, image.stem], deadline, cwd=folder)
                if rendered.returncode != 0 or not _rendered(image, width, height, dpi):
                    raise DocumentError("document.ocr_failed", f"{name}: {step} could not be rendered", name=name)
                if number == 1 and len(languages) > 1:
                    # The main language first: tesseract favors the first language, and with all six
                    # in a fixed order it drops accents (número -> numero). Page 1 is read in each
                    # language alone; the most confident reading is kept and decides the order.
                    readings = [(code, _recognize(programs["tesseract"], image, code, deadline)) for code in languages]
                    best, tsv = max(readings, key=lambda reading: _confidence(reading[1]))
                    if _confidence(tsv) > 0:
                        languages = [best, *(code for code in languages if code != best)]
                else:
                    tsv = _recognize(programs["tesseract"], image, "+".join(languages), deadline)
                image.unlink()
            except subprocess.TimeoutExpired:
                raise DocumentError("document.ocr_failed", f"{name}: {step} timed out", name=name) from None
            except (OSError, subprocess.SubprocessError):
                raise DocumentError("document.ocr_failed", f"{name}: {step} failed", name=name) from None
            text, page_uncertain, page_words = parse_tsv(tsv)
            uncertain += page_uncertain
            words += page_words
            texts.append(f"## Page {number}\n\n{text}")
    if total > count:
        # Said in the text itself, so that neither the user nor an agent takes it for the whole document.
        texts.append(f"(Only the first {count} of {total} pages were recognised.)")
    return OcrResult(
        text="\n\n".join(texts), pages=count, uncertain=uncertain, words=words, language="+".join(languages)
    )


def _recognize(tesseract: str, image: Path, language: str, deadline: float) -> str:
    """Tesseract's TSV output for one page image (``--psm 1``: also reads rotated pages)."""
    result = _run([tesseract, image.name, "stdout", "-l", language, "--psm", "1", "tsv"], deadline, cwd=image.parent)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, result.args)
    return result.stdout


class TesseractOcr:
    """The :class:`~nodestro_runtime.extensions.OcrEngine` of the local programs."""

    name = "tesseract"

    def available(self) -> bool:
        return ocr_available()

    def recognize(self, data: bytes, name: str) -> OcrResult:
        return run_ocr(data, name)


def integration() -> Integration:
    """The entry point of this integration."""
    return Integration(
        name="tesseract-ocr",
        version=__version__,
        ocr=TesseractOcr(),
        # Stated, not defaulted: the default is the runtime's current contract, which would accept this
        # integration even after the contract changed.
        contract=1,
        description="Local OCR of scanned PDFs with poppler and tesseract",
    )
