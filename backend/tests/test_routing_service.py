import pytest

from services.routing_service import RoutingService
from services.triage_service import TriageService


@pytest.mark.parametrize(
    ("category", "expected_team"),
    [
        ("Network", "Network Infrastructure"),
        ("Security", "Security Operations"),
        ("Software", "Software Support"),
        ("Other", "General IT Support"),
        ("Unknown", "General IT Support"),
    ],
)
def test_route_category(category, expected_team):
    assert RoutingService.route_category(category) == expected_team


@pytest.mark.parametrize(
    ("title", "description", "expected_category", "expected_priority", "expected_team"),
    [
        (
            "VPN connection keeps dropping",
            "I cannot maintain a connection to the company VPN and the network keeps disconnecting.",
            "Network",
            "MEDIUM",
            "Network Infrastructure",
        ),
        (
            "Critical security breach detected",
            "We detected unauthorized access and suspicious malware activity on a company system.",
            "Security",
            "HIGH",
            "Security Operations",
        ),
        (
            "Application keeps crashing",
            "The internal application crashes whenever I try to open the reporting module.",
            "Software",
            "HIGH",
            "Software Support",
        ),
        (
            "Marketing campaign question",
            "I need information about our upcoming marketing campaign.",
            "Other",
            "MEDIUM",
            "General IT Support",
        ),
    ],
)
def test_model_triage_then_routing(
    title,
    description,
    expected_category,
    expected_priority,
    expected_team,
):
    triage_result = TriageService().triage(title, description)

    assert triage_result.category == expected_category
    assert triage_result.priority.value == expected_priority
    assert RoutingService.route_category(triage_result.category) == expected_team
