"""
Enhanced FastAPI server with advanced AI agents.

Features:
- Safety layers (input/output validation, rate limiting)
- A2A communication workflow
- Sentiment analysis
- Knowledge base integration
- Comprehensive error handling
- Monitoring and metrics
"""

import os
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Import safety layers
from safety.input_validator import InputValidator, ValidationResult
from safety.output_validator import OutputValidator, OutputValidationResult
from safety.rate_limiter import RateLimiter, RateLimitExceeded, UserTier

# Import A2A framework and agents
from agents.a2a_manager import A2AManager
from agents.triage_agent import TriageAgent, Ticket
from agents.retrieval_agent import RetrievalAgent
from agents.escalation_agent import EscalationAgent

# Import database
from db.connection import init_db, get_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Pydantic models
class QueryRequest(BaseModel):
    """Request model for agent queries."""
    text: str = Field(..., min_length=1, max_length=5000, description="User query text")
    user_email: Optional[str] = Field(None, description="User email for context")
    session_id: str = Field(default="default", description="Session identifier")


class QueryResponse(BaseModel):
    """Response model for agent queries."""
    status: str = Field(..., description="Response status (success, error, escalated)")
    message: str = Field(..., description="Response message")
    confidence: Optional[float] = Field(None, description="Confidence score (0.0-1.0)")
    diagnostic_reasoning: Optional[str] = Field(None, description="Diagnostic reasoning")
    ticket_id: Optional[str] = Field(None, description="Ticket ID for tracking")
    should_escalate: bool = Field(default=False, description="Whether human review is needed")


# Global instances
input_validator: Optional[InputValidator] = None
output_validator: Optional[OutputValidator] = None
rate_limiter: Optional[RateLimiter] = None
a2a_manager: Optional[A2AManager] = None
triage_agent: Optional[TriageAgent] = None
retrieval_agent: Optional[RetrievalAgent] = None
escalation_agent: Optional[EscalationAgent] = None
session_service: Optional[InMemorySessionService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    logger.info("Starting up AI Agents system...")
    
    global input_validator, output_validator, rate_limiter
    global a2a_manager, triage_agent, retrieval_agent, escalation_agent
    global session_service
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Initialize safety layers
    input_validator = InputValidator(max_length=5000)
    output_validator = OutputValidator(min_confidence=0.6)
    rate_limiter = RateLimiter(
        global_limit_per_minute=1000,
        enable_global_limit=True
    )
    logger.info("Safety layers initialized")
    
    # Initialize A2A manager
    a2a_manager = A2AManager()
    logger.info("A2A manager initialized")
    
    # Initialize agents with database connection
    with get_db_connection() as conn:
        # Create agents
        triage_agent = TriageAgent("triage", a2a_manager, conn)
        retrieval_agent = RetrievalAgent("retrieval", a2a_manager, conn)
        escalation_agent = EscalationAgent(
            "escalation",
            a2a_manager,
            conn,
            skip_email_for={"alice@example.com", "bob@example.com"}
        )
    
    logger.info("Agents initialized: triage, retrieval, escalation")
    
    # Initialize session service
    session_service = InMemorySessionService()
    logger.info("Session service initialized")
    
    logger.info("✅ AI Agents system ready!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Agents system...")
    
    # Cleanup agents
    if triage_agent:
        triage_agent.cleanup()
    if retrieval_agent:
        retrieval_agent.cleanup()
    if escalation_agent:
        escalation_agent.cleanup()
    
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Advanced AI Agents API",
    description="Production-ready multi-agent customer support system",
    version="2.0.0",
    lifespan=lifespan
)


# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    request_id = str(uuid.uuid4())
    logger.info(f"[{request_id}] {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    logger.info(f"[{request_id}] Status: {response.status_code}")
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agents": a2a_manager.list_agents() if a2a_manager else [],
        "version": "2.0.0"
    }


