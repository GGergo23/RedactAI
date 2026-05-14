"""Tests for the automatic detection pipeline controller."""

from __future__ import annotations

from PIL import Image

from src.ai.types import (
    BoundingBox,
    DetectedObject,
    NLPEntity,
    OCRResult,
    OCRWord,
    TextDetection,
)
from src.businessLogic.pipeline_controller import (
    PipelineController,
    PipelineSettings,
    PipelineStage,
)
from src.redactEngine import RedactionType


class FakeNLPDetector:
    """Deterministic NLP detector used by pipeline tests."""

    def detect(self, text: str) -> list[NLPEntity]:
        assert text == "John Doe"
        return [
            NLPEntity(
                label="PERSON",
                text="John Doe",
                start=0,
                end=8,
                confidence=0.9,
                source="fake",
            )
        ]


class FakeObjectDetector:
    """Deterministic object detector used by pipeline tests."""

    def detect(self, images: list[Image.Image]) -> list[list[DetectedObject]]:
        assert len(images) == 1
        return [
            [
                DetectedObject(
                    label="face",
                    bounding_box=BoundingBox(x=30, y=40, width=50, height=60),
                    confidence=0.8,
                )
            ]
        ]


def fake_ocr_runner(images: list[Image.Image]) -> list[OCRResult]:
    """Return one OCR result with two words and stable character offsets."""

    assert len(images) == 1
    return [
        OCRResult(
            detections=[
                TextDetection(
                    text="John Doe",
                    words=[
                        OCRWord(
                            text="John",
                            bounding_box=BoundingBox(x=10, y=20, width=30, height=10),
                            confidence=95,
                            char_offset=0,
                        ),
                        OCRWord(
                            text="Doe",
                            bounding_box=BoundingBox(x=45, y=20, width=20, height=10),
                            confidence=92,
                            char_offset=5,
                        ),
                    ],
                )
            ]
        )
    ]


def test_pipeline_maps_nlp_entities_to_redaction_targets() -> None:
    image = Image.new("RGB", (100, 100))
    controller = PipelineController(
        ocr_runner=fake_ocr_runner,
        nlp_detector=FakeNLPDetector(),
    )

    result = controller.process_images([image])

    image_result = result.results[0]
    assert image_result.success is True
    assert len(image_result.candidates) == 1
    assert image_result.candidates[0].label == "PERSON"
    assert image_result.candidates[0].bounding_box == BoundingBox(
        x=10,
        y=20,
        width=55,
        height=10,
    )
    assert image_result.redaction_targets[0].redaction_type == RedactionType.BLACK_BAR


def test_pipeline_includes_object_detection_candidates() -> None:
    image = Image.new("RGB", (100, 100))
    controller = PipelineController(
        ocr_runner=fake_ocr_runner,
        nlp_detector=FakeNLPDetector(),
        object_detector=FakeObjectDetector(),
    )

    result = controller.process_images([image])

    assert [candidate.label for candidate in result.results[0].candidates] == [
        "PERSON",
        "face",
    ]
    assert result.results[0].redaction_targets[1].location == BoundingBox(
        x=30,
        y=40,
        width=50,
        height=60,
    )


def test_pipeline_filters_by_enabled_labels() -> None:
    image = Image.new("RGB", (100, 100))
    controller = PipelineController(
        ocr_runner=fake_ocr_runner,
        nlp_detector=FakeNLPDetector(),
        object_detector=FakeObjectDetector(),
    )
    settings = PipelineSettings(
        enabled_text_labels=frozenset({"EMAIL"}),
        enabled_object_labels=frozenset({"face"}),
    )

    result = controller.process_images([image], settings=settings)

    candidates = result.results[0].candidates
    assert len(candidates) == 1
    assert candidates[0].label == "face"


def test_pipeline_emits_intermediate_progress_updates() -> None:
    image = Image.new("RGB", (100, 100))
    progress_events = []
    controller = PipelineController(
        ocr_runner=fake_ocr_runner,
        nlp_detector=FakeNLPDetector(),
    )

    controller.process_images([image], progress_callback=progress_events.append)

    stages = [event.stage for event in progress_events]
    assert stages[:2] == [PipelineStage.QUEUED, PipelineStage.STARTED]
    assert PipelineStage.OCR_COMPLETED in stages
    assert PipelineStage.NLP_COMPLETED in stages
    assert PipelineStage.REDACTION_TARGETS_READY in stages
    assert stages[-1] == PipelineStage.COMPLETED
    assert progress_events[-1].completed_images == 1


def test_pipeline_skips_images_above_cap_without_crashing() -> None:
    images = [Image.new("RGB", (10, 10)) for _ in range(51)]
    controller = PipelineController(
        ocr_runner=fake_ocr_runner,
        nlp_detector=FakeNLPDetector(),
    )

    result = controller.process_images(images)

    assert result.processed_images == 50
    assert result.skipped_images == 1
    assert len(result.results) == 51
    assert result.results[-1].success is False
    assert "image limit" in (result.results[-1].error or "")
