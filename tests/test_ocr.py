"""The tesseract OCR integration: its parsing, its programs (simulated) and its use by the runtime."""

from __future__ import annotations

from collections.abc import Callable
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import time

from nodestro_runtime.documents import DocumentError
from nodestro_runtime.extensions import CONTRACT, Extensions, Integration, OcrEngine, discover
from nodestro_runtime.schemas import SettingsIn
from nodestro_runtime.workspace import Workspace
import pytest

from nodestro_integrations import ocr

DATA = Path(__file__).parent / "data"
TSV_HEADER = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"


def _word(text: str, conf: object = 95, block: int = 1, par: int = 1, line: int = 1) -> str:
    return f"5\t1\t{block}\t{par}\t{line}\t1\t0\t0\t1\t1\t{conf}\t{text}\n"


# ---- parsing tesseract's TSV output ---------------------------------------------------


def test_ocr_text_marks_uncertain_words() -> None:
    tsv = TSV_HEADER + _word("Rechnung", 96) + _word("l23", 31) + _word("Summe", 90, line=2)
    found, uncertain, words = ocr.parse_tsv(tsv)
    assert found == "Rechnung [?l23]\nSumme"
    assert (uncertain, words) == (1, 3)


@pytest.mark.parametrize(
    ("conf", "marked"),
    [
        *[("0", True), ("59", True), ("59.9", True), ("60", False), ("100", False), ("120", False)],
        *[("-1", False), ("nan", False), ("", False), ("high", False)],
    ],
)
def test_the_confidence_threshold(conf: str, marked: bool) -> None:
    found, uncertain, words = ocr.parse_tsv(TSV_HEADER + _word("Wort", conf))
    assert found == ("[?Wort]" if marked else "Wort")
    assert (uncertain, words) == (int(marked), 1)


def test_parsing_skips_rows_that_are_not_words() -> None:
    tsv = (
        TSV_HEADER
        + "1\t1\t0\t0\t0\t0\t0\t0\t1654\t2339\t-1\t\n"  # page row
        + "5\t1\t1\t1\t1\t1\t0\t0\t1\t1\t95\n"  # too short
        + _word("   ", 95)  # no text
        + "garbage\n\n"
        + "5\t1\t1\t1\t1\t2\t0\t0\t1\t1\t95\tGröße\textra\n"  # an extra field is ignored
    )
    assert ocr.parse_tsv(tsv) == ("Größe", 0, 1)
    assert ocr.parse_tsv("") == ("", 0, 0)
    # Without the header line the words are still read.
    assert ocr.parse_tsv(_word("ohne")) == ("ohne", 0, 1)


def test_paragraphs_are_separated_and_keep_their_order() -> None:
    tsv = (
        TSV_HEADER
        + _word("Linke", block=1)
        + _word("Spalte", block=1)
        + _word("weiter", block=1, line=2)
        + _word("Rechte", block=2)
        + _word("Spalte", block=2)
        + _word("Absatz", block=2, par=2)
    )
    assert ocr.parse_tsv(tsv)[0] == "Linke Spalte\nweiter\n\nRechte Spalte\n\nAbsatz"


def test_the_resolution_stays_within_the_pixel_limit() -> None:
    assert ocr._dpi(595, 842) == ocr.DPI  # A4
    assert ocr._dpi(2384, 3370) == 160  # A0
    huge = ocr._dpi(14400, 14400)  # the largest page PDF allows: 200 x 200 inches
    assert huge == 31
    assert (14400 / 72 * huge) ** 2 <= ocr.MAX_PAGE_PIXELS
    assert ocr._dpi(0, 0) == ocr.DPI


# ---- simulated programs ---------------------------------------------------------------

