"""Nodestro Integrations: optional extensions of the Nodestro runtime.

Each integration is registered through the extension contract of ``nodestro-runtime``
(:mod:`nodestro_runtime.extensions`, entry point group ``nodestro.integrations``); installing
this package makes them available to every workspace, the API and the studio. Nothing here is
needed for running workflows: without it, the integrations' features are reported as
unavailable.

Integrations:

- ``tesseract-ocr`` (:mod:`nodestro_integrations.ocr`): local OCR of scanned PDFs for
  knowledge files and run inputs.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("nodestro-integrations")
except PackageNotFoundError:  # pragma: no cover - running from a source checkout
    __version__ = "0.0.0"

__all__ = ["__version__"]
