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
a lower resolution than :data:`DPI`; a page above the limit even at :data:`MIN_DPI` is refused),
a timeout per program call and :data:`MAX_SECONDS` for the whole document. Per process, at most
:data:`MAX_PARALLEL` documents are recognized at the same time (others wait within their time limit), and on Linux
each program gets at most :data:`MAX_PROGRAM_BYTES` of address space (``RLIMIT_AS``).

The engine is registered as the integration ``tesseract-ocr`` (entry point group
``nodestro.integrations``, see :mod:`nodestro_runtime.extensions`).
"""

from __future__ import annotations

import csv
from importlib import metadata
import math
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import sysconfig
import tempfile
import threading
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
#: The lowest rendering resolution; a page above :data:`MAX_PAGE_PIXELS` even at this resolution is refused.
MIN_DPI = 1
#: Seconds one program call may take.
STEP_SECONDS = 300
#: Seconds the whole document may take.
MAX_SECONDS = 900
#: Documents recognized at the same time in one process (``NODESTRO_OCR_PARALLEL``, 1 to 64); the others wait,
#: and the wait counts against their :data:`MAX_SECONDS`. Each document needs up to about 700 MB (largest pages).
MAX_PARALLEL = 2
#: Address space one program call may use (``NODESTRO_OCR_PROGRAM_BYTES``, at least 256 MiB): ``RLIMIT_AS`` on POSIX
#: systems that enforce it (Linux); a program that needs more fails and the page is reported as failed.
MAX_PROGRAM_BYTES = 2 * 1024**3
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
    ``PATH`` holds only the folders the programs are looked up in (:func:`program_path`); no ``LD_*`` or ``DYLD_*``
    variable reaches them, so no other library is loaded into them (review M2).
    """
    environment = {
        name: value for name, value in os.environ.items() if name.upper() in _ENV_NAMES or name.startswith("LC_")
    }
    environment["PATH"] = os.pathsep.join(program_path())
    environment.setdefault("OMP_THREAD_LIMIT", "1")
    return environment


def program_owners() -> frozenset[int]:
    """The users a program folder, the program file and every parent may belong to: root only (owner decision
    2026-11-27). A folder of the current user (Homebrew's or conda's ``bin``) is refused: whatever runs as this user
    could replace a program there."""
    return frozenset({0})


def _status(path: Path) -> os.stat_result:
    return os.stat(path)


def _chain(real: Path) -> list[Path]:
    """The folders checked for ``real``: itself and every parent up to the root of the file system."""
    return [real, *real.parents]


def _unsafe(path: Path) -> bool:
    """Whether ``path`` is not administered by root alone: another owner than :func:`program_owners`, or writable by
    a group or by every user (no exception for sticky folders such as ``/tmp`` or for root's group)."""
    try:
        info = _status(path)
    except OSError:
        return True
    if info.st_uid not in program_owners():
        return True
    return bool(info.st_mode & (stat.S_IWGRP | stat.S_IWOTH))


def _chain_closed(real: Path) -> bool:
    return not any(_unsafe(folder) for folder in _chain(real))


def resolved(path: Path) -> Path | None:
    """The real path of ``path`` (absolute) when it and every parent belong to root and no group or other user can
    write them, and so does every symbolic link met on the way: the link itself and the real folder holding it with
    its parents (review F1: whoever can write a folder holding a link can repoint it). Links are resolved hop by hop,
    as the runtime's import path check does; more than 40 or a loop: ``None``. Windows: ACLs are not read, the path
    is only resolved there (the runtime locks its trusted import)."""
    if os.name != "posix":
        return Path(os.path.realpath(path))
    parts = list(path.parts)
    if not parts or not path.is_absolute():
        return None
    current = Path(parts.pop(0))
    hops = 0
    while parts:
        part = parts.pop(0)
        if part in ("", "."):
            continue
        if part == "..":
            current = current.parent  # ``current`` is real (its links are resolved), so this is the kernel's parent
            continue
        candidate = current / part
        try:
            info = os.lstat(candidate)
        except OSError:
            current = candidate  # missing: the check of the result refuses it
            continue
        if not stat.S_ISLNK(info.st_mode):
            current = candidate
            continue
        hops += 1
        if hops > 40 or info.st_uid not in program_owners() or not _chain_closed(current):
            return None
        target = Path(os.readlink(candidate))
        if target.is_absolute():
            current, parts = Path(target.anchor), [*target.parts[1:], *parts]
        else:
            parts = [*target.parts, *parts]
    return current if _chain_closed(current) else None


