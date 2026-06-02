"""Tests for export orchestration."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import numpy as np
from PIL import Image

from src.businessLogic.export_orchestrator import (
    ApprovedRedaction,
    ExportCommand,
    ExportOrchestrator,
    ExportProgress,
)
from src.redactEngine import RedactionType


def test_export_applies_redactions_and_saves_image(tmp_path) -> None:
    image = Image.new("RGB", (20, 20), color=(255, 255, 255))
    output_path = tmp_path / "redacted.png"
    orchestrator = ExportOrchestrator()
    command = ExportCommand(
        image=image,
        output_path=output_path,
        redactions=[
            ApprovedRedaction(
                x=2,
                y=3,
                width=5,
                height=4,
                mode=RedactionType.BLACK_BAR,
            )
        ],
    )

    result = orchestrator.export([command])

    assert result.total_images == 1
    assert result.successful_images == 1
    assert result.results[0].success is True
    saved = np.array(Image.open(output_path))
    assert np.array_equal(saved[3:7, 2:7], np.zeros((4, 5, 3), dtype=np.uint8))


def test_export_reports_per_image_failure_without_stopping_batch(tmp_path) -> None:
    image = Image.new("RGB", (20, 20), color=(255, 255, 255))
    orchestrator = ExportOrchestrator()
    commands = [
        ExportCommand(
            image=image,
            output_path=tmp_path / "valid.png",
            redactions=[],
        ),
        ExportCommand(
            image=image,
            output_path=tmp_path / "invalid.png",
            redactions=[
                ApprovedRedaction(
                    x=1,
                    y=1,
                    width=5,
                    height=5,
                    mode="unsupported",
                )
            ],
        ),
    ]

    result = orchestrator.export(commands)

    assert result.successful_images == 1
    assert result.failed_images == 1
    assert result.results[0].success is True
    assert result.results[1].success is False
    assert "unsupported" in (result.results[1].error or "")


def test_export_submits_successful_redaction_count_to_analytics(tmp_path) -> None:
    submitted = []

    def fake_analytics_submitter(redaction_count, consent_granted):
        submitted.append((redaction_count, consent_granted))
        return True

    image = Image.new("RGB", (20, 20), color=(255, 255, 255))
    orchestrator = ExportOrchestrator(
        analytics_submitter=fake_analytics_submitter,
        analytics_consent=True,
    )
    commands = [
        ExportCommand(
            image=image,
            output_path=tmp_path / "valid.png",
            redactions=[
                ApprovedRedaction(x=1, y=1, width=3, height=3),
                ApprovedRedaction(x=5, y=5, width=3, height=3),
            ],
        ),
        ExportCommand(
            image=image,
            output_path=tmp_path / "invalid.png",
            redactions=[
                ApprovedRedaction(x=1, y=1, width=5, height=5, mode="not-a-mode")
            ],
        ),
    ]

    result = orchestrator.export(commands)

    assert submitted == [(2, True)]
    assert result.analytics_submitted is True


def test_start_export_returns_quickly_and_uses_result_callback(tmp_path) -> None:
    callback_results = []

    def slow_saver(image, output_path, image_format):
        time.sleep(0.2)
        return Path(output_path)

    image = Image.new("RGB", (20, 20), color=(255, 255, 255))
    orchestrator = ExportOrchestrator(image_saver=slow_saver)
    command = ExportCommand(
        image=image,
        output_path=tmp_path / "out.png",
        redactions=[],
    )

    started_at = time.perf_counter()
    task = orchestrator.start_export([command], result_callback=callback_results.append)
    elapsed = time.perf_counter() - started_at

    assert elapsed < 0.5
    for _ in range(50):
        if callback_results:
            break
        time.sleep(0.05)

    assert task.done is True
    assert callback_results[0].successful_images == 1


def test_start_export_runs_on_background_thread(tmp_path) -> None:
    worker_thread_ids = []
    caller_thread_id = threading.get_ident()

    def recording_saver(image, output_path, image_format):
        worker_thread_ids.append(threading.get_ident())
        return Path(output_path)

    image = Image.new("RGB", (20, 20), color=(255, 255, 255))
    orchestrator = ExportOrchestrator(image_saver=recording_saver)
    command = ExportCommand(
        image=image,
        output_path=tmp_path / "out.png",
        redactions=[],
    )

    task = orchestrator.start_export([command])
    for _ in range(50):
        if task.done:
            break
        time.sleep(0.05)

    assert worker_thread_ids
    assert worker_thread_ids[0] != caller_thread_id


def test_export_passes_approved_coordinates_to_redaction_engine(tmp_path) -> None:
    captured_targets = []

    def fake_redaction_applier(image, targets):
        captured_targets.extend(targets)
        return image

    def fake_saver(image, output_path, image_format):
        return Path(output_path)

    image = Image.new("RGB", (20, 20))
    orchestrator = ExportOrchestrator(
        redaction_applier=fake_redaction_applier,
        image_saver=fake_saver,
    )

    orchestrator.export(
        [
            ExportCommand(
                image=image,
                output_path=tmp_path / "out.png",
                redactions=[
                    ApprovedRedaction(
                        x=4,
                        y=5,
                        width=6,
                        height=7,
                        mode=RedactionType.PIXELATE,
                    )
                ],
            )
        ]
    )

    assert captured_targets[0].location.x == 4
    assert captured_targets[0].location.y == 5
    assert captured_targets[0].location.width == 6
    assert captured_targets[0].location.height == 7
    assert captured_targets[0].redaction_type == RedactionType.PIXELATE


def test_start_export_invokes_progress_callback_per_image(tmp_path) -> None:
    events: list[ExportProgress] = []

    image = Image.new("RGB", (20, 20), color=(255, 255, 255))
    orchestrator = ExportOrchestrator()
    commands = [
        ExportCommand(
            image=image,
            output_path=tmp_path / f"out_{index}.png",
            redactions=[],
        )
        for index in range(3)
    ]

    task = orchestrator.start_export(commands, progress_callback=events.append)
    for _ in range(50):
        if task.done:
            break
        time.sleep(0.05)

    assert task.done is True
    assert [event.completed_images for event in events] == [1, 2, 3]
    assert all(event.total_images == 3 for event in events)
    assert all(event.success for event in events)


def test_cancel_stops_subsequent_exports_and_marks_remaining_failed(tmp_path) -> None:
    proceed_after_first = threading.Event()
    seen_indices: list[int] = []

    def blocking_saver(image, output_path, image_format):
        index = len(seen_indices)
        seen_indices.append(index)
        if index == 0:
            proceed_after_first.wait(timeout=2.0)
        return Path(output_path)

    image = Image.new("RGB", (20, 20), color=(255, 255, 255))
    orchestrator = ExportOrchestrator(image_saver=blocking_saver)
    commands = [
        ExportCommand(
            image=image,
            output_path=tmp_path / f"out_{index}.png",
            redactions=[],
        )
        for index in range(3)
    ]

    callback_results = []
    task = orchestrator.start_export(
        commands,
        result_callback=callback_results.append,
    )

    # Wait until the first image is in-flight, then cancel.
    for _ in range(50):
        if seen_indices:
            break
        time.sleep(0.02)
    task.cancel()
    proceed_after_first.set()

    for _ in range(50):
        if callback_results:
            break
        time.sleep(0.05)

    assert task.done is True
    result = callback_results[0]
    assert result.cancelled is True
    assert result.results[0].success is True
    assert result.results[1].success is False
    assert result.results[1].error == "cancelled"
    assert result.results[2].success is False
    assert result.results[2].error == "cancelled"
    assert result.successful_images == 1
    assert result.failed_images == 2
