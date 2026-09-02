from fastapi import FastAPI


app = FastAPI(title="Intelligent IT Support Ticket Triage and Routing")


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "IT Support Backend",
    }
