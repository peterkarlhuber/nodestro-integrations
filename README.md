# Nodestro Integrations

Erweiterungen für [Nodestro](https://github.com/peterkarlhuber/nodestro-studio) über den Erweiterungsvertrag der
[Runtime](https://github.com/peterkarlhuber/nodestro-runtime) (`nodestro_runtime.extensions`, Vertrag 1). Das Studio
installiert dieses Paket mit; die API läuft auch ohne.

Teil der Nodestro-Plattform; den Überblick gibt
[PLATTFORM.md](https://github.com/peterkarlhuber/nodestro-studio/blob/master/docs/PLATTFORM.md).

## Enthalten

| Integration | Einstiegspunkt | Leistung |
| --- | --- | --- |
| `tesseract-ocr` | `nodestro_integrations.ocr:integration` | Lokale OCR gescannter PDFs mit poppler (`pdftoppm`) und tesseract: Text je Seite, unsichere Wörter markiert, Sprache nach den installierten tesseract-Sprachen. Nichts verlässt den Rechner. |

Ohne die beiden Programme meldet die Integration sich als nicht verfügbar, und Nodestro verhält sich wie 0.1 ohne
tesseract.

## Eine eigene Integration

```toml
# pyproject.toml
[project.entry-points."nodestro.integrations"]
meine-integration = "mein_paket:integration"
```

```python
from nodestro_runtime.extensions import Integration


def integration() -> Integration:
    return Integration(name="meine-integration", version="1.0.0", tools=[...], description="...")
```

`tools` sind orkexa-Tools für die Tool-Bibliothek, `ocr` eine `OcrEngine` (`available()`, `recognize(data, name)`).
Eine Integration, die nicht lädt, wird protokolliert und ausgelassen; eine für einen anderen Vertrag lehnt die Runtime
ab.

## Entwicklung

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check . && mypy && pytest
```

Die meisten Tests simulieren `pdftoppm` und `tesseract`; `test_real_ocr_reads_a_scanned_pdf` nutzt die echten
Programme, wenn sie installiert sind (in der CI immer: `apt-get install tesseract-ocr poppler-utils`).

Die CI braucht das Repository-Secret `NODESTRO_READ` (Lesezugriff auf orkexa und die nodestro-Repositories).

## Herkunft und Lizenz

Die OCR stammt aus `backend/src/nodestro/documents.py` von `nodestro` 0.1 (15e2076), siehe
[PROVENANCE.md](PROVENANCE.md). MIT, siehe [LICENSE](LICENSE).
