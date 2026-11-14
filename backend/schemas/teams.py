from pydantic import BaseModel


class TeamResponse(BaseModel):
    id: int
    name: str


class TeamAgentMembershipResponse(BaseModel):
    team_id: int
    team_name: str


class TeamAgentResponse(BaseModel):
    id: int
    name: str
    memberships: list[TeamAgentMembershipResponse]