def _closed(path: Path) -> bool:
    """Whether :func:`resolved` accepts ``path``."""
    return resolved(path) is not None


def _identity(path: str | os.PathLike[str]) -> tuple[int, int] | None:
    try:
        info = os.stat(path)
    except OSError:
        return None
    return info.st_dev, info.st_ino


def python_folders() -> set[tuple[int, int]]:
    """The folders Python packages can place programs in (review N-22 NEW-5), by device and inode: the interpreter's
    own program folders (``bin`` or ``Scripts`` of its prefixes, of every install scheme) and every folder that holds
    a file named in a distribution's ``RECORD``. A wheel's ``.data/scripts`` lands there, so a ``tesseract`` from a
    package is never taken for the system's."""
    folders: set[str] = set()
    for prefix in {sys.prefix, sys.exec_prefix}:
        folders |= {os.path.join(prefix, "bin"), os.path.join(prefix, "Scripts")}
    for scheme in sysconfig.get_scheme_names():
        try:
            folders.add(sysconfig.get_path("scripts", scheme))
        except (KeyError, ValueError):
            continue
    for distribution in metadata.distributions():
        base = str(distribution.locate_file(""))
        record = distribution.read_text("RECORD")
        if record is not None:  # read directly: its folders, not its files, are needed (a tenth of the time)
            named = {os.path.dirname(row[0]) for row in csv.reader(record.splitlines()) if row}
        else:
            named = {os.path.dirname(str(file)) for file in distribution.files or ()}
        folders |= {os.path.normpath(os.path.join(base, folder)) for folder in named}
    return {found for found in map(_identity, folders) if found is not None}


def program_path() -> list[str]:
    """The ``PATH`` folders the programs may come from (review M2, owner decision 2026-11-27): absolute, existing, and
    with the whole chain owned by root and writable by no group or other user (:func:`_closed`). An empty or relative
    element (the working directory) and a folder the user or another user could change are left out, so a program
    placed there is never found or run. So is every folder of :func:`python_folders` (NEW-5): the
    OCR programs are system programs, never ones a Python package installed."""
    folders: list[str] = []
    excluded: set[tuple[int, int]] | None = None
    for element in os.environ.get("PATH", "").split(os.pathsep):
        if not element or not os.path.isabs(element) or not os.path.isdir(element):
            continue
        if element in folders or not _closed(Path(element)):
            continue
        if excluded is None:
            excluded = python_folders()
        if _identity(element) not in excluded:
            folders.append(element)
    return folders


def find_program(name: str) -> str | None:
    """The real path of the program ``name`` in a folder of :func:`program_path`, when the file and every link on the
    way to it pass :func:`resolved`; ``None`` when there is none. The real path is what runs (review F1), so a link
    is not resolved again when the program starts."""
    for folder in program_path():
        found = shutil.which(name, path=folder)
        if found is not None and (real := resolved(Path(found))) is not None:
            return str(real)
    return None


def _setting(name: str, default: int, low: int, high: int) -> int:
    """An integer from the environment within ``low`` and ``high``; the default when unset or invalid."""
    try:
        value = int(os.environ.get(name, "").strip())
    except ValueError:
        return default
    return min(max(value, low), high)


def max_parallel() -> int:
    """How many documents this process recognizes at the same time (:data:`MAX_PARALLEL` unless configured)."""
    return _setting("NODESTRO_OCR_PARALLEL", MAX_PARALLEL, 1, 64)


def max_program_bytes() -> int:
    """The address space limit of one program call (:data:`MAX_PROGRAM_BYTES` unless configured)."""
    return _setting("NODESTRO_OCR_PROGRAM_BYTES", MAX_PROGRAM_BYTES, 256 * 1024**2, 1024**4)


