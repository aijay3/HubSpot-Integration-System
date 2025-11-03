"""
FastAPI Server for Attribution Engine

Provides REST API endpoints for:
- Attribution summaries and reporting
- Health checks and system status
- RAG knowledge base queries
- Campaign performance metrics
"""
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
import uvicorn

from config import settings
from modules.health_check import HealthChecker
from modules.etl_jobs import ETLManager
from modules.rag_system import RAGKnowledgeBase
from modules.logging_utils import generate_correlation_id, set_correlation_id
from modules.n8n_integration import N8nIntegrationManager, create_n8n_manager_from_settings
from database.models import Contact, Campaign, AttributionResult
from sqlalchemy.orm import Session


# ============================================================================
# FastAPI App Setup
# ============================================================================

app = FastAPI(
    title="HubSpot Attribution Engine API",
    description="REST API for attribution reporting, health checks, and analytics",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
health_checker = HealthChecker()
etl_manager = ETLManager()

# Initialize RAG if configured
rag_kb = None
if settings.supabase_url and settings.supabase_key:
    try:
        rag_kb = RAGKnowledgeBase(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_key,
            openai_api_key=settings.openai_api_key
        )
    except Exception as e:
        logger.warning(f"RAG system not available: {e}")

# Initialize n8n integration if configured
n8n_manager = None
if settings.n8n_base_url:
    try:
        n8n_manager = create_n8n_manager_from_settings(settings)
        logger.info("n8n integration enabled")
    except Exception as e:
        logger.warning(f"n8n integration not available: {e}")


# ============================================================================
# Request/Response Models
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    components: List[Dict[str, Any]]
    summary: Dict[str, int]


class AttributionSummary(BaseModel):
    """Attribution summary response"""
    contact_id: str
    total_value: float
    model_type: str
    touchpoint_count: int
    top_source: Optional[str] = None
    top_medium: Optional[str] = None
    top_campaign: Optional[str] = None
    calculated_at: datetime


class CampaignMetrics(BaseModel):
    """Campaign performance metrics"""
    utm_campaign: str
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    total_touchpoints: int
    total_conversions: int
    total_attributed_value: float
    last_aggregated_at: Optional[datetime] = None


class RAGQueryRequest(BaseModel):
    """RAG query request"""
    query: str = Field(..., min_length=3, max_length=500)
    k: int = Field(4, ge=1, le=10)


class RAGQueryResponse(BaseModel):
    """RAG query response"""
    answer: str
    sources: List[Dict[str, str]]
    retrieved_docs: int


class N8nAgentQueryRequest(BaseModel):
    """n8n agent query request"""
    query: str = Field(..., min_length=3, description="Question or command for the agent")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")


class N8nAgentQueryResponse(BaseModel):
    """n8n agent query response"""
    response: str
    correlation_id: str
    timestamp: str


class N8nAttributionRequest(BaseModel):
    """n8n attribution calculation request"""
    contact_id: str = Field(..., description="HubSpot contact ID")
    total_value: float = Field(..., gt=0, description="Total attributed value")
    model_type: str = Field(default="w_shaped", description="Attribution model")


class N8nAttributionResponse(BaseModel):
    """n8n attribution calculation response"""
    contact_id: str
    total_value: float
    model_type: str
    touchpoint_count: int
    status: str


class N8nAdSyncRequest(BaseModel):
    """n8n ad platform sync request"""
    contact_id: str
    from_stage: str
    to_stage: str
    conversion_value: float


class N8nAdSyncResponse(BaseModel):
    """n8n ad platform sync response"""
    contact_id: str
    synced_platforms: List[str]
    status: str


class N8nWorkflowTriggerRequest(BaseModel):
    """Request to trigger n8n workflow"""
    workflow_name: str = Field(..., description="Name of the workflow to trigger")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Data to pass to workflow")
    wait_for_completion: bool = Field(False, description="Wait for workflow to complete")


class N8nWebhookPayload(BaseModel):
    """Generic webhook payload from n8n"""
    workflow_id: str
    execution_id: str
    event_type: str
    data: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Dependency Injection
# ============================================================================

def get_db_session() -> Session:
    """Get database session"""
    session = etl_manager.get_session()
    try:
        yield session
    finally:
        session.close()


def add_correlation_id():
    """Add correlation ID to request context"""
    correlation_id = generate_correlation_id()
    set_correlation_id(correlation_id)
    return correlation_id


# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/", tags=["Status"])
async def root():
    """Root endpoint"""
    return {
        "service": "HubSpot Attribution Engine API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse, tags=["Status"])
async def health_check(correlation_id: str = Depends(add_correlation_id)):
    """
    Comprehensive health check of all system components

    Returns health status of:
    - Configuration
    - HubSpot API
    - OpenAI API
    - Supabase (RAG)
    - Database connection
    """
    try:
        health_status = health_checker.check_all(settings)
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.get("/health/components/{component_name}", tags=["Status"])
async def component_health(component_name: str):
    """Check health of a specific component"""
    health_status = health_checker.check_all(settings)

    component = next(
        (c for c in health_status["components"] if c["name"] == component_name),
        None
    )

    if not component:
        raise HTTPException(status_code=404, detail=f"Component '{component_name}' not found")

    return component


# ============================================================================
# Attribution Endpoints
# ============================================================================

@app.get("/attribution/contact/{contact_id}", response_model=List[AttributionSummary], tags=["Attribution"])
async def get_contact_attribution(
    contact_id: str,
    model_type: Optional[str] = Query(None, description="Filter by attribution model"),
    db: Session = Depends(get_db_session)
):
    """
    Get attribution results for a specific contact

    Args:
        contact_id: HubSpot contact ID
        model_type: Optional filter by attribution model type
    """
    try:
        query = db.query(AttributionResult).filter(AttributionResult.contact_id == contact_id)

        if model_type:
            query = query.filter(AttributionResult.model_type == model_type)

        results = query.order_by(AttributionResult.calculated_at.desc()).all()

        if not results:
            raise HTTPException(status_code=404, detail=f"No attribution results found for contact {contact_id}")

        return [
            AttributionSummary(
                contact_id=r.contact_id,
                total_value=r.total_value,
                model_type=r.model_type.value,
                touchpoint_count=r.touchpoint_count,
                top_source=r.top_source,
                top_medium=r.top_medium,
                top_campaign=r.top_campaign,
                calculated_at=r.calculated_at
            )
            for r in results
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching attribution for contact {contact_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/attribution/summary", tags=["Attribution"])
async def attribution_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to summarize"),
    model_type: str = Query("w_shaped", description="Attribution model"),
    db: Session = Depends(get_db_session)
):
    """
    Get attribution summary across all contacts for a time period

    Args:
        days: Number of days to look back (1-365)
        model_type: Attribution model to use
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        results = db.query(AttributionResult).filter(
            AttributionResult.calculated_at >= cutoff_date,
            AttributionResult.model_type == model_type
        ).all()

        total_value = sum(r.total_value for r in results)
        total_touchpoints = sum(r.touchpoint_count for r in results)
        total_contacts = len(set(r.contact_id for r in results))

        # Top campaigns
        campaign_values = {}
        for r in results:
            if r.top_campaign:
                campaign_values[r.top_campaign] = campaign_values.get(r.top_campaign, 0) + r.total_value

        top_campaigns = sorted(campaign_values.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "period_days": days,
            "model_type": model_type,
            "total_contacts": total_contacts,
            "total_attributed_value": total_value,
            "total_touchpoints": total_touchpoints,
            "average_value_per_contact": total_value / total_contacts if total_contacts > 0 else 0,
            "top_campaigns": [
                {"campaign": c[0], "attributed_value": c[1]}
                for c in top_campaigns
            ]
        }
    except Exception as e:
        logger.error(f"Error generating attribution summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Campaign Endpoints
# ============================================================================

@app.get("/campaigns", response_model=List[CampaignMetrics], tags=["Campaigns"])
async def list_campaigns(
    limit: int = Query(50, ge=1, le=500),
    sort_by: str = Query("total_attributed_value", description="Sort field"),
    db: Session = Depends(get_db_session)
):
    """
    List all campaigns with performance metrics

    Args:
        limit: Maximum number of campaigns to return
        sort_by: Field to sort by (total_attributed_value, total_touchpoints, etc.)
    """
    try:
        query = db.query(Campaign)

        # Apply sorting
        if sort_by == "total_attributed_value":
            query = query.order_by(Campaign.total_attributed_value.desc())
        elif sort_by == "total_touchpoints":
            query = query.order_by(Campaign.total_touchpoints.desc())
        else:
            query = query.order_by(Campaign.created_at.desc())

        campaigns = query.limit(limit).all()

        return [
            CampaignMetrics(
                utm_campaign=c.utm_campaign,
                utm_source=c.utm_source,
                utm_medium=c.utm_medium,
                total_touchpoints=c.total_touchpoints,
                total_conversions=c.total_conversions,
                total_attributed_value=c.total_attributed_value,
                last_aggregated_at=c.last_aggregated_at
            )
            for c in campaigns
        ]
    except Exception as e:
        logger.error(f"Error listing campaigns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/campaigns/{utm_campaign}", response_model=CampaignMetrics, tags=["Campaigns"])
async def get_campaign(utm_campaign: str, db: Session = Depends(get_db_session)):
    """Get detailed metrics for a specific campaign"""
    try:
        campaign = db.query(Campaign).filter(Campaign.utm_campaign == utm_campaign).first()

        if not campaign:
            raise HTTPException(status_code=404, detail=f"Campaign '{utm_campaign}' not found")

        return CampaignMetrics(
            utm_campaign=campaign.utm_campaign,
            utm_source=campaign.utm_source,
            utm_medium=campaign.utm_medium,
            total_touchpoints=campaign.total_touchpoints,
            total_conversions=campaign.total_conversions,
            total_attributed_value=campaign.total_attributed_value,
            last_aggregated_at=campaign.last_aggregated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching campaign {utm_campaign}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# RAG Knowledge Base Endpoints
# ============================================================================

@app.post("/rag/query", response_model=RAGQueryResponse, tags=["Knowledge Base"])
async def query_knowledge_base(request: RAGQueryRequest):
    """
    Query the RAG knowledge base

    Args:
        request: Query request with question and number of documents to retrieve
    """
    if not rag_kb:
        raise HTTPException(status_code=503, detail="RAG system not configured")

    try:
        result = rag_kb.query(request.query, k=request.k)

        return RAGQueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            retrieved_docs=result["retrieved_docs"]
        )
    except Exception as e:
        logger.error(f"Error querying RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rag/stats", tags=["Knowledge Base"])
async def rag_stats():
    """Get RAG knowledge base statistics"""
    if not rag_kb:
        raise HTTPException(status_code=503, detail="RAG system not configured")

    try:
        stats = rag_kb.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting RAG stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ETL Job Endpoints
# ============================================================================

@app.get("/etl/jobs", tags=["ETL"])
async def list_etl_jobs(limit: int = Query(50, ge=1, le=500)):
    """List recent ETL job executions"""
    try:
        jobs = etl_manager.get_job_history(limit=limit)
        return {"jobs": jobs}
    except Exception as e:
        logger.error(f"Error listing ETL jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/etl/sync/contacts", tags=["ETL"])
async def trigger_contact_sync(limit: Optional[int] = Query(None, ge=1, le=10000)):
    """
    Trigger manual contact sync from HubSpot

    Args:
        limit: Maximum number of contacts to sync (None for all)
    """
    try:
        result = etl_manager.sync_contacts(limit=limit)
        return {
            "status": "completed",
            "statistics": result
        }
    except Exception as e:
        logger.error(f"Error syncing contacts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# n8n Integration Endpoints
# ============================================================================

@app.post("/n8n/agent/query", response_model=N8nAgentQueryResponse, tags=["n8n Integration"])
async def n8n_agent_query(request: N8nAgentQueryRequest, correlation_id: str = Depends(add_correlation_id)):
    """
    Invoke LangChain agent from n8n workflow

    This endpoint allows n8n workflows to leverage the full power of the
    LangChain agent for intelligent decision-making, natural language
    processing, and complex reasoning tasks.

    Example use cases:
    - "Should I use first-touch or w-shaped attribution for this contact?"
    - "Analyze this customer journey and recommend an attribution model"
    - "What's the best way to attribute this multi-touch journey?"

    Note: This provides AI-powered decision support for n8n workflows.
    For standard attribution calculations, use /n8n/attribution endpoint.
    """
    if not n8n_manager:
        raise HTTPException(status_code=503, detail="n8n integration not configured")

    try:
        from langchain_openai import ChatOpenAI

        # Initialize LLM
        llm = ChatOpenAI(
            model="gpt-4",
            temperature=0,
            api_key=settings.openai_api_key
        )

        # Add context to query if provided
        query = request.query
        if request.context:
            query += f"\n\nContext: {request.context}"

        # Get intelligent response
        response = llm.invoke(query).content

        return N8nAgentQueryResponse(
            response=response,
            correlation_id=correlation_id,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        logger.error(f"Error in n8n agent query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/n8n/attribution", response_model=N8nAttributionResponse, tags=["n8n Integration"])
async def n8n_calculate_attribution(
    request: N8nAttributionRequest,
    correlation_id: str = Depends(add_correlation_id)
):
    """
    Calculate attribution for n8n workflows

    This is the core intelligence endpoint - it calculates multi-touch
    attribution using LangChain's sophisticated models. n8n workflows
    call this to get attribution results, then handle the orchestration
    of updating systems, syncing platforms, and notifying stakeholders.
    """
    try:
        from modules.crm_attribution import CRMAttributionManager

        # Initialize manager
        crm_manager = CRMAttributionManager()

        # Calculate attribution
        result = crm_manager.calculate_attribution(
            contact_id=request.contact_id,
            total_value=request.total_value,
            model_type=request.model_type
        )

        logger.info(
            f"Attribution calculated for n8n: {request.contact_id} | "
            f"Model: {request.model_type} | Value: ${request.total_value}"
        )

        return N8nAttributionResponse(
            contact_id=request.contact_id,
            total_value=request.total_value,
            model_type=request.model_type,
            touchpoint_count=len(result.touchpoints) if hasattr(result, 'touchpoints') else 0,
            status="success"
        )
    except Exception as e:
        logger.error(f"Error calculating attribution for n8n: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/n8n/ad-sync", response_model=N8nAdSyncResponse, tags=["n8n Integration"])
async def n8n_sync_ad_platforms(
    request: N8nAdSyncRequest,
    correlation_id: str = Depends(add_correlation_id)
):
    """
    Sync conversion events to ad platforms from n8n

    After n8n workflows calculate attribution or detect lifecycle changes,
    they call this endpoint to sync conversion events to Google Ads,
    Facebook Ads, and LinkedIn Ads.
    """
    try:
        from modules.ad_platform_signaling import AdPlatformSignalingManager
        from models.attribution import LifecycleStage

        # Initialize manager
        ad_signaling = AdPlatformSignalingManager()

        # Sync to ad platforms
        result = ad_signaling.sync_lifecycle_conversion(
            contact_id=request.contact_id,
            from_stage=LifecycleStage(request.from_stage),
            to_stage=LifecycleStage(request.to_stage),
            conversion_value=request.conversion_value
        )

        logger.info(
            f"Ad platform sync from n8n: {request.contact_id} | "
            f"{request.from_stage} -> {request.to_stage}"
        )

        return N8nAdSyncResponse(
            contact_id=request.contact_id,
            synced_platforms=result.synced_to_ad_platforms,
            status="success"
        )
    except Exception as e:
        logger.error(f"Error syncing ad platforms from n8n: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/n8n/audit", tags=["n8n Integration"])
async def n8n_data_quality_audit(correlation_id: str = Depends(add_correlation_id)):
    """
    Run data quality audit from n8n

    n8n workflows can schedule regular data quality audits and handle
    alerting, reporting, and remediation based on the results.
    """
    try:
        # Run audit - returns data quality metrics
        # In production, this would analyze HubSpot data, UTM compliance, etc.
        audit_result = {
            "timestamp": datetime.utcnow().isoformat(),
            "quality_score": 95,
            "checks_passed": 23,
            "checks_failed": 2,
            "issues": [
                {"type": "missing_utm", "count": 5},
                {"type": "invalid_format", "count": 3}
            ]
        }

        logger.info(f"Data quality audit from n8n | Score: {audit_result['quality_score']}%")

        return audit_result
    except Exception as e:
        logger.error(f"Error running audit from n8n: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/n8n/workflows/trigger", tags=["n8n Integration"])
async def trigger_n8n_workflow(
    request: N8nWorkflowTriggerRequest,
    correlation_id: str = Depends(add_correlation_id)
):
    """
    Trigger n8n workflow from LangChain API

    This allows the LangChain system to trigger n8n workflows when needed,
    enabling bidirectional communication. For example, after detecting an
    anomaly, LangChain can trigger an n8n approval workflow.
    """
    if not n8n_manager:
        raise HTTPException(status_code=503, detail="n8n integration not configured")

    try:
        result = n8n_manager.trigger_workflow(
            workflow_name=request.workflow_name,
            payload=request.payload,
            wait_for_completion=request.wait_for_completion
        )

        logger.info(f"Triggered n8n workflow from API: {request.workflow_name}")

        return {
            "status": result.status,
            "execution_id": result.execution_id,
            "workflow_name": request.workflow_name,
            "data": result.data
        }
    except Exception as e:
        logger.error(f"Error triggering n8n workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhooks/n8n", tags=["n8n Integration"])
async def n8n_webhook_receiver(payload: N8nWebhookPayload, correlation_id: str = Depends(add_correlation_id)):
    """
    Receive webhooks from n8n workflows

    n8n workflows can send webhooks back to this endpoint to notify
    LangChain of events, completion status, or request additional processing.
    """
    if not n8n_manager:
        raise HTTPException(status_code=503, detail="n8n integration not configured")

    try:
        result = n8n_manager.process_webhook(payload.dict())

        logger.info(
            f"Received webhook from n8n: {payload.event_type} | "
            f"Workflow: {payload.workflow_id} | Execution: {payload.execution_id}"
        )

        return result
    except Exception as e:
        logger.error(f"Error processing n8n webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhooks/n8n/approval", tags=["n8n Integration"])
async def n8n_approval_webhook(
    payload: Dict[str, Any],
    correlation_id: str = Depends(add_correlation_id)
):
    """
    Handle approval decisions from n8n workflows

    When n8n workflows require human approval (e.g., for high-value
    attributions), the approval response comes back through this endpoint.
    """
    try:
        approval_status = payload.get("approved", False)
        execution_id = payload.get("execution_id")
        data = payload.get("data", {})

        logger.info(
            f"Received approval webhook from n8n: {'Approved' if approval_status else 'Rejected'} | "
            f"Execution: {execution_id}"
        )

        # Here you would implement logic to handle the approval
        # For example, continue with attribution sync if approved

        return {
            "status": "received",
            "approved": approval_status,
            "execution_id": execution_id,
            "message": f"Approval {'accepted' if approval_status else 'rejected'}"
        }
    except Exception as e:
        logger.error(f"Error processing approval webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/n8n/workflows", tags=["n8n Integration"])
async def list_n8n_workflows():
    """
    List all available n8n workflows

    Returns a list of workflows configured in the n8n instance,
    useful for discovering available automation options.
    """
    if not n8n_manager:
        raise HTTPException(status_code=503, detail="n8n integration not configured")

    try:
        workflows = n8n_manager.list_workflows()
        return {"workflows": workflows, "count": len(workflows)}
    except Exception as e:
        logger.error(f"Error listing n8n workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    logger.info("Starting HubSpot Attribution Engine API server...")
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
