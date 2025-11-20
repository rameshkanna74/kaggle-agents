import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from agents.coordinator import coordinator_agent
from db.connection import init_db

app = FastAPI(title="ADK Customer Support Agent")

# Initialize session service
session_service = InMemorySessionService()

# Initialize runner
runner = Runner(
    agent=coordinator_agent,
    session_service=session_service,
    app_name="customer_support_agent"
)

USER_ID = "default_user"

class QueryRequest(BaseModel):
    text: str
    user_email: str | None = None
    session_id: str = "default"

@app.on_event("startup")
def on_startup():
    init_db()

@app.post("/query")
async def query_agent(request: QueryRequest):
    """
    Endpoint to interact with the multi-agent system.
    """
    try:
        # Prepare the query
        prompt = request.text
        if request.user_email:
            prompt = f"[User: {request.user_email}] {prompt}"
        
        # Get or create session
        try:
            session = await session_service.create_session(
                app_name=runner.app_name,
                user_id=USER_ID,
                session_id=request.session_id
            )
        except:
            session = await session_service.get_session(
                app_name=runner.app_name,
                user_id=USER_ID,
                session_id=request.session_id
            )
        
        # Convert query to ADK Content format
        query_content = types.Content(
            role="user",
            parts=[types.Part(text=prompt)]
        )
        
        # Run the agent and collect response
        final_response = None
        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=session.id,
            new_message=query_content
        ):
            if event.content and event.content.parts:
                if event.content.parts[0].text and event.content.parts[0].text != "None":
                    final_response = event.content.parts[0].text
        
        return {"response": final_response or "No response generated"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
