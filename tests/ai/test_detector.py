from pathlib import Path

import pytest

import src.ai.detector as detector_module
from src.ai.detector import DEFAULT_MODEL_PATH, NLPDetector, ModelLoadError
from src.ai.types import NLPEntity


def test_entity_contract_fields():
    entity = NLPEntity(
        label="PERSON",
        text="John Smith",
        start=0,
        end=10,
        confidence=0.87,
        source="spacy",
    )

    assert entity.label == "PERSON"
    assert entity.text == "John Smith"
    assert entity.start == 0
    assert entity.end == 10
    assert entity.confidence == 0.87
    assert entity.source == "spacy"
    assert entity.text[entity.start : entity.end] == entity.text  # noqa: E203


def test_entity_contract_is_frozen():
    entity = NLPEntity(
        label="EMAIL",
        text="alice@example.com",
        start=0,
        end=17,
        confidence=1.0,
        source="regex",
    )

    with pytest.raises(AttributeError):
        entity.label = "PHONE"  # type: ignore[misc]


def test_detector_default_model_path_points_under_assets_models():
    detector = NLPDetector()

    assert detector.model_path == DEFAULT_MODEL_PATH


def test_loads_and_caches_local_model(monkeypatch, tmp_path):
    model_dir = tmp_path / "en_core_web_sm"
    model_dir.mkdir()

    class FakeEntity:
        def __init__(self) -> None:
            self.label_ = "PERSON"
            self.text = "John Smith"
            self.start_char = 0
            self.end_char = 10

    class FakeDoc:
        ents = [FakeEntity()]

    class FakeLanguage:
        def __call__(self, text: str):
            assert text == "John Smith"
            return FakeDoc()

    calls: list[Path] = []

    def fake_load(path):
        calls.append(Path(path))
        return FakeLanguage()

    monkeypatch.setattr(detector_module.spacy, "load", fake_load)

    detector = NLPDetector(model_path=model_dir)
    assert detector.detect("John Smith") == [
        NLPEntity(
            label="PERSON",
            text="John Smith",
            start=0,
            end=10,
            confidence=1.0,
            source="spacy",
        )
    ]
    assert detector.detect("John Smith") == [
        NLPEntity(
            label="PERSON",
            text="John Smith",
            start=0,
            end=10,
            confidence=1.0,
            source="spacy",
        )
    ]
    assert calls == [model_dir]


def test_detector_raises_clear_error_when_model_is_missing():
    detector = NLPDetector(model_path=Path("/tmp/redactai-missing-model"))

    with pytest.raises(ModelLoadError, match="local spaCy model"):
        detector.detect("John Smith")
