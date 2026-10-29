import pytest

from services.resolution_service import (
    DEFAULT_CLASSIFICATION_CONFIDENCE_THRESHOLD,
    classification_confidence_threshold,
    evaluate_resolution_eligibility,
)


def assess(**overrides):
    values = {
        "category": "Software",
        "title": "Application will not launch",
        "description": "The approved application closes when opened.",
        "classification_confidence": 0.82,
        "knowledge_match_status": "MATCHED",
        "knowledge_match_confidence": 0.55,
    }
    values.update(overrides)
    return evaluate_resolution_eligibility(**values)


def test_classification_threshold_defaults_to_configured_starting_value(monkeypatch):
    monkeypatch.delenv("AI_RESOLUTION_CONFIDENCE_THRESHOLD", raising=False)
    assert classification_confidence_threshold() == DEFAULT_CLASSIFICATION_CONFIDENCE_THRESHOLD == 0.75


@pytest.mark.parametrize("value", ["-0.1", "1.1", "not-a-number"])
def test_classification_threshold_rejects_invalid_values(monkeypatch, value):
    monkeypatch.setenv("AI_RESOLUTION_CONFIDENCE_THRESHOLD", value)
    with pytest.raises(ValueError, match="between 0 and 1"):
        classification_confidence_threshold()


def test_eligible_software_requires_both_independent_scores():
    decision = assess()
    assert decision.eligible is True
    assert decision.reason == "ELIGIBLE"
    assert decision.classification_confidence == 0.82
    assert decision.knowledge_match_confidence == 0.55


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"category": "Security"}, "SECURITY_SENSITIVE"),
        ({"description": "I received a suspicious phishing message."}, "SECURITY_SENSITIVE"),
        ({"description": "The laptop has a cracked display."}, "HARDWARE_REPAIR"),
        ({"description": "The keyboard is not working."}, "HARDWARE_REPAIR"),
        ({"category": "Network"}, "NON_SOFTWARE_ISSUE"),
        ({"classification_confidence": 0.74}, "LOW_CLASSIFICATION_CONFIDENCE"),
        ({"classification_confidence": None}, "LOW_CLASSIFICATION_CONFIDENCE"),
        ({"knowledge_match_status": "NO_MATCH"}, "NO_SUFFICIENT_KNOWLEDGE"),
        ({"knowledge_match_confidence": 0.39}, "NO_SUFFICIENT_KNOWLEDGE"),
        ({"knowledge_match_confidence": None}, "NO_SUFFICIENT_KNOWLEDGE"),
    ],
)
def test_unsafe_or_low_evidence_cases_are_not_eligible(overrides, reason):
    decision = assess(**overrides)
    assert decision.eligible is False
    assert decision.reason == reason


def test_explicit_threshold_is_independent_of_knowledge_match_confidence():
    decision = assess(classification_confidence=0.70, classification_threshold=0.70)
    assert decision.eligible is True
    assert decision.classification_confidence != decision.knowledge_match_confidence