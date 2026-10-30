# Provenance

Source: `peterkarlhuber/nodestro` (now `nodestro-legacy`) at commit
`15e20768dea496820d4f8a286720176b47817da7` (merge of PR #14, version 0.1.0). The "State" column compares each file
byte for byte with the original as of the split (version 0.2.0); "adapted" gives the changed lines (mostly rewritten
imports). Changes since then are listed in [CHANGELOG.md](CHANGELOG.md).

0 files unchanged, 2 adapted, 9 new.

| File | Original | State |
| --- | --- | --- |
| `.github/workflows/ci.yml` | — | new |
| `.gitignore` | — | new |
| `CHANGELOG.md` | — | new |
| `LICENSE` | — | new |
| `README.md` | — | new |
| `pyproject.toml` | — | new |
| `src/nodestro_integrations/__init__.py` | — | new |
| `src/nodestro_integrations/ocr.py` | `backend/src/nodestro/documents.py` | adapted (+31 −365 lines) |
| `src/nodestro_integrations/py.typed` | — | new |
| `tests/data/scan-lieferschein.pdf` | — | new |
| `tests/test_ocr.py` | `backend/src/nodestro/documents.py` | adapted (+81 −436 lines) |