# One script plays pdfinfo, pdftoppm and tesseract (by the name it is called with). What it does is
# set in config.json next to it; every call is logged to calls.jsonl with its arguments and environment.
_FAKE = r"""
import json, math, os, sys, time
from pathlib import Path

here = Path(__file__).resolve().parent
config = json.loads((here / "config.json").read_text())
program = Path(sys.argv[0]).name
args = sys.argv[1:]
with (here / "calls.jsonl").open("a") as log:
    log.write(json.dumps({"program": program, "args": args, "env": dict(os.environ), "cwd": os.getcwd()}) + "\n")

def option(name, default=None):
    return args[args.index(name) + 1] if name in args else default

behaviour = config.get(program, "ok")
if behaviour == "sleep" and args != ["--list-langs"]:
    time.sleep(30)
if behaviour == "fail":
    sys.stderr.write("simulated failure\n")
    sys.exit(1)

pages, width, height = config.get("pages", 2), config.get("width", 595), config.get("height", 842)
if program == "pdfinfo":
    if behaviour == "password":
        sys.stderr.write("Command Line Error: Incorrect password\n")
        sys.exit(1)
    print("Title: Scan")
    if behaviour != "no-pages":
        print(f"Pages:           {pages}")
    first, last = int(option("-f", 1)), min(int(option("-l", pages)), pages)
    for number in range(first, last + 1):
        if behaviour == "no-sizes":
            continue
        print(f"Page {number:4d} size: {width} x {height} pts (A4)")
        print(f"Page {number:4d} rot:   0")
elif program == "pdftoppm":
    number, dpi, target = int(option("-f")), int(option("-r")), Path(args[-1] + ".png")
    if behaviour == "nothing" or (behaviour == "skip-page-2" and number == 2):
        sys.exit(0)
    size = (1, 1) if behaviour == "tiny" else (math.ceil(width * dpi / 72), math.ceil(height * dpi / 72))
    header = b"\x89PNG\r\n\x1a\n" + b"\0\0\0\rIHDR" + size[0].to_bytes(4, "big") + size[1].to_bytes(4, "big")
    target.write_bytes(header + b"\x08\x00\x00\x00\x00" + (b"" if behaviour == "broken" else b"\0" * 32))
    if behaviour == "broken":
        target.write_bytes(b"not a png")
elif program == "tesseract":
    if args[0] == "--list-langs":
        print('List of available languages in "/usr/share/tesseract-ocr/5/tessdata/" (3):')
        print("\n".join(config.get("languages", ["deu", "eng", "osd"])))
        sys.exit(0)
    image, language = args[0], option("-l")
    print("level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext")
    if behaviour == "blank":
        sys.exit(0)
    number = int(Path(image).stem.rsplit("-", 1)[1])
    if behaviour == "fail-page-2" and number == 2:
        sys.exit(1)
    # The configured main language reads most confidently.
    confident = language.split("+")[0] == config.get("main", "deu")
    print(f"5\t1\t1\t1\t1\t1\t0\t0\t1\t1\t{95 if confident else 70}\tSeite")
    print(f"5\t1\t1\t1\t1\t2\t0\t0\t1\t1\t20\t{number}")
"""


class Programs:
    """Simulated pdfinfo, pdftoppm and tesseract on PATH."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.config: dict[str, object] = {}
        script = folder / "fake.py"
        script.write_text(_FAKE, encoding="utf-8")
        for name in ("pdfinfo", "pdftoppm", "tesseract"):
            path = folder / name
            path.write_text(f"#!{sys.executable}\nexec(open({str(script)!r}).read())\n", encoding="utf-8")
            path.chmod(path.stat().st_mode | stat.S_IEXEC)
        self.set()

    def set(self, **values: object) -> None:
        self.config.update(values)
        (self.folder / "config.json").write_text(json.dumps(self.config), encoding="utf-8")

    def remove(self, name: str) -> None:
        (self.folder / name).unlink()

    def calls(self, program: str | None = None) -> list[dict[str, object]]:
        log = self.folder / "calls.jsonl"
        lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
        found = [json.loads(line) for line in lines]
        return [call for call in found if program is None or call["program"] == program]


@pytest.fixture
def programs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Programs:
    """Two A4 pages, German and English installed; each page reads ``Seite [?N]``."""
    folder = tmp_path / "bin"
    folder.mkdir()
    monkeypatch.setenv("PATH", str(folder))
    return Programs(folder)


@pytest.fixture
def temp_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The folder temporary directories are created in (to check that nothing stays behind)."""
    root = tmp_path / "tmp"
    root.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(root))
    return root


def _failure(run: Callable[[], object]) -> DocumentError:
    with pytest.raises(DocumentError) as raised:
        run()
    return raised.value


