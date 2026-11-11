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
    assert result.category_model_version == "category-v1"
    assert result.priority_model_version == "priority-v2"
    assert sum(result.category_probabilities.values()) == pytest.approx(1.0)
    assert sum(result.priority_probabilities.values()) == pytest.approx(1.0)
    assert result.category_probabilities[result.category] == pytest.approx(result.classification_confidence)
    assert result.category_probabilities.keys() == {"Network", "Other", "Security", "Software"}
    assert 0.0 <= result.classification_confidence <= 1.0
    assert 0.0 <= result.confidence <= 1.0


def test_high_priority_prediction(triage_service):
    result = triage_service.triage(
        "Critical security breach detected",
        "Unauthorized access and suspicious malware activity were detected on a production system.",
    )

    assert result.priority.value == "HIGH"
    assert 0.0 <= result.classification_confidence <= 1.0
    assert 0.0 <= result.confidence <= 1.0


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


@pytest.mark.parametrize(
    ("probabilities", "message"),
    [
        ([0.2], "probability count"),
        ([0.2, float("nan")], "outside the range"),
        ([0.2, 1.2], "outside the range"),
        ([0.2, 0.7], "sum to 1"),
    ],
)
def test_model_rejects_invalid_probability_vectors(probabilities, message):
    class FixedModel:
        classes_ = ["Other", "Software"]

        def predict(self, _texts):
            return ["Software"]

        def predict_proba(self, _texts):
            return [probabilities]

    with pytest.raises(ValueError, match=message):
        TriageService._predict_with_confidence(FixedModel(), "App issue")


@pytest.mark.parametrize(
    "probability_rows",
    [[], [[0.2, 0.3], [0.5, 0.0]], [0.2, 0.8]],
)
def test_model_rejects_invalid_probability_output_shapes(probability_rows):
    class FixedModel:
        classes_ = ["Other", "Software"]

        def predict(self, _texts):
            return ["Software"]

        def predict_proba(self, _texts):
            return probability_rows

    with pytest.raises(ValueError, match="probability"):
        TriageService._predict_with_confidence(FixedModel(), "App issue")


def test_model_accepts_probability_sum_with_small_rounding_error():
    class FixedModel:
        classes_ = ["Other", "Software"]

        def predict(self, _texts):
            return ["Software"]

        def predict_proba(self, _texts):
            return [[0.2, 0.8000005]]

    prediction, confidence, probabilities = TriageService._predict_with_confidence(
        FixedModel(), "App issue"
    )

    assert prediction == "Software"
    assert confidence == pytest.approx(0.8000005)
    assert probabilities["Other"] == pytest.approx(0.2)
    assert probabilities["Software"] == pytest.approx(0.8000005)


def test_confidence_repair_requires_model_to_reproduce_stored_category():
    class FixedModel:
        classes_ = ["Other", "Software"]

        def predict(self, _texts):
            return ["Software"]

        def predict_proba(self, _texts):
            return [[0.2, 0.8]]

    service = TriageService.__new__(TriageService)
    service.category_model = FixedModel()

    assert service.classification_confidence_for_category(
        "App issue", "The application stopped responding.", "Software"
    ) == 0.8
    with pytest.raises(ValueError, match="stored prediction is 'Network'"):
        service.classification_confidence_for_category(
            "App issue", "The application stopped responding.", "Network"
        )


def test_model_loading_failure_has_clear_error():
    with patch("services.triage_service.joblib.load", side_effect=OSError("corrupt model")):
        with pytest.raises(RuntimeError, match="Unable to load.*category and priority"):
            TriageService()
