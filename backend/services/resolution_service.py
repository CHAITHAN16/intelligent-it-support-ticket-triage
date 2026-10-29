from __future__ import annotations

import os
import re
from dataclasses import dataclass

from services.knowledge_base_service import LOW_CONFIDENCE_THRESHOLD


DEFAULT_CLASSIFICATION_CONFIDENCE_THRESHOLD = 0.75
_SECURITY_SIGNALS = re.compile(
    r"\b(security|phish(?:ing)?|malware|ransomware|breach|unauthori[sz]ed|"
    r"compromis(?:ed|e)|suspicious login|data leak|stolen credentials)\b",
    re.IGNORECASE,
)
_HARDWARE_REPAIR_SIGNALS = re.compile(
    r"\b(physical damage|broken (?:screen|hinge|keyboard|port)|"
    r"won't power on|will not power on|does not power on|dead battery|"
    r"battery swelling|cracked display|liquid damage|hardware repair)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ResolutionDecision:
    eligible: bool
    reason: str
    classification_confidence: float | None
    knowledge_match_confidence: float | None


def classification_confidence_threshold() -> float:
    raw_threshold = os.getenv(
        "AI_RESOLUTION_CONFIDENCE_THRESHOLD",
        str(DEFAULT_CLASSIFICATION_CONFIDENCE_THRESHOLD),
    )
    try:
        threshold = float(raw_threshold)
    except ValueError as error:
        raise ValueError("AI_RESOLUTION_CONFIDENCE_THRESHOLD must be between 0 and 1") from error
    if not 0 <= threshold <= 1:
        raise ValueError("AI_RESOLUTION_CONFIDENCE_THRESHOLD must be between 0 and 1")
    return threshold


def evaluate_resolution_eligibility(
    *,
    category: str | None,
    title: str,
    description: str,
    classification_confidence: float | None,
    knowledge_match_status: str | None,
    knowledge_match_confidence: float | None,
    classification_threshold: float | None = None,
) -> ResolutionDecision:
    """Decide eligibility using separate, deliberately uncalibrated model and KB scores."""
    threshold = (
        classification_confidence_threshold()
        if classification_threshold is None
        else classification_threshold
    )
    text = f"{title}\n{description}"

    if (category or "").strip().lower() == "security" or _SECURITY_SIGNALS.search(text):
        reason = "SECURITY_SENSITIVE"
    elif (category or "").strip().lower() == "hardware" or _HARDWARE_REPAIR_SIGNALS.search(text):
        reason = "HARDWARE_REPAIR"
    elif (category or "").strip().lower() != "software":
        reason = "NON_SOFTWARE_ISSUE"
    elif classification_confidence is None or classification_confidence < threshold:
        reason = "LOW_CLASSIFICATION_CONFIDENCE"
    elif (
        knowledge_match_status != "MATCHED"
        or knowledge_match_confidence is None
        or knowledge_match_confidence < LOW_CONFIDENCE_THRESHOLD
    ):
        reason = "NO_SUFFICIENT_KNOWLEDGE"
    else:
        return ResolutionDecision(
            eligible=True,
            reason="ELIGIBLE",
            classification_confidence=classification_confidence,
            knowledge_match_confidence=knowledge_match_confidence,
        )

    return ResolutionDecision(
        eligible=False,
        reason=reason,
        classification_confidence=classification_confidence,
        knowledge_match_confidence=knowledge_match_confidence,
    )