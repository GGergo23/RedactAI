"""Typed NLP entity contracts used by the detector."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NLPEntity:
    """Single PII detection returned by the NLP detector.

    Attributes:
        label: Normalized entity label such as PERSON, EMAIL, or PHONE.
        text: Exact substring matched in the OCR input.
        start: Inclusive 0-based start offset into the OCR text.
        end: Exclusive end offset into the OCR text.
        confidence: Confidence score in the range 0..1.
        source: Detector source, usually ``spacy`` or ``regex``.
    """

    label: str
    text: str
    start: int
    end: int
    confidence: float = 1.0
    source: str = "spacy"
