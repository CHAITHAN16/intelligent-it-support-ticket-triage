from pathlib import Path
from unittest.mock import patch

import pytest

from services.triage_service import TriageService


@pytest.fixture(scope="module")
def triage_service() -> TriageService:
    return TriageService()


@pytest.mark.parametrize(
    ("title", "description", "expected_category"),
    [
        ("Network connection keeps dropping", "The office network disconnects repeatedly.", "Network"),
        ("Critical security breach detected", "Unauthorized access and malware activity were detected.", "Security"),
        ("Application keeps crashing", "The internal application crashes when opening reports.", "Software"),
        ("Marketing campaign question", "I need information about a marketing campaign.", "Other"),
    ],
)
def test_category_predictions(triage_service, title, description, expected_category):
    result = triage_service.triage(title, description)

    assert result.category == expected_category
    assert result.subcategory is None
    assert result.model_version == "category-v1+priority-v2"
    assert 0.0 <= result.confidence <= 1.0


def test_high_priority_prediction(triage_service):
    result = triage_service.triage(
        "Critical security breach detected",
        "Unauthorized access and suspicious malware activity were detected on a production system.",
    )

    assert result.priority.value == "HIGH"


def test_model_loading_failure_has_clear_error():
    with patch("services.triage_service.joblib.load", side_effect=OSError("corrupt model")):
        with pytest.raises(RuntimeError, match="Unable to load.*category and priority"):
            TriageService()
