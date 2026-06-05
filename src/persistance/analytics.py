"""Analytics submission for RedactAI.

Submits a redaction count to a developer-owned Google Form. The submission is
gated on user consent: if consent is not granted, the function returns
immediately and makes no network call.

The form URL and field ID live in :mod:`src.persistance.analytics_config` and
ship inside the binary. Setting either constant to an empty string disables
analytics submission (the function returns ``False`` without making a network
call). The submission carries only the integer count; no image content or
other identifying information is transmitted.
"""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request

from src.persistance import analytics_config


def submit_analytics(
    redaction_count: int,
    consent_granted: bool,
    *,
    timeout: float = 5.0,
) -> bool:
    """Submit redaction analytics to the configured Google Form.

    Args:
        redaction_count: The number of redactions applied in the session.
            Must be non-negative; negative values cause the function to return
            ``False`` without making a network call.
        consent_granted: Whether the user has granted consent for analytics.
            When ``False`` the function returns immediately and performs no
            side effect (no config reads, no logging, no network call).
        timeout: Per-request timeout in seconds for the HTTP POST.

    Returns:
        ``True`` when the form accepted the submission with a 2xx status,
        ``False`` otherwise (consent denied, negative count, config blank,
        network error, or non-2xx response).
    """
    if not consent_granted:
        return False

    if redaction_count < 0:
        return False

    form_url = analytics_config.FORM_URL
    entry_count = analytics_config.ENTRY_COUNT
    if not form_url or not entry_count:
        return False

    payload = urllib.parse.urlencode({entry_count: str(int(redaction_count))}).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        url=form_url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", None)
            if status is None:
                status = response.getcode()
            return 200 <= int(status) < 300
    except urllib.error.URLError, TimeoutError, OSError:
        return False
