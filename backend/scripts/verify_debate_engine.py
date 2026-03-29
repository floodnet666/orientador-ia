import asyncio
import json
import logging
from uuid import UUID
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.sql_models import User, Project
from app.api.chat import _build_graph_state
from app.agents.graph_factory import backend_graph
from langchain_core.messages import HumanMessage

async def test_debate_logic():
    print("--- DEBATE ENGINE TEST ---")
    async with AsyncSessionLocal() as db:
        # Get first user and project for context
        user_res = await db.execute(select(User).limit(1))
        user = user_res.scalar_one_or_none()
        if not user:
            print("FAILED: No user found in DB.")
            return

        proj_res = await db.execute(select(Project).limit(1))
        project = proj_res.scalar_one_or_none()
        if not project:
            print("FAILED: No project found in DB.")
            return

        print(f"Using Project: {project.id} | User: {user.email}")
        
        # Build initial state
        state = await _build_graph_state(project.id, user, db)
        
        # Simulate debate trigger message
        state["messages"] = [HumanMessage(content="/debate O impacto da IA na educação brasileira")]
        
        print("Executing Graph (astream_events)...")
        debate_triggered = False
        manifest_received = False
        
        # We only run a few events to verify the flow
        async for event in backend_graph.astream_events(state, version="v2"):
            kind = event["event"]
            name = event.get("name")
            
            # Special check for debate manifest (which is sent in chat.py but triggered by the start of the 'debate' chain)
            if kind == "on_chain_start" and name == "debate":
                print("SUCCESS: 'debate' chain started in LangGraph.")
                debate_triggered = True
                break # We don't need to run the whole LLM debate to verify the trigger
                
        if debate_triggered:
            print("VERIFICATION: Debate Mode v4 trigger logic is OPERATIONAL.")
        else:
            print("FAILED: Debate Mode was not triggered by the message.")

if __name__ == "__main__":
    asyncio.run(test_debate_logic())