def test_the_engine_runs_the_local_programs(programs: Programs) -> None:
    engine = ocr.TesseractOcr()
    assert isinstance(engine, OcrEngine)
    assert engine.available()
    result = engine.recognize(b"%PDF-1.4", "scan.pdf")
    assert result.pages == 2 and result.words == 4 and result.uncertain == 2
    assert result.language == "deu+eng"
    assert result.text == "## Page 1\n\nSeite [?1]\n\n## Page 2\n\nSeite [?2]"
    # Each page is rendered on its own at 200 dpi (its crop box, as viewers show it) and read with
    # orientation detection, so that rotated scans are read too.
    renders = programs.calls("pdftoppm")
    assert [call["args"][:6] for call in renders] == [["-f", str(n), "-l", str(n), "-r", "200"] for n in (1, 2)]
    assert all("-cropbox" in call["args"] for call in renders)
    assert all(call["args"][-5:-2] == ["-l", "deu+eng", "--psm"] for call in programs.calls("tesseract")[-1:])


def test_the_main_language_of_the_first_page_comes_first(programs: Programs) -> None:
    programs.set(languages=["deu", "eng", "spa", "osd"], main="spa")
    result = ocr.TesseractOcr().recognize(b"%PDF-1.4", "albaran.pdf")
    assert result.language == "spa+deu+eng"
    readings = [call["args"][call["args"].index("-l") + 1] for call in programs.calls("tesseract")[1:]]
    # Page 1 in each language alone (the best reading is kept), page 2 with the main language first.
    assert readings == ["deu", "eng", "spa", "spa+deu+eng"]
    assert result.uncertain == 2 and "## Page 1\n\nSeite [?1]" in result.text


def test_a_blank_document_keeps_the_default_order(programs: Programs) -> None:
    """A valid PDF without text is an empty result, not an error."""
    programs.set(languages=["eng", "deu"], tesseract="blank")
    result = ocr.TesseractOcr().recognize(b"%PDF-1.4", "scan.pdf")
    assert (result.language, result.words, result.uncertain) == ("deu+eng", 0, 0)
    assert result.text == "## Page 1\n\n\n\n## Page 2\n\n"


def test_pages_are_read_in_order(programs: Programs) -> None:
    programs.set(pages=21)
    result = ocr.TesseractOcr().recognize(b"%PDF-1.4", "scan.pdf")
    headings = [line for line in result.text.splitlines() if line.startswith("## Page")]
    assert headings == [f"## Page {n}" for n in range(1, 22)]
    assert "## Page 9\n\nSeite [?9]\n\n## Page 10\n\nSeite [?10]\n\n" in result.text
    assert "## Page 19\n\nSeite [?19]\n\n## Page 20\n\nSeite [?20]\n\n" in result.text


@pytest.mark.parametrize(("pages", "note"), [(1, False), (49, False), (50, False), (51, True), (120, True)])
def test_at_most_fifty_pages_and_a_note_about_the_rest(programs: Programs, pages: int, note: bool) -> None:
    programs.set(pages=pages)
    result = ocr.TesseractOcr().recognize(b"%PDF-1.4", "scan.pdf")
    recognized = min(pages, ocr.MAX_PAGES)
    assert result.pages == recognized and result.words == 2 * recognized
    assert len(programs.calls("pdftoppm")) == recognized
    assert f"## Page {recognized}\n\nSeite [?{recognized}]" in result.text
    if note:
        assert result.text.endswith(f"(Only the first 50 of {pages} pages were recognised.)")
    else:
        assert "Only the first" not in result.text


def test_a_large_page_is_rendered_at_a_lower_resolution(programs: Programs) -> None:
    programs.set(pages=1, width=14400, height=14400)
    assert ocr.TesseractOcr().recognize(b"%PDF-1.4", "plan.pdf").words == 2
    assert programs.calls("pdftoppm")[0]["args"][4:6] == ["-r", "31"]


def test_without_the_programs_the_engine_is_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    engine = ocr.TesseractOcr()
    assert not engine.available()
    assert ocr.tesseract_languages() == ""
    assert _failure(lambda: engine.recognize(b"%PDF-1.4", "scan.pdf")).code == "document.ocr_unavailable"
    assert Extensions([ocr.integration()]).ocr() is None


@pytest.mark.parametrize("missing", ["pdfinfo", "pdftoppm", "tesseract"])
def test_each_program_is_required(programs: Programs, missing: str) -> None:
    # Without pdfinfo the page count is unknown, and a long document could be cut short unnoticed.
    programs.remove(missing)
    assert not ocr.ocr_available()
    assert _failure(lambda: ocr.run_ocr(b"%PDF-1.4", "scan.pdf")).code == "document.ocr_unavailable"


