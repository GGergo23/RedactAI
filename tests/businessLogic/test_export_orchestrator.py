"""Tests for export orchestration."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from src.businessLogic.export_orchestrator import (
    ApprovedRedaction,
    ExportCommand,
    ExportOrchestrator,
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
