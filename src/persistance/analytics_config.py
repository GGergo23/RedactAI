"""Analytics endpoint configuration.

The Google Form URL and field IDs are committed to the repo deliberately --
they are effectively a public write token that has to ship inside the binary
anyway. Setting any value to an empty string disables analytics submission:
``submit_analytics`` will return ``False`` without making a network call.
"""

FORM_URL: str = (
    "https://docs.google.com/forms/d/e/" "1FAIpQLScPVrw-dDh-9_W9RimXuP9G9cF9cZl6UmPToaxAX212gNbVIg/formResponse"
)
ENTRY_COUNT: str = "entry.1704973568"
ENTRY_TEST_MODE: str = "entry.2112608349"