class _Slots:
    """At most :func:`max_parallel` documents at a time; the limit is read when a document asks for a slot."""

    def __init__(self) -> None:
        self._changed = threading.Condition()
        self._busy = 0

    @property
    def busy(self) -> int:
        with self._changed:
            return self._busy

    def acquire(self, deadline: float) -> bool:
        with self._changed:
            while self._busy >= max_parallel():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._changed.wait(remaining)
            self._busy += 1
            return True

    def release(self) -> None:
        with self._changed:
            self._busy -= 1
            self._changed.notify_all()


_SLOTS = _Slots()

#: Runs the program given after the limit with ``RLIMIT_AS`` set (``exec``: the same process, the same arguments).
#: A system that does not enforce the limit (macOS) or refuses it runs the program without one.
_LIMITER = (
    "import os, sys\n"
    "try:\n"
    "    import resource\n"
    "    limit = int(sys.argv[1])\n"
    "    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))\n"
    "except (ImportError, ValueError, OSError):\n"
    "    pass\n"
    "os.execv(sys.argv[2], sys.argv[2:])\n"
)


def _limited(command: list[str]) -> list[str]:
    """``command`` with its address space limited (Linux); unchanged where there is no such limit (Windows)."""
    if os.name != "posix" or sys.platform == "darwin" or not sys.executable:
        return command
    return [sys.executable, "-I", "-S", "-c", _LIMITER, str(max_program_bytes()), *command]


def _programs() -> dict[str, str] | None:
    """The full paths of the programs (``None`` when one is missing)."""
    found = {name: find_program(name) for name in ("tesseract", "pdftoppm", "pdfinfo")}
    return {name: path for name, path in found.items() if path is not None} if all(found.values()) else None


def _run(command: list[str], deadline: float, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a program without a shell; raises :class:`subprocess.TimeoutExpired` past the deadline.

    On a timeout :func:`subprocess.run` kills the program before raising.
    """
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise subprocess.TimeoutExpired(command, 0)
    return subprocess.run(
        _limited(command),
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
    tesseract = find_program("tesseract")
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
    pdfinfo = find_program("pdfinfo")
    if pdfinfo is None:
        return None
    try:
        return _pdf_info(pdfinfo, source, source.name, time.monotonic() + 60)[0]
    except DocumentError:
        return None


def _pixels(width: float, height: float, dpi: int) -> int:
    """Pixels of a page of ``width`` x ``height`` points rendered at ``dpi`` (as poppler rounds: up)."""
    return math.ceil(width * dpi / 72) * math.ceil(height * dpi / 72)


def _dpi(width: float, height: float) -> int | None:
    """The resolution for a page of ``width`` x ``height`` points: :data:`DPI` within :data:`MAX_PAGE_PIXELS`.

    ``None`` when the page exceeds :data:`MAX_PAGE_PIXELS` even at :data:`MIN_DPI`: such a page is
    refused instead of rendered beyond the limit.
    """
    square_inches = (width / 72) * (height / 72)
    if square_inches <= 0:
        return DPI
    dpi = min(DPI, int(math.sqrt(MAX_PAGE_PIXELS / square_inches)))
    # Rounding up to whole pixels can exceed the limit by a row or column: step down until it fits.
    while dpi >= MIN_DPI and _pixels(width, height, dpi) > MAX_PAGE_PIXELS:
        dpi -= 1
    return dpi if dpi >= MIN_DPI else None


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
    password-protected PDF, a page that cannot be rendered or recognized, a page too large to
    render within :data:`MAX_PAGE_PIXELS`, or a timeout.
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
    if not _SLOTS.acquire(deadline):
        raise DocumentError(
            "document.ocr_failed", f"{name}: timed out waiting for other documents to be recognized", name=name
        )
    try:
        return _recognize_document(programs, languages, data, name, deadline)
    finally:
        _SLOTS.release()


def _recognize_document(
    programs: dict[str, str], languages: list[str], data: bytes, name: str, deadline: float
) -> OcrResult:
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
                if dpi is None:
                    raise DocumentError("document.ocr_failed", f"{name}: {step} is too large to render", name=name)
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
