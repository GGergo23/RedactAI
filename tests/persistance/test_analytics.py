"""Tests for the analytics submission module."""

from __future__ import annotations

import urllib.error
import urllib.parse
from unittest.mock import MagicMock, patch

import pytest

from src.persistance import analytics_config
from src.persistance.analytics import submit_analytics

FAKE_FORM_URL = "https://docs.google.com/forms/d/e/FAKE/formResponse"
FAKE_ENTRY_COUNT = "entry.111111111"
FAKE_ENTRY_TEST_MODE = "entry.222222222"


def _set_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(analytics_config, "FORM_URL", FAKE_FORM_URL)
    monkeypatch.setattr(analytics_config, "ENTRY_COUNT", FAKE_ENTRY_COUNT)
    monkeypatch.setattr(analytics_config, "ENTRY_TEST_MODE", FAKE_ENTRY_TEST_MODE)


def _make_response(status: int) -> MagicMock:
    """Build a context-manager mock mimicking ``urllib.request.urlopen``'s return."""
    response = MagicMock()
    response.status = status
    response.getcode.return_value = status
    cm = MagicMock()
    cm.__enter__.return_value = response
    cm.__exit__.return_value = False
    return cm


def _decode_post_body(call) -> dict[str, str]:
    """Extract and decode the urlencoded body from a urlopen call."""
    request = call.args[0]
    body = request.data.decode("utf-8")
    return {k: v[0] for k, v in urllib.parse.parse_qs(body).items()}


class TestConsentGate:
    def test_no_network_call_when_consent_denied(self, monkeypatch):
        _set_config(monkeypatch)
        with patch("src.persistance.analytics.urllib.request.urlopen") as mock_urlopen:
            result = submit_analytics(
                redaction_count=7, test_mode=False, consent_granted=False
            )
        assert result is False
        mock_urlopen.assert_not_called()

    def test_returns_false_when_consent_denied_even_with_config_blank(
        self, monkeypatch
    ):
        monkeypatch.setattr(analytics_config, "FORM_URL", "")
        monkeypatch.setattr(analytics_config, "ENTRY_COUNT", "")
        monkeypatch.setattr(analytics_config, "ENTRY_TEST_MODE", "")
        with patch("src.persistance.analytics.urllib.request.urlopen") as mock_urlopen:
            result = submit_analytics(
                redaction_count=1, test_mode=True, consent_granted=False
            )
        assert result is False
        mock_urlopen.assert_not_called()


class TestSuccessfulSubmission:
    def test_posts_count_and_test_mode_and_returns_true(self, monkeypatch):
        _set_config(monkeypatch)
        with patch(
            "src.persistance.analytics.urllib.request.urlopen",
            return_value=_make_response(200),
        ) as mock_urlopen:
            result = submit_analytics(
                redaction_count=5, test_mode=True, consent_granted=True
            )

        assert result is True
        mock_urlopen.assert_called_once()
        body = _decode_post_body(mock_urlopen.call_args)
        assert body == {FAKE_ENTRY_COUNT: "5", FAKE_ENTRY_TEST_MODE: "true"}

        request = mock_urlopen.call_args.args[0]
        assert request.full_url == FAKE_FORM_URL
        assert request.get_method() == "POST"
        assert request.get_header("Content-type") == "application/x-www-form-urlencoded"

    @pytest.mark.parametrize(
        "test_mode, expected",
        [(True, "true"), (False, "false")],
    )
    def test_test_mode_serialised_correctly(self, monkeypatch, test_mode, expected):
        _set_config(monkeypatch)
        with patch(
            "src.persistance.analytics.urllib.request.urlopen",
            return_value=_make_response(200),
        ) as mock_urlopen:
            submit_analytics(
                redaction_count=0, test_mode=test_mode, consent_granted=True
            )
        body = _decode_post_body(mock_urlopen.call_args)
        assert body[FAKE_ENTRY_TEST_MODE] == expected

    def test_count_coerced_to_str_of_int(self, monkeypatch):
        _set_config(monkeypatch)
        with patch(
            "src.persistance.analytics.urllib.request.urlopen",
            return_value=_make_response(200),
        ) as mock_urlopen:
            submit_analytics(redaction_count=42, test_mode=False, consent_granted=True)
        body = _decode_post_body(mock_urlopen.call_args)
        assert body[FAKE_ENTRY_COUNT] == "42"

    def test_timeout_passed_to_urlopen(self, monkeypatch):
        _set_config(monkeypatch)
        with patch(
            "src.persistance.analytics.urllib.request.urlopen",
            return_value=_make_response(200),
        ) as mock_urlopen:
            submit_analytics(
                redaction_count=1, test_mode=False, consent_granted=True, timeout=2.5
            )
        assert mock_urlopen.call_args.kwargs.get("timeout") == 2.5


class TestMissingConfiguration:
    @pytest.mark.parametrize(
        "blank_attr",
        ["FORM_URL", "ENTRY_COUNT", "ENTRY_TEST_MODE"],
    )
    def test_returns_false_when_required_config_blank(self, monkeypatch, blank_attr):
        _set_config(monkeypatch)
        monkeypatch.setattr(analytics_config, blank_attr, "")
        with patch("src.persistance.analytics.urllib.request.urlopen") as mock_urlopen:
            result = submit_analytics(
                redaction_count=3, test_mode=False, consent_granted=True
            )
        assert result is False
        mock_urlopen.assert_not_called()


class TestErrorHandling:
    def test_returns_false_on_url_error(self, monkeypatch):
        _set_config(monkeypatch)
        with patch(
            "src.persistance.analytics.urllib.request.urlopen",
            side_effect=urllib.error.URLError("boom"),
        ):
            result = submit_analytics(
                redaction_count=1, test_mode=True, consent_granted=True
            )
        assert result is False

    def test_returns_false_on_timeout(self, monkeypatch):
        _set_config(monkeypatch)
        with patch(
            "src.persistance.analytics.urllib.request.urlopen",
            side_effect=TimeoutError("slow"),
        ):
            result = submit_analytics(
                redaction_count=1, test_mode=True, consent_granted=True
            )
        assert result is False

    def test_returns_false_on_os_error(self, monkeypatch):
        _set_config(monkeypatch)
        with patch(
            "src.persistance.analytics.urllib.request.urlopen",
            side_effect=OSError("dns"),
        ):
            result = submit_analytics(
                redaction_count=1, test_mode=True, consent_granted=True
            )
        assert result is False

    def test_returns_false_on_non_2xx_status(self, monkeypatch):
        _set_config(monkeypatch)
        with patch(
            "src.persistance.analytics.urllib.request.urlopen",
            return_value=_make_response(500),
        ):
            result = submit_analytics(
                redaction_count=1, test_mode=True, consent_granted=True
            )
        assert result is False
