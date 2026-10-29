"""Local OCR for scanned PDFs with poppler (``pdftoppm``) and ``tesseract``.

Moved unchanged from Nodestro 0.1 (``nodestro/documents.py``): the pages of a PDF are rendered
with ``pdftoppm`` and recognised with ``tesseract`` in the installed interface languages;
words recognised with low confidence are marked ``[?word]`` and counted. Both programs run on
this computer; no account, no network and no new Python library is needed. Without them the
engine reports itself unavailable and Nodestro shows OCR as not installed.

The engine is registered as the integration ``tesseract-ocr`` (entry point group
``nodestro.integrations``, see :mod:`nodestro_runtime.extensions`).
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile

from nodestro_runtime.documents import DocumentError, OcrResult
from nodestro_runtime.extensions import Integration

from . import __version__

_OCR_UNCERTAIN = 60.0


def ocr_available() -> bool:
    return shutil.which("tesseract") is not None and shutil.which("pdftoppm") is not None


def tesseract_languages() -> str:
    """Installed tesseract languages among Nodestro's UI languages (``deu+eng`` …)."""
    wanted = ["deu", "eng", "spa", "fra", "por", "ita"]
    try:
        listed = subprocess.run(
            ["tesseract", "--list-langs"], capture_output=True, text=True, timeout=20, check=False
        ).stdout.split()
    except (OSError, subprocess.TimeoutExpired):
        return "eng"
    found = [code for code in wanted if code in listed]
    return "+".join(found) or "eng"


def parse_tsv(tsv: str) -> tuple[str, int, int]:
    """Text from tesseract's TSV output with uncertain words marked ``[?word]``."""
    lines: dict[tuple[str, str, str, str], list[str]] = {}
    uncertain = words = 0
    for row in tsv.splitlines()[1:]:
        parts = row.split("\t")
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
        lines.setdefault((parts[1], parts[2], parts[3], parts[4]), []).append(word)
    text = "\n".join(" ".join(items) for items in lines.values())
    return text, uncertain, words


def run_ocr(data: bytes, name: str) -> OcrResult:
    """Recognise the text of a scanned PDF with poppler and tesseract (both local)."""
    if not ocr_available():
        raise DocumentError("document.ocr_unavailable", "OCR needs tesseract and pdftoppm installed")
    language = tesseract_languages()
    with tempfile.TemporaryDirectory(prefix="nodestro-ocr-") as directory:
        folder = Path(directory)
        source = folder / "input.pdf"
        source.write_bytes(data)
        try:
            subprocess.run(
                ["pdftoppm", "-r", "200", "-l", "50", "-png", str(source), str(folder / "page")],
                capture_output=True,
                timeout=300,
                check=True,
            )
        except (OSError, subprocess.SubprocessError):
            raise DocumentError("document.ocr_failed", f"{name}: the pages could not be rendered", name=name) from None
        pages = sorted(folder.glob("page*.png"))
        texts: list[str] = []
        uncertain = words = 0
        for number, page in enumerate(pages, start=1):
            try:
                tsv = subprocess.run(
                    ["tesseract", str(page), "stdout", "-l", language, "tsv"],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    check=True,
                ).stdout
            except (OSError, subprocess.SubprocessError):
                raise DocumentError("document.ocr_failed", f"{name}: page {number} failed", name=name) from None
            text, page_uncertain, page_words = parse_tsv(tsv)
            uncertain += page_uncertain
            words += page_words
            texts.append(f"## Page {number}\n\n{text}")
    return OcrResult(text="\n\n".join(texts), pages=len(pages), uncertain=uncertain, words=words, language=language)


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
        description="Local OCR of scanned PDFs with poppler and tesseract",
    )