@pytest.mark.parametrize(("languages", "tesseract"), [(["osd", "chi_sim"], "ok"), ([], "ok"), (["eng"], "fail")])
def test_without_a_usable_language_the_engine_is_unavailable(
    programs: Programs, languages: list[str], tesseract: str
) -> None:
    """Only other languages, none at all, or a failing ``--list-langs``: no fallback to a missing ``eng``."""
    programs.set(languages=languages, tesseract=tesseract)
    assert ocr.tesseract_languages() == ""
    assert not ocr.TesseractOcr().available()
    error = _failure(lambda: ocr.run_ocr(b"%PDF-1.4", "scan.pdf"))
    assert error.code == "document.ocr_unavailable" and "language" in str(error)


def test_the_installed_languages_in_nodestro_order(programs: Programs) -> None:
    programs.set(languages=["ita", "osd", "eng", "por", "fra", "spa", "deu", "nld"])
    assert ocr.tesseract_languages() == "deu+eng+spa+fra+por+ita"


@pytest.mark.parametrize(
    ("config", "message"),
    [
        ({"pdfinfo": "fail"}, "damaged or not a PDF"),
        ({"pdfinfo": "password"}, "password-protected"),
        ({"pdfinfo": "no-pages"}, "page count could not be read"),
        ({"pdfinfo": "no-sizes"}, "page 1 has no size"),
        ({"pages": 0}, "has no pages"),
        ({"pdftoppm": "fail"}, "page 1 could not be rendered"),
        # pdftoppm reports success but writes nothing, a 1x1 image (poppler's answer to pages it
        # cannot allocate) or no PNG: never a seemingly complete result with empty pages.
        ({"pdftoppm": "nothing"}, "page 1 could not be rendered"),
        ({"pdftoppm": "skip-page-2"}, "page 2 could not be rendered"),
        ({"pdftoppm": "tiny"}, "page 1 could not be rendered"),
        ({"pdftoppm": "broken"}, "page 1 could not be rendered"),
        ({"tesseract": "fail-page-2"}, "page 2 failed"),
    ],
)
def test_failures_are_reported_with_the_step(
    programs: Programs, temp_root: Path, config: dict[str, object], message: str
) -> None:
    programs.set(**config)
    error = _failure(lambda: ocr.run_ocr(b"%PDF-1.4", "scan.pdf"))
    assert error.code == "document.ocr_failed"
    assert str(error).startswith("scan.pdf: ") and message in str(error)
    assert error.params["name"] == "scan.pdf"
    assert "simulated" not in str(error)  # program output stays out of messages
    assert list(temp_root.iterdir()) == []


@pytest.mark.parametrize("program", ["pdfinfo", "pdftoppm", "tesseract"])
def test_a_hanging_program_is_stopped(
    programs: Programs, temp_root: Path, monkeypatch: pytest.MonkeyPatch, program: str
) -> None:
    monkeypatch.setattr(ocr, "STEP_SECONDS", 1)
    programs.set(**{program: "sleep"})
    started = time.monotonic()
    error = _failure(lambda: ocr.run_ocr(b"%PDF-1.4", "scan.pdf"))
    assert time.monotonic() - started < 10
    assert error.code == "document.ocr_failed"
    assert "timed out" in str(error)
    assert list(temp_root.iterdir()) == []


def test_the_whole_document_has_a_time_limit(
    programs: Programs, monkeypatch: pytest.MonkeyPatch, temp_root: Path
) -> None:
    monkeypatch.setattr(ocr, "MAX_SECONDS", 0.5)
    programs.set(pages=50)
    started = time.monotonic()
    error = _failure(lambda: ocr.run_ocr(b"%PDF-1.4", "scan.pdf"))
    assert time.monotonic() - started < 10
    assert "timed out" in str(error)
    assert list(temp_root.iterdir()) == []


