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


def test_category_confidence_is_separate_from_combined_triage_score():
    class FixedModel:
        def __init__(self, prediction, classes, probabilities):
            self.prediction = prediction
            self.classes_ = classes
            self.probabilities = probabilities

        def predict(self, _texts):
            return [self.prediction]

        def predict_proba(self, _texts):
            return [self.probabilities]

    service = TriageService.__new__(TriageService)
    service.category_model = FixedModel("Software", ["Other", "Software"], [0.2, 0.8])
    service.priority_model = FixedModel("HIGH", ["LOW", "MEDIUM", "HIGH"], [0.1, 0.2, 0.7])

    result = service.triage("App issue", "The application stopped responding.")

    assert result.classification_confidence == 0.8
    assert result.confidence == 0.75


def test_model_loading_failure_has_clear_error():
    with patch("services.triage_service.joblib.load", side_effect=OSError("corrupt model")):
        with pytest.raises(RuntimeError, match="Unable to load.*category and priority"):
            TriageService()
