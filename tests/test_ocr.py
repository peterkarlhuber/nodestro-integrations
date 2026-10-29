"""The tesseract OCR integration: its parsing, its programs (simulated) and its use by the runtime."""

from __future__ import annotations

from pathlib import Path
import stat

from nodestro_runtime.documents import DocumentError
from nodestro_runtime.extensions import CONTRACT, Extensions, Integration, OcrEngine, discover
from nodestro_runtime.workspace import Workspace
import pytest

from nodestro_integrations import ocr

TSV_HEADER = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"


def test_ocr_text_marks_uncertain_words() -> None:
    tsv = TSV_HEADER
    tsv += "5\t1\t1\t1\t1\t1\t0\t0\t1\t1\t96\tRechnung\n5\t1\t1\t1\t1\t2\t0\t0\t1\t1\t31\tl23\n"
    tsv += "5\t1\t1\t1\t2\t1\t0\t0\t1\t1\t90\tSumme\n"
    found, uncertain, words = ocr.parse_tsv(tsv)
    assert found == "Rechnung [?l23]\nSumme"
    assert (uncertain, words) == (1, 3)


def _program(folder: Path, name: str, script: str) -> None:
    path = folder / name
    path.write_text("#!/bin/sh\n" + script, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def programs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Stand-ins for pdftoppm and tesseract on PATH: two pages, one uncertain word."""
    folder = tmp_path / "bin"
    folder.mkdir()
    # pdftoppm -r 200 -l 50 -png INPUT PREFIX  ->  PREFIX-1.png, PREFIX-2.png
    _program(folder, "pdftoppm", 'for last; do :; done\ntouch "$last-1.png" "$last-2.png"\n')
    rows = TSV_HEADER + "5\t1\t1\t1\t1\t1\t0\t0\t1\t1\t95\tLieferschein\n5\t1\t1\t1\t1\t2\t0\t0\t1\t1\t20\t4711\n"
    tsv = rows.replace("\t", "\\t").replace("\n", "\\n")
    _program(
        folder,
        "tesseract",
        'if [ "$1" = "--list-langs" ]; then printf "List of available languages\\ndeu\\neng\\n"; exit 0; fi\n'
        f'printf "{tsv}"\n',
    )
    monkeypatch.setenv("PATH", f"{folder}:/usr/bin:/bin")
    return folder


def test_the_engine_runs_the_local_programs(programs: Path) -> None:
    engine = ocr.TesseractOcr()
    assert isinstance(engine, OcrEngine)
    assert engine.available()
    result = engine.recognize(b"%PDF-1.4", "scan.pdf")
    assert result.pages == 2 and result.words == 4 and result.uncertain == 2
    assert result.language == "deu+eng"
    assert "## Page 1\n\nLieferschein [?4711]" in result.text


def test_without_the_programs_the_engine_is_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    engine = ocr.TesseractOcr()
    assert not engine.available()
    with pytest.raises(DocumentError) as raised:
        engine.recognize(b"%PDF-1.4", "scan.pdf")
    assert raised.value.code == "document.ocr_unavailable"
    assert Extensions([ocr.integration()]).ocr() is None


def test_the_integration_is_registered_by_installation() -> None:
    found = {item.name: item for item in discover()}
    assert "tesseract-ocr" in found
    item = found["tesseract-ocr"]
    assert item.contract == CONTRACT and isinstance(item.ocr, ocr.TesseractOcr)
    assert isinstance(item, Integration)


def test_a_workspace_uses_the_installed_engine(programs: Path, tmp_path: Path) -> None:
    workspace = Workspace(tmp_path / "data")
    try:
        assert workspace.settings().ocr_available is True
        assert "tesseract-ocr" in [item["name"] for item in workspace.extensions.summary()]
        runner = workspace.knowledge.runner()
        assert runner is not None
        assert runner(b"%PDF-1.4", "scan.pdf").words == 4
    finally:
        workspace.close()


def test_a_workspace_without_integrations_has_no_ocr(programs: Path, tmp_path: Path) -> None:
    workspace = Workspace(tmp_path / "data", integrations=[])
    try:
        assert workspace.settings().ocr_available is False
    finally:
        workspace.close()


@pytest.mark.skipif(not ocr.ocr_available(), reason="needs tesseract and pdftoppm (CI installs them)")
def test_real_ocr_reads_a_scanned_pdf() -> None:
    """The real programs on an image-only PDF (tests/data/scan-lieferschein.pdf has no text layer)."""
    data = (Path(__file__).parent / "data" / "scan-lieferschein.pdf").read_bytes()
    result = ocr.TesseractOcr().recognize(data, "scan-lieferschein.pdf")
    assert result.pages == 1 and result.words >= 2
    assert "Lieferschein" in result.text and "4711" in result.text
