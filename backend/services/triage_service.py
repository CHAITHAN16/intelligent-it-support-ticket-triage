from pydantic import BaseModel, Field

from models import TicketPriority


class TriageResult(BaseModel):
    category: str
    subcategory: str
    priority: TicketPriority
    confidence: float = Field(ge=0.0, le=1.0)
    model_version: str


class TriageService:
    """Classifies tickets through a temporary deterministic implementation."""

    MODEL_VERSION = "mock-v1"

    def triage(self, title: str, description: str) -> TriageResult:
        # TODO: Replace this keyword matcher with the trained classifier.
        text = f"{title} {description}".lower()

        if any(keyword in text for keyword in ("vpn", "network", "internet", "wifi")):
            return TriageResult(
                category="Network",
                subcategory="Connectivity",
                priority=TicketPriority.HIGH,
                confidence=0.90,
                model_version=self.MODEL_VERSION,
            )

        if any(keyword in text for keyword in ("password", "login", "sign in", "access")):
            return TriageResult(
                category="Access",
                subcategory="Authentication",
                priority=TicketPriority.MEDIUM,
                confidence=0.85,
                model_version=self.MODEL_VERSION,
            )

        return TriageResult(
            category="General IT",
            subcategory="General Support",
            priority=TicketPriority.LOW,
            confidence=0.50,
            model_version=self.MODEL_VERSION,
        )
