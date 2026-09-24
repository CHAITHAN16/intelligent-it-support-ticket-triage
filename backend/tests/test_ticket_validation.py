import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from pydantic import ValidationError

from schemas.tickets import TicketCreate, TicketUpdateRequest


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", ""),
        ("title", "   "),
        ("title", "x" * 256),
        ("description", ""),
        ("description", " \t\n "),
    ],
)
def test_ticket_create_rejects_invalid_text(field, value):
    payload = {"title": "Valid title", "description": "Valid description", "creator_id": 1}
    payload[field] = value

    with pytest.raises(ValidationError):
        TicketCreate(**payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", " "),
        ("title", "x" * 256),
        ("description", "\t"),
        ("category", ""),
        ("category", "x" * 101),
        ("subcategory", "   "),
        ("subcategory", "x" * 101),
        ("assigned_team_id", 0),
        ("assigned_team_id", -2),
        ("priority", "IMMEDIATE"),
        ("status", "PENDING"),
    ],
)
def test_ticket_update_rejects_invalid_values(field, value):
    with pytest.raises(ValidationError):
        TicketUpdateRequest(**{field: value})


def test_ticket_update_accepts_omitted_and_nullable_fields():
    assert TicketUpdateRequest().model_dump(exclude_unset=True) == {}
    assert TicketUpdateRequest(category=None).category is None
    assert TicketUpdateRequest(assigned_team_id=None).assigned_team_id is None
