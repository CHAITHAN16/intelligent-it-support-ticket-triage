import math
from pathlib import Path
from typing import Any

import joblib
from pydantic import BaseModel, Field

from models import TicketPriority


MODEL_VERSION = "category-v1+priority-v2"
CATEGORY_MODEL_VERSION = "category-v1"
PRIORITY_MODEL_VERSION = "priority-v2"
EXPECTED_CATEGORIES = {"Network", "Security", "Software", "Other"}
EXPECTED_PRIORITIES = {TicketPriority.LOW, TicketPriority.MEDIUM, TicketPriority.HIGH}


class TriageResult(BaseModel):
    category: str
    subcategory: str | None
    priority: TicketPriority
    classification_confidence: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    model_version: str
    category_model_version: str
    priority_model_version: str
    category_probabilities: dict[str, float]
    priority_probabilities: dict[str, float]


class ConfidencePredictionMismatchError(ValueError):
    """Raised when the configured category model disagrees with a stored prediction."""


class TriageService:
    """Runs the trained category and priority classifiers."""

    def __init__(self) -> None:
        self.category_model, self.priority_model = self._load_models()

    @staticmethod
    def _load_models() -> tuple[Any, Any]:
        project_root = Path(__file__).resolve().parents[2]
        category_path = project_root / "ml" / "models" / "category_model_v1.joblib"
        priority_path = project_root / "ml" / "models" / "priority_model_v2.joblib"

        for model_path in (category_path, priority_path):
            if not model_path.is_file():
                raise FileNotFoundError(
                    f"Required ML triage model file is missing: {model_path}"
                )

        try:
            return joblib.load(category_path), joblib.load(priority_path)
        except Exception as error:
            raise RuntimeError(
                "Unable to load the configured category and priority ML models"
            ) from error

    @staticmethod
    def _predict_with_confidence(model: Any, text: str) -> tuple[str, float, dict[str, float]]:
        predictions = model.predict([text])
        probability_rows = model.predict_proba([text])
        classes = list(model.classes_)
        if len(predictions) != 1 or len(probability_rows) != 1:
            raise ValueError("ML model must return one prediction and probability row")

        prediction = predictions[0]
        try:
            probability_row = probability_rows[0]
            row_length = len(probability_row)
        except (IndexError, TypeError) as error:
            raise ValueError("ML model returned an invalid probability row") from error
        if row_length != len(classes):
            raise ValueError("ML probability count does not match the model classes")
        probabilities = [float(value) for value in probability_row]
        if not classes or len(probabilities) != len(classes):
            raise ValueError("ML probability count does not match the model classes")
        if any(not math.isfinite(value) or not 0.0 <= value <= 1.0 for value in probabilities):
            raise ValueError("ML model returned a probability outside the range [0, 1]")
        if not math.isclose(sum(probabilities), 1.0, rel_tol=0.0, abs_tol=1e-6):
            raise ValueError("ML model probabilities must sum to 1")
        try:
            predicted_class_index = classes.index(prediction)
        except ValueError as error:
            raise ValueError("ML prediction is not present in the model classes") from error
        probability_map = {
            str(label): probability for label, probability in zip(classes, probabilities)
        }
        return str(prediction), probabilities[predicted_class_index], probability_map

    def classification_confidence_for_category(
        self, title: str, description: str, expected_category: str
    ) -> float:
        text = f"{title or ''} {description or ''}".strip()
        predicted_category, confidence, _ = self._predict_with_confidence(
            self.category_model, text
        )
        if predicted_category != expected_category:
            raise ConfidencePredictionMismatchError(
                "Configured category model predicted "
                f"{predicted_category!r}, but the stored prediction is {expected_category!r}"
            )
        if predicted_category not in EXPECTED_CATEGORIES:
            raise ValueError(
                f"ML category model returned unsupported category: {predicted_category!r}"
            )
        return confidence

    def triage(self, title: str, description: str) -> TriageResult:
        text = f"{title or ''} {description or ''}".strip()
        predicted_category, category_confidence, category_probabilities = self._predict_with_confidence(
            self.category_model, text
        )
        predicted_priority, priority_confidence, priority_probabilities = self._predict_with_confidence(
            self.priority_model, text
        )

        if predicted_category not in EXPECTED_CATEGORIES:
            raise ValueError(
                f"ML category model returned unsupported category: {predicted_category!r}"
            )

        try:
            priority = TicketPriority(predicted_priority)
        except ValueError as error:
            raise ValueError(
                f"ML priority model returned unsupported priority: {predicted_priority!r}"
            ) from error
        if priority not in EXPECTED_PRIORITIES:
            raise ValueError(
                f"ML priority model returned unsupported priority: {predicted_priority!r}"
            )

        return TriageResult(
            category=predicted_category,
            subcategory=None,
            priority=priority,
            classification_confidence=category_confidence,
            # The mean is deterministic and gives equal weight to both model signals.
            confidence=(category_confidence + priority_confidence) / 2,
            model_version=MODEL_VERSION,
            category_model_version=CATEGORY_MODEL_VERSION,
            priority_model_version=PRIORITY_MODEL_VERSION,
            category_probabilities=category_probabilities,
            priority_probabilities=priority_probabilities,
        )
