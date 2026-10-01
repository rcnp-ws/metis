# backend/src/metis/central/main.py

from fastapi import FastAPI
from metis.central.api.agents import router as agents_router
from metis.central.connections.registry import AgentRegistry


def create_app() -> FastAPI:
    app = FastAPI(title="Metis Central API")

    app.state.agent_registry = AgentRegistry()
    app.include_router(agents_router)

    return app
