"""
Agent Registry API Service.

Provides HTTP endpoints for agent CRUD operations.
"""

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import agent_storage
from models import Agent, AgentCreate, AgentStatusUpdate, AgentUpdate
from validation import validate_agent_name

app = FastAPI(
    title="Agent Registry",
    description="CRUD operations for agent blueprints",
    version="0.1.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/agents", response_model=list[Agent])
def list_agents():
    """List all agents."""
    return agent_storage.list_agents()


@app.get("/agents/{name}", response_model=Agent)
def get_agent(name: str):
    """Get agent by name."""
    agent = agent_storage.get_agent(name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    return agent


@app.post("/agents", response_model=Agent, status_code=201)
def create_agent(data: AgentCreate):
    """Create a new agent."""
    try:
        validate_agent_name(data.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        agent = agent_storage.create_agent(data)
        return agent
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.patch("/agents/{name}", response_model=Agent)
def update_agent(name: str, updates: AgentUpdate):
    """Update an existing agent (partial update)."""
    agent = agent_storage.update_agent(name, updates)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    return agent


@app.delete("/agents/{name}", status_code=204)
def delete_agent(name: str):
    """Delete an agent."""
    if not agent_storage.delete_agent(name):
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    return None


@app.patch("/agents/{name}/status", response_model=Agent)
def update_agent_status(name: str, data: AgentStatusUpdate):
    """Update agent status (active/inactive)."""
    agent = agent_storage.set_agent_status(name, data.status)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    return agent


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("AGENT_REGISTRY_HOST", "0.0.0.0")
    port = int(os.environ.get("AGENT_REGISTRY_PORT", "8767"))

    uvicorn.run(app, host=host, port=port)
