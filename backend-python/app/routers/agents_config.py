from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from app.database import get_session
from app.models.agent import Agent, AgentCreate, AgentRead, AgentUpdate, AgentSpec

router = APIRouter(prefix="/agents", tags=["agents"])

@router.post("/", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
def create_agent(agent: AgentCreate, session: Session = Depends(get_session)):
    db_agent = Agent.model_validate(agent)
    # Ensure spec is converted to dict for storage if it's a model
    if isinstance(db_agent.spec, AgentSpec):
        db_agent.spec = db_agent.spec.model_dump()
    
    session.add(db_agent)
    session.commit()
    session.refresh(db_agent)
    return db_agent

@router.get("/", response_model=List[AgentRead])
def list_agents(session: Session = Depends(get_session)):
    agents = session.exec(select(Agent)).all()
    return agents

@router.get("/{agent_id}", response_model=AgentRead)
def get_agent(agent_id: int, session: Session = Depends(get_session)):
    db_agent = session.get(Agent, agent_id)
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return db_agent

@router.patch("/{agent_id}", response_model=AgentRead)
def update_agent(agent_id: int, agent: AgentUpdate, session: Session = Depends(get_session)):
    db_agent = session.get(Agent, agent_id)
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent_data = agent.model_dump(exclude_unset=True)
    for key, value in agent_data.items():
        if key == "spec" and value is not None:
            # Handle recursive update of spec if needed, or just replace
            db_agent.spec = value.model_dump() if hasattr(value, "model_dump") else value
        else:
            setattr(db_agent, key, value)
    
    session.add(db_agent)
    session.commit()
    session.refresh(db_agent)
    return db_agent

@router.delete("/{agent_id}")
def delete_agent(agent_id: int, session: Session = Depends(get_session)):
    db_agent = session.get(Agent, agent_id)
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    session.delete(db_agent)
    session.commit()
    return {"ok": True}
