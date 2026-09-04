from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
from pydantic import BaseModel, Field

from models import TicketPriority


MODEL_VERSION = "ml-v1"


class TriageResult(BaseModel):
    category: str
    subcategory: str
    priority: TicketPriority
    confidence: float = Field(ge=0.0, le=1.0)
    model_version: str


class TriageService:
    """Runs the trained subcategory and priority classifiers."""

    def __init__(self) -> None:
        self.subcategory_model, self.priority_model = self._load_models()

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_models() -> tuple[Any, Any]:
        project_root = Path(__file__).resolve().parents[2]
        subcategory_path = project_root / "ml" / "models" / "subcategory_model.joblib"
        priority_path = project_root / "ml" / "models" / "priority_model.joblib"

        for model_path in (subcategory_path, priority_path):
            if not model_path.is_file():
                raise FileNotFoundError(
                    f"Required ML triage model file is missing: {model_path}"
                )

        return joblib.load(subcategory_path), joblib.load(priority_path)

    @staticmethod
    def _predict_with_confidence(model: Any, text: str) -> tuple[str, float]:
        prediction = model.predict([text])[0]
        probabilities = model.predict_proba([text])[0]
        predicted_class_index = list(model.classes_).index(prediction)
        return str(prediction), float(probabilities[predicted_class_index])

    def triage(self, title: str, description: str) -> TriageResult:
        text = title + " " + description
        predicted_subcategory, subcategory_confidence = self._predict_with_confidence(
            self.subcategory_model, text
        )
        predicted_priority, priority_confidence = self._predict_with_confidence(
            self.priority_model, text
        )

        try:
            priority = TicketPriority(predicted_priority)
        except ValueError as error:
            raise ValueError(
                f"ML priority model returned unsupported priority: {predicted_priority!r}"
            ) from error

        return TriageResult(
            category="IT & Technology",
            subcategory=predicted_subcategory,
            priority=priority,
            confidence=(subcategory_confidence + priority_confidence) / 2,
            model_version=MODEL_VERSION,
        )
