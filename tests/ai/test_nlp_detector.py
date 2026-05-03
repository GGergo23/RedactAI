from pathlib import Path

import pytest

from src.ai.detector import ModelLoadError, NLPDetector


def test_empty_and_whitespace_returns_empty():
    d = NLPDetector()
    # model must not be loaded on instantiation
    assert getattr(d, "_nlp") is None

    assert d.detect("") == []
    assert d.detect("   \n\t") == []
    # still not loaded
    assert getattr(d, "_nlp") is None


def test_model_load_error_on_missing_model():
    missing = Path("/tmp/nonexistent_model_for_tests_abcdef")
    d = NLPDetector(model_path=missing)
    assert getattr(d, "_nlp") is None
    with pytest.raises(ModelLoadError):
        d.detect("John Doe")
    # after failed load, _nlp remains None
    assert getattr(d, "_nlp") is None


def _assert_roundtrip_and_sorted(text, entities):
    """Assert round-trip property, sorting, and no overlaps."""
    # round-trip: text[start:end] should match entity text
    for e in entities:
        assert text[e.start : e.end] == e.text
    # sorted by start index
    if len(entities) > 1:
        assert all(
            entities[i].start <= entities[i + 1].start for i in range(len(entities) - 1)
        )
    # no overlaps
    for i in range(len(entities) - 1):
        assert entities[i].end <= entities[i + 1].start


def test_validation_corpus_roundtrip():
    """Test detector against all corpus entries for expected detections."""
    d = NLPDetector()
    corpus = Path("assets/corpus/validation_corpus.jsonl")
    msg = "Corpus file missing: assets/corpus/validation_corpus.jsonl"
    assert corpus.exists(), msg

    import json

    for line in corpus.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        text = obj["text"]
        expected = obj.get("expected", [])

        ents = d.detect(text)

        # Round-trip and ordering invariants for all detected entities
        if ents:
            _assert_roundtrip_and_sorted(text, ents)

        # For each expected entity (label + text) assert existence
        for exp in expected:
            if exp["label"] == "PHONE":

                def norm_phone(s: str) -> str:
                    return "".join(ch for ch in s if ch.isdigit())

                exp_norm = norm_phone(exp["text"])
                matches = [
                    e
                    for e in ents
                    if e.label == "PHONE" and exp_norm in norm_phone(e.text)
                ]
            elif exp["label"] == "IBAN":
                exp_norm = exp["text"].replace(" ", "").lower()
                matches = [
                    e
                    for e in ents
                    if e.label == "IBAN" and exp_norm in e.text.replace(" ", "").lower()
                ]
            else:
                matches = [
                    e for e in ents if e.label == exp["label"] and exp["text"] in e.text
                ]

            msg = f"Expected {exp} not in {text}"
            assert matches, msg
