from fastapi import FastAPI

from routers.teams import router as teams_router
from routers.tickets import router as tickets_router


app = FastAPI(title="Intelligent IT Support Ticket Triage and Routing")
app.include_router(tickets_router)
app.include_router(teams_router)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "IT Support Backend",
    }