def test_without_temporary_space_the_ocr_fails_cleanly(
    programs: Programs, temp_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def full(self: Path, data: bytes) -> int:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(Path, "write_bytes", full)
    error = _failure(lambda: ocr.run_ocr(b"%PDF-1.4", "scan.pdf"))
    assert error.code == "document.ocr_failed" and "temporary" in str(error)
    assert list(temp_root.iterdir()) == []


def test_temporary_files_are_private_and_removed(programs: Programs, temp_root: Path) -> None:
    ocr.run_ocr(b"%PDF-1.4 confidential", "scan.pdf")
    assert list(temp_root.iterdir()) == []
    # The programs worked in a folder of their own (created by tempfile: readable by this user only).
    folders = {Path(str(call["cwd"])) for call in programs.calls() if call["args"] != ["--list-langs"]}
    assert len(folders) == 1 and next(iter(folders)).parent == temp_root


def test_the_file_name_never_reaches_the_file_system(programs: Programs, temp_root: Path) -> None:
    name = "../../etc/-rf passwd\n" + "ä" * 300 + ".pdf"
    result = ocr.run_ocr(b"%PDF-1.4", name)
    assert result.pages == 2
    for call in programs.calls():
        assert not any(name in str(arg) or ".." in str(arg) for arg in call["args"])
    programs.set(pdfinfo="fail")
    assert _failure(lambda: ocr.run_ocr(b"%PDF-1.4", name)).params["name"] == name


def test_the_programs_get_no_secrets(programs: Programs, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GITHUB_TOKEN", "AWS_SECRET_ACCESS_KEY", "HTTPS_PROXY"):
        monkeypatch.setenv(name, "secret-value")
    monkeypatch.setenv("TESSDATA_PREFIX", "/opt/tessdata")
    monkeypatch.setenv("LC_ALL", "C.UTF-8")
    monkeypatch.delenv("OMP_THREAD_LIMIT", raising=False)
    ocr.run_ocr(b"%PDF-1.4", "scan.pdf")
    calls = programs.calls()
    assert {call["program"] for call in calls} == {"pdfinfo", "pdftoppm", "tesseract"}
    for call in calls:
        env = call["env"]
        assert isinstance(env, dict)
        assert "secret-value" not in env.values()
        assert env["PATH"] == os.environ["PATH"] and env["TESSDATA_PREFIX"] == "/opt/tessdata"
        assert env["LC_ALL"] == "C.UTF-8" and env["OMP_THREAD_LIMIT"] == "1"
    monkeypatch.setenv("OMP_THREAD_LIMIT", "4")
    assert ocr.program_environment()["OMP_THREAD_LIMIT"] == "4"


# ---- the runtime's contract -----------------------------------------------------------


def test_the_integration_is_registered_by_installation() -> None:
    found = {item.name: item for item in discover()}
    assert "tesseract-ocr" in found
    item = found["tesseract-ocr"]
    assert item.contract == CONTRACT and isinstance(item.ocr, ocr.TesseractOcr)
    assert isinstance(item, Integration)
    assert item.version == ocr.__version__ and item.tools == ()
    assert Extensions([item]).summary() == [
        {"name": "tesseract-ocr", "version": item.version, "tools": [], "ocr": "tesseract"}
    ]


def test_the_integration_states_its_contract() -> None:
    assert ocr.integration().contract == 1 == CONTRACT


def test_the_readme_example_is_a_valid_integration() -> None:
    """The example of README.md runs and fits the runtime's contract."""
    readme = (Path(__file__).parent.parent / "README.md").read_text(encoding="utf-8")
    code = readme.split("```python\n", 1)[1].split("```", 1)[0]
    namespace: dict[str, object] = {}
    exec(code, namespace)
    integration = namespace["integration"]
    assert callable(integration)
    item = integration()
    assert isinstance(item, Integration)
    assert Extensions([item, ocr.integration()]).summary()[0] == {
        "name": "my-integration",
        "version": "1.0.0",
        "tools": ["word_count"],
        "ocr": None,
    }


def test_a_workspace_uses_the_installed_engine(programs: Programs, tmp_path: Path) -> None:
    workspace = Workspace(tmp_path / "data")
    try:
        assert workspace.settings().ocr_available is True
        assert "tesseract-ocr" in [item["name"] for item in workspace.extensions.summary()]
        assert isinstance(workspace.extensions.ocr(), ocr.TesseractOcr)
        runner = workspace.knowledge.runner()
        assert runner is not None
        assert runner(b"%PDF-1.4", "scan.pdf").words == 4
    finally:
        workspace.close()


def test_a_workspace_without_the_programs_has_no_ocr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    workspace = Workspace(tmp_path / "data")
    try:
        assert "tesseract-ocr" in [item["name"] for item in workspace.extensions.summary()]
        assert workspace.settings().ocr_available is False
        assert workspace.extensions.ocr() is None
    finally:
        workspace.close()


def test_a_workspace_without_integrations_has_no_ocr(programs: Programs, tmp_path: Path) -> None:
    workspace = Workspace(tmp_path / "data", integrations=[])
    try:
        assert workspace.settings().ocr_available is False
        assert workspace.extensions.summary() == []
    finally:
        workspace.close()


# ---- the real programs ----------------------------------------------------------------

# CI sets NODESTRO_REQUIRE_REAL_OCR=1: there a missing program fails these tests instead of skipping them.
_REQUIRED = os.environ.get("NODESTRO_REQUIRE_REAL_OCR") == "1"


def _real(*languages: str) -> None:
    installed = ocr.tesseract_languages().split("+")
    if not ocr.ocr_available() or not set(languages) <= set(installed):
        reason = f"needs tesseract with {', '.join(languages)}, pdftoppm and pdfinfo"
        if _REQUIRED:
            pytest.fail(f"NODESTRO_REQUIRE_REAL_OCR=1 but OCR is not ready: {reason}")
        pytest.skip(reason)


def test_real_ocr_reads_a_scanned_pdf() -> None:
    """The real programs on an image-only PDF (tests/data/scan-lieferschein.pdf has no text layer)."""
    _real("deu")
    data = (DATA / "scan-lieferschein.pdf").read_bytes()
    result = ocr.TesseractOcr().recognize(data, "scan-lieferschein.pdf")
    assert result.pages == 1 and result.words >= 2
    assert "Lieferschein" in result.text and "4711" in result.text


def test_real_ocr_reads_a_rotated_spanish_scan() -> None:
    """A page scanned sideways, in Spanish: read upright, with its accents."""
    _real("spa", "deu", "eng")
    data = (DATA / "scan-delivery-note-es-rotated.pdf").read_bytes()
    result = ocr.TesseractOcr().recognize(data, "albaran.pdf")
    assert result.language.startswith("spa+")
    assert "Albarán número 4711" in result.text and "señores" in result.text and "mercancía" in result.text
    assert result.uncertain == 0


def test_real_ocr_rejects_damaged_and_protected_pdfs() -> None:
    _real("eng")
    data = (DATA / "scan-lieferschein.pdf").read_bytes()
    for broken in (b"", b"hello", b"%PDF-1.4\nnot really\n", data[: len(data) // 2]):
        error = _failure(lambda broken=broken: ocr.run_ocr(broken, "broken.pdf"))
        assert error.code == "document.ocr_failed" and "damaged" in str(error)


def test_real_ocr_through_knowledge_and_run_inputs(tmp_path: Path) -> None:
    """Scanned PDF -> OCR -> knowledge index -> search, and as a run input file."""
    _real("deu")
    data = (DATA / "scan-lieferschein.pdf").read_bytes()
    workspace = Workspace(tmp_path / "data")
    try:
        # OCR is off by default: the scan is stored, but not read.
        assert workspace.settings().ocr_available is True and workspace.settings().ocr_enabled is False
        assert workspace.knowledge.add(data, name="first.pdf").ocr is None
        assert "input.ocr_used" not in workspace.inputs.add(data, name="first.pdf").notes

        workspace.update_settings(SettingsIn(ocr_enabled=True))
        entry = workspace.knowledge.add(data, name="scan-lieferschein.pdf")
        assert entry.ocr == "done" and entry.ocr_words >= 2 and entry.ocr_uncertain == 0
        hits = workspace.knowledge.search("Lieferschein")
        assert hits and hits[0].source == entry.id and "4711" in hits[0].text
        assert "4711" in workspace.knowledge.text_of(entry.id)

        item = workspace.inputs.add(data, name="scan.pdf")
        assert {"input.pdf_scanned", "input.ocr_used"} <= set(item.notes)
        extracted = workspace.inputs.extracted(item.id)
        assert extracted.pages and "Lieferschein 4711" in extracted.pages[0]
        assert "Text recognised by OCR (1 page," in extracted.text
    finally:
        workspace.close()
