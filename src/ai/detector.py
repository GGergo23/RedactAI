"""Offline NLP detector for OCR text."""

from __future__ import annotations

from pathlib import Path

import spacy
from spacy.language import Language

from src.ai.types import NLPEntity


class ModelLoadError(RuntimeError):
    """Raised when the local spaCy model cannot be loaded."""


DEFAULT_MODEL_PATH = Path("assets/models/en_core_web_sm")


class NLPDetector:
    """Detect named entities from OCR text using a local spaCy model."""

    def __init__(self, model_path: Path | str | None = None) -> None:
        if model_path is None:
            self._model_path = DEFAULT_MODEL_PATH
        else:
            self._model_path = Path(model_path)
        self._nlp: Language | None = None

    @property
    def model_path(self) -> Path:
        """Return the filesystem path used for local model loading."""

        return self._model_path

    def _load_nlp(self) -> Language:
        if self._nlp is not None:
            return self._nlp

        if not self._model_path.exists():
            raise ModelLoadError(
                f"Unable to load local spaCy model from {self._model_path}. "
                "Ensure the model exists under assets/models/ or pass a valid "
                "filesystem path."
            )

        try:
            self._nlp = spacy.load(str(self._model_path))
        except Exception as exc:  # pragma: no cover - wrapped failure paths
            raise ModelLoadError(
                f"Unable to load local spaCy model from {self._model_path}. "
                "Ensure the model is readable and compatible with spaCy."
            ) from exc

        return self._nlp

    def detect(self, text: str) -> list[NLPEntity]:
        """Detect entities in OCR text using the local spaCy pipeline.

        Empty or whitespace-only input returns an empty list before loading.
        """

        if not text or not text.strip():
            return []

        nlp = self._load_nlp()
        doc = nlp(text)

        entities: list[NLPEntity] = []
        for entity in doc.ents:
            entities.append(
                NLPEntity(
                    label=entity.label_,
                    text=entity.text,
                    start=entity.start_char,
                    end=entity.end_char,
                    confidence=1.0,
                    source="spacy",
                )
            )

        return entities
