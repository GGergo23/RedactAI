"""Tests for the automatic detection pipeline controller."""

from __future__ import annotations

import time
from threading import Event

from PIL import Image

from src.ai.types import (
    BoundingBox,
    DetectedObject,
    NLPEntity,
    OCRResult,
    OCRWord,
    TextDetection,
)
from src.businessLogic.pipeline_controller import PipelineController
from src.businessLogic.pipeline_types import (
    PipelineSettings,
    PipelineStage,
    PipelineStatus,
)


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


def _write_image(tmp_path, name: str = "input.png") -> str:
    image_path = tmp_path / name
    Image.new("RGB", (100, 100), color=(255, 255, 255)).save(image_path)
    return str(image_path)


def test_pipeline_maps_nlp_entities_to_detection_results(tmp_path) -> None:
    image_path = _write_image(tmp_path)
    controller = PipelineController(
        ocr_runner=fake_ocr_runner,
        nlp_detector=FakeNLPDetector(),
    )

    result = controller.process_image_paths([image_path])

    image_result = result.results[0]
    assert image_result.image_path == image_path
    assert image_result.success is True
    assert len(image_result.detections) == 1
    assert image_result.detections[0].label == "PERSON"
    assert image_result.detections[0].bounding_box == BoundingBox(
        x=10,
        y=20,
        width=55,
        height=10,
    )


def test_pipeline_includes_object_detection_candidates(tmp_path) -> None:
    image_path = _write_image(tmp_path)
    controller = PipelineController(
        ocr_runner=fake_ocr_runner,
        nlp_detector=FakeNLPDetector(),
        object_detector=FakeObjectDetector(),
    )

    result = controller.process_image_paths([image_path])

    assert [candidate.label for candidate in result.results[0].detections] == [
        "PERSON",
        "face",
    ]
    assert result.results[0].detections[1].bounding_box == BoundingBox(
        x=30,
        y=40,
        width=50,
        height=60,
    )


def test_pipeline_filters_by_enabled_labels(tmp_path) -> None:
    image_path = _write_image(tmp_path)
    controller = PipelineController(
        ocr_runner=fake_ocr_runner,
        nlp_detector=FakeNLPDetector(),
        object_detector=FakeObjectDetector(),
    )
    settings = PipelineSettings(
        enabled_text_labels=frozenset({"EMAIL"}),
        enabled_object_labels=frozenset({"face"}),
    )

    result = controller.process_image_paths([image_path], settings=settings)

    detections = result.results[0].detections
    assert len(detections) == 1
    assert detections[0].label == "face"


def test_pipeline_emits_intermediate_progress_updates(tmp_path) -> None:
    image_path = _write_image(tmp_path)
    progress_events = []
    controller = PipelineController(
        ocr_runner=fake_ocr_runner,
        nlp_detector=FakeNLPDetector(),
    )

    controller.process_image_paths(
        [image_path], progress_callback=progress_events.append
    )

    stages = [event.stage for event in progress_events]
    assert stages[:2] == [PipelineStage.QUEUED, PipelineStage.STARTED]
    assert PipelineStage.IMAGE_LOADED in stages
    assert PipelineStage.OCR_COMPLETED in stages
    assert PipelineStage.NLP_COMPLETED in stages
    assert PipelineStage.DETECTIONS_READY in stages
    assert stages[-1] == PipelineStage.COMPLETED
    assert progress_events[-1].completed_images == 1


def test_pipeline_skips_paths_above_cap_without_crashing(tmp_path) -> None:
    image_path = _write_image(tmp_path)
    image_paths = [image_path for _ in range(51)]
    controller = PipelineController(
        ocr_runner=fake_ocr_runner,
        nlp_detector=FakeNLPDetector(),
    )

    result = controller.process_image_paths(image_paths)

    assert result.processed_images == 50
    assert result.skipped_images == 1
    assert len(result.results) == 51
    assert result.results[-1].success is False
    assert "image limit" in (result.results[-1].error or "")


def test_start_detection_returns_quickly_and_uses_result_callback(tmp_path) -> None:
    image_path = _write_image(tmp_path)
    callback_results = []
    controller = PipelineController(
        ocr_runner=fake_ocr_runner,
        nlp_detector=FakeNLPDetector(),
    )

    started_at = time.perf_counter()
    task = controller.start_detection(
        [image_path],
        result_callback=callback_results.append,
    )
    elapsed = time.perf_counter() - started_at

    assert elapsed < 0.5
    for _ in range(50):
        if callback_results:
            break
        time.sleep(0.05)

    assert task.done is True
    assert callback_results[0].results[0].success is True


def test_running_detection_can_be_cancelled(tmp_path) -> None:
    image_path = _write_image(tmp_path)
    progress_events = []
    callback_results = []

    def slow_ocr_runner(images: list[Image.Image]) -> list[OCRResult]:
        time.sleep(0.2)
        return fake_ocr_runner(images)

    controller = PipelineController(
        ocr_runner=slow_ocr_runner,
        nlp_detector=FakeNLPDetector(),
    )

    task = controller.start_detection(
        [image_path],
        progress_callback=progress_events.append,
        result_callback=callback_results.append,
    )
    task.cancel()

    for _ in range(50):
        if callback_results:
            break
        time.sleep(0.05)

    assert task.cancelled is True
    assert callback_results[0].cancelled is True
    assert any(event.status == PipelineStatus.CANCELLED for event in progress_events)


def test_pre_cancelled_job_records_cancelled_result_for_in_cap_path(tmp_path) -> None:
    image_path = _write_image(tmp_path)
    cancel_event = Event()
    cancel_event.set()
    controller = PipelineController(
        ocr_runner=fake_ocr_runner,
        nlp_detector=FakeNLPDetector(),
    )

    result = controller._run_detection_job(
        job_id="job-id",
        image_paths=[image_path],
        settings=PipelineSettings(),
        progress_callback=None,
        result_callback=None,
        cancel_event=cancel_event,
    )

    assert result.cancelled is True
    assert result.processed_images == 1
    assert len(result.results) == 1
    assert result.results[0].success is False
    assert result.results[0].error == "Detection cancelled."


def test_pipeline_reports_invalid_image_path_as_failed_result(tmp_path) -> None:
    image_path = str(tmp_path / "missing.png")
    controller = PipelineController(
        ocr_runner=fake_ocr_runner,
        nlp_detector=FakeNLPDetector(),
    )

    result = controller.process_image_paths([image_path])

    assert result.results[0].image_path == image_path
    assert result.results[0].success is False
    assert result.results[0].detections == []
