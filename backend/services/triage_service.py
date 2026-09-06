from pathlib import Path
from typing import Any

import joblib
from pydantic import BaseModel, Field

from models import TicketPriority


MODEL_VERSION = "category-v1+priority-v2"
EXPECTED_CATEGORIES = {"Network", "Security", "Software", "Other"}
EXPECTED_PRIORITIES = {TicketPriority.LOW, TicketPriority.MEDIUM, TicketPriority.HIGH}


class TriageResult(BaseModel):
    category: str
    subcategory: str | None
    priority: TicketPriority
    confidence: float = Field(ge=0.0, le=1.0)
    model_version: str


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
    def _predict_with_confidence(model: Any, text: str) -> tuple[str, float]:
        prediction = model.predict([text])[0]
        probabilities = model.predict_proba([text])[0]
        predicted_class_index = list(model.classes_).index(prediction)
        return str(prediction), float(probabilities[predicted_class_index])

    def triage(self, title: str, description: str) -> TriageResult:
        text = f"{title or ''} {description or ''}".strip()
        predicted_category, category_confidence = self._predict_with_confidence(
            self.category_model, text
        )
        predicted_priority, priority_confidence = self._predict_with_confidence(
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
            # The mean is deterministic and gives equal weight to both model signals.
            confidence=(category_confidence + priority_confidence) / 2,
            model_version=MODEL_VERSION,
        )