@app.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest, http_request: Request):
    """
    Main endpoint for agent queries.
    
    Workflow:
    1. Input validation (safety layer)
    2. Rate limiting check
    3. Sentiment analysis
    4. A2A workflow: Triage → Retrieval → Escalation
    5. Output validation (safety layer)
    6. Return response
    """
    try:
        # Step 1: Input validation
        validation_result: ValidationResult = input_validator.validate(request.text)
        
        if not validation_result.is_valid:
            logger.warning(f"Input validation failed: {validation_result.issues}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Input validation failed",
                    "issues": [issue.message for issue in validation_result.issues],
                    "risk_score": validation_result.risk_score
                }
            )
        
        # Use sanitized input
        sanitized_text = validation_result.sanitized_input
        
        # Step 2: Rate limiting
        user_id = request.user_email or http_request.client.host
        user_tier = UserTier.STANDARD  # Default, should be fetched from DB
        
        try:
            rate_limiter.check_rate_limit(user_id, user_tier)
        except RateLimitExceeded as e:
            logger.warning(f"Rate limit exceeded for {user_id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "retry_after": e.retry_after,
                    "limit_type": e.limit_type
                }
            )
        
        # Step 3: Sentiment analysis (simple keyword-based)
        sentiment = _analyze_sentiment(sanitized_text)
        
        # Step 4: Create ticket and process through A2A workflow
        ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
        ticket = Ticket(
            ticket_id=ticket_id,
            text=sanitized_text,
            user_ref=request.user_email or "anonymous"
        )
        ticket.context["sentiment"] = sentiment
        ticket.context["session_id"] = request.session_id
        
        logger.info(f"Processing ticket {ticket_id} for user {user_id}")
        
        # Process through triage agent (will trigger A2A workflow)
        with get_db_connection() as conn:
            # Update agent database connections
            triage_agent.db = conn
            retrieval_agent.db = conn
            escalation_agent.db = conn
            
            result = triage_agent.process_ticket(ticket)
        
        # Step 5: Output validation
        response_text = ticket.context.get("resolution", "Ticket processed successfully")
        confidence = ticket.context.get("confidence_score", 0.0)
        
        output_result: OutputValidationResult = output_validator.validate(
            response_text,
            confidence,
            context={"user_email": request.user_email}
        )
        
        if not output_result.is_safe:
            logger.error(f"Output validation failed for ticket {ticket_id}")
            # Use fallback response
            response_text = "I apologize, but I need to escalate this to a human agent for proper assistance."
            output_result.should_escalate = True
        
        # Use sanitized output
        response_text = output_result.sanitized_output
        
        # Step 6: Build response
        return QueryResponse(
            status=ticket.status.lower(),
            message=response_text,
            confidence=confidence,
            diagnostic_reasoning=ticket.context.get("diagnostic_reasoning"),
            ticket_id=ticket_id,
            should_escalate=output_result.should_escalate or ticket.status == "Escalated"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error processing query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal server error",
                "message": "An unexpected error occurred. Please try again later."
            }
        )


def _analyze_sentiment(text: str) -> str:
    """
    Simple sentiment analysis based on keywords.
    
    In production, use a dedicated sentiment analysis model.
    
    Args:
        text: Text to analyze
    
    Returns:
        Sentiment label (POSITIVE, NEUTRAL, NEGATIVE, ANGRY)
    """
    text_lower = text.lower()
    
    # Angry keywords
    angry_keywords = ["angry", "furious", "outraged", "terrible", "worst", "hate", "disgusting"]
    if any(kw in text_lower for kw in angry_keywords):
        return "ANGRY"
    
    # Negative keywords
    negative_keywords = ["bad", "poor", "disappointed", "unhappy", "problem", "issue", "broken"]
    if any(kw in text_lower for kw in negative_keywords):
        return "NEGATIVE"
    
    # Positive keywords
    positive_keywords = ["great", "excellent", "love", "amazing", "perfect", "thank"]
    if any(kw in text_lower for kw in positive_keywords):
        return "POSITIVE"
    
    return "NEUTRAL"


@app.get("/metrics")
async def get_metrics():
    """
    Get system metrics.
    
    Returns:
        Dictionary of metrics
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get analytics
            cursor.execute("SELECT metric, value FROM analytics")
            analytics = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Get feedback stats
            cursor.execute("""
                SELECT 
                    status,
                    COUNT(*) as count,
                    AVG(confidence_score) as avg_confidence
                FROM feedback_loop
                GROUP BY status
            """)
            feedback_stats = [
                {"status": row[0], "count": row[1], "avg_confidence": row[2]}
                for row in cursor.fetchall()
            ]
            
            return {
                "analytics": analytics,
                "feedback_stats": feedback_stats,
                "agents": a2a_manager.list_agents() if a2a_manager else []
            }
    except Exception as e:
        logger.exception(f"Error fetching metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching metrics"
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
