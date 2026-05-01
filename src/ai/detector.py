"""Offline NLP detector for OCR text."""

from __future__ import annotations

import re
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

        # Load spaCy pipeline lazily and collect spaCy entities first.
        nlp = self._load_nlp()
        doc = nlp(text)

        spacy_entities: list[NLPEntity] = []
        for entity in doc.ents:
            norm_label = _normalize_label(entity.label_)
            if norm_label is None:
                continue
            spacy_entities.append(
                NLPEntity(
                    label=norm_label,
                    text=entity.text,
                    start=entity.start_char,
                    end=entity.end_char,
                    confidence=1.0,
                    source="spacy",
                )
            )

        regex_entities = _regex_entities(text)

        # Remove any spaCy entity that overlaps a regex span (regex wins).
        retained_spacy: list[NLPEntity] = []
        for se in spacy_entities:
            overlaps = any(
                _spans_overlap(se.start, se.end, re_e.start, re_e.end)
                for re_e in regex_entities
            )
            if overlaps:
                continue
            retained_spacy.append(se)

        merged = list(regex_entities) + retained_spacy
        merged.sort(key=lambda e: e.start)

        return merged


def _spans_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[-\.\s]?)?(?:\(?\d{2,4}\)?[-\.\s]?)?\d{3,5}[-\.\s]?\d{3,5}"
)
_IBAN_RE = re.compile(r"\b[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}\b", re.IGNORECASE)


def _regex_entities(text: str) -> list[NLPEntity]:
    candidates: list[NLPEntity] = []
    for m in _EMAIL_RE.finditer(text):
        candidates.append(
            NLPEntity(
                label="EMAIL",
                text=m.group(0),
                start=m.start(),
                end=m.end(),
                confidence=1.0,
                source="regex",
            )
        )
    for m in _PHONE_RE.finditer(text):
        candidates.append(
            NLPEntity(
                label="PHONE",
                text=m.group(0),
                start=m.start(),
                end=m.end(),
                confidence=1.0,
                source="regex",
            )
        )
    for m in _IBAN_RE.finditer(text):
        candidates.append(
            NLPEntity(
                label="IBAN",
                text=m.group(0),
                start=m.start(),
                end=m.end(),
                confidence=1.0,
                source="regex",
            )
        )

    # Prefer longer matches when regexes overlap: sort by span length desc
    # and accept non-overlapping matches only (longer spans win).
    candidates.sort(key=lambda e: e.end - e.start, reverse=True)
    accepted: list[NLPEntity] = []
    for c in candidates:
        overlaps = any(_spans_overlap(c.start, c.end, a.start, a.end) for a in accepted)
        if overlaps:
            continue
        accepted.append(c)

    # Return accepted matches sorted by start index.
    accepted.sort(key=lambda e: e.start)
    return accepted


def _normalize_label(label: str) -> str | None:
    """Map spaCy label names to the canonical phase-3 set or drop them.

    Supported canonical labels: PERSON, ORG, LOCATION, DATE
    """
    mapping = {
        "PERSON": "PERSON",
        "ORG": "ORG",
        "GPE": "LOCATION",
        "LOC": "LOCATION",
        "DATE": "DATE",
    }
    return mapping.get(label)
