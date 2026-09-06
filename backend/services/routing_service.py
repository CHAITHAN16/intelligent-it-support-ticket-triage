from __future__ import annotations

from types import MappingProxyType


GENERAL_IT_SUPPORT = "General IT Support"

_CATEGORY_TO_TEAM = MappingProxyType(
    {
        "Network": "Network Infrastructure",
        "Security": "Security Operations",
        "Software": "Software Support",
        "Other": GENERAL_IT_SUPPORT,
    }
)


class RoutingService:
    """Routes tickets using only the category produced by AI triage."""

    @staticmethod
    def route_category(category: str | None) -> str:
        """Return the simulated support team for a predicted category."""
        return _CATEGORY_TO_TEAM.get(category, GENERAL_IT_SUPPORT)
