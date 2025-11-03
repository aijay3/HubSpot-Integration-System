# Hybrid LangChain + n8n Attribution System

## Overview

This system implements a **hybrid architecture** that combines the strengths of two powerful tools:

- **LangChain:** Handles intelligent attribution reasoning, multi-touch attribution models, RAG knowledge base, and AI-powered decision making
- **n8n:** Provides visual workflow orchestration, multi-system coordination, human-in-the-loop approvals, and team-friendly automation

### Why Hybrid?

Each tool excels at different things:

| Capability | Best Tool | Reason |
|------------|-----------|---------|
| Attribution Logic | **LangChain** | Complex AI reasoning, multiple attribution models, dynamic decision-making |
| System Orchestration | **n8n** | Visual workflows, conditional routing, multi-system coordination |
| Human Approvals | **n8n** | Wait nodes, approval workflows, human-in-the-loop |
| Knowledge Queries | **LangChain** | RAG system, semantic search, natural language understanding |
| Scheduled Jobs | **n8n** | Cron scheduling, monitoring, error handling with retries |
| Data Transformation | **n8n** | Visual mapping, format conversion, business rule routing |
| Intelligent Analysis | **LangChain** | AI agent reasoning, anomaly detection, recommendation engine |
| Team Visibility | **n8n** | Visual workflow builder, execution logs, team collaboration |

**If you built everything in n8n:** Attribution logic would be brittle and hard to maintain. Complex AI reasoning doesn't fit well in visual workflows.

**If you built everything in LangChain:** Operations teams couldn't modify workflows without coding. No visual representation of system flows.

**Hybrid approach:** LangChain handles the "thinking," n8n handles the "doing." Best of both worlds.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          n8n Workflows                               │
│  ┌────────────────┐  ┌──────────────┐  ┌───────────────────┐       │
│  │  HubSpot       │  │  Scheduled   │  │  Approval         │       │
│  │  Contact       │  │  Attribution │  │  Workflows        │       │
│  │  Trigger       │  │  Sync        │  │  (High Value)     │       │
│  └────────┬───────┘  └──────┬───────┘  └────────┬──────────┘       │
│           │                  │                    │                  │
│           │  Orchestration   │                    │                  │
└───────────┼──────────────────┼────────────────────┼──────────────────┘
            │                  │                    │
            │   HTTP Request   │                    │
            ▼                  ▼                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│              FastAPI Server (Extended for n8n)                       │
│                                                                      │
│  LangChain Intelligence Endpoints:                                  │
│  • POST /n8n/agent/query       - Invoke LangChain agent            │
│  • POST /n8n/attribution       - Calculate attribution             │
│  • POST /n8n/ad-sync          - Sync to ad platforms               │
│  • POST /n8n/audit            - Data quality audit                 │
│                                                                      │
│  n8n Control Endpoints:                                             │
│  • POST /n8n/workflows/trigger - Trigger n8n workflows             │
│  • GET  /n8n/workflows         - List n8n workflows                │
│                                                                      │
│  Webhook Receivers:                                                 │
│  • POST /webhooks/n8n          - Generic n8n webhooks              │
│  • POST /webhooks/n8n/approval - Approval responses                │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  LangChain Intelligence Layer                        │
│                                                                      │
│  • Attribution Agent (GPT-4)    • Multi-touch attribution models    │
│  • RAG Knowledge Base           • Anomaly detection                 │
│  • UTM validation               • Natural language processing       │
│  • Decision making              • Intelligent routing               │
└─────────────────────────────────────────────────────────────────────┘
```

## Installation & Setup

### Step 1: Install n8n

Choose one of the following methods:

#### Option A: Docker (Recommended)

```bash
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
```

#### Option B: npm

```bash
npm install -g n8n
n8n start
```

#### Option C: Docker Compose (with persistence)

Create `docker-compose-n8n.yml`:

```yaml
version: '3.8'

services:
  n8n:
    image: n8nio/n8n
    restart: always
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=your_password_here
      - N8N_HOST=localhost
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
      - WEBHOOK_URL=http://localhost:5678/
    volumes:
      - n8n_data:/home/node/.n8n

volumes:
  n8n_data:
```

Run:
```bash
docker-compose -f docker-compose-n8n.yml up -d
```

Access n8n at: http://localhost:5678

### Step 2: Configure Environment Variables

Update your `.env` file:

```bash
# n8n Integration
N8N_BASE_URL=http://localhost:5678
N8N_API_KEY=your_n8n_api_key_here  # Optional, for API access
N8N_WEBHOOK_BASE_URL=http://localhost:8000  # Where this API receives webhooks
```

### Step 3: Configure n8n Environment Variables

In n8n, go to Settings → Environments and add:

```bash
LANGCHAIN_API_URL=http://localhost:8000
HUBSPOT_PORTAL_ID=your_portal_id
```

If your LangChain API is running in Docker, use Docker networking:
```bash
LANGCHAIN_API_URL=http://host.docker.internal:8000  # macOS/Windows
# OR
LANGCHAIN_API_URL=http://172.17.0.1:8000  # Linux
```

### Step 4: Set Up Credentials in n8n

Configure these credentials in n8n (Settings → Credentials):

1. **HubSpot:**
   - Type: HubSpot
   - Auth Type: API Key
   - API Key: Your HubSpot private app token

2. **Slack:**
   - Type: Slack
   - Auth Type: OAuth2
   - Follow the OAuth flow to connect your Slack workspace

3. **Email (SMTP):**
   - Type: SMTP
   - Host: smtp.gmail.com (or your SMTP server)
   - Port: 587
   - User: your email
   - Password: app password

4. **Google Sheets (Optional):**
   - Type: Google Sheets
   - Auth Type: OAuth2
   - Follow the OAuth flow

### Step 5: Import Workflows

1. Open n8n at http://localhost:5678
2. Click "Add workflow" (+)
3. Click the "..." menu → "Import from File"
4. Navigate to `n8n_workflows/` directory
5. Import each workflow:
   - `attribution_pipeline.json`
   - `campaign_reporting.json`
   - `data_quality_audit.json`

### Step 6: Configure Workflow Settings

For each imported workflow, update:

1. **Slack channel IDs:**
   - Find in Slack: Right-click channel → View channel details
   - Copy channel ID (e.g., `C0123456789`)
   - Update in Slack nodes

2. **Email recipients:**
   - Update in Email Send nodes

3. **Google Sheets (if using):**
   - Update document ID and sheet names

### Step 7: Test Integration

Start the LangChain API server:
```bash
python api_server.py
```

Test the connection from n8n:
1. Create a simple HTTP Request node
2. URL: `http://localhost:8000/health`
3. Method: GET
4. Execute the node
5. Should return: `{"status": "healthy", ...}`

### Step 8: Activate Workflows

In each workflow:
1. Review all node configurations
2. Click the toggle to "Active"
3. Monitor the executions tab for issues

## Usage Examples

### Example 1: Trigger Attribution from n8n

Create an HTTP Request node in n8n:

```json
{
  "method": "POST",
  "url": "http://localhost:8000/n8n/attribution",
  "body": {
    "contact_id": "12345",
    "total_value": 5000,
    "model_type": "w_shaped"
  }
}
```

Response:
```json
{
  "contact_id": "12345",
  "total_value": 5000,
  "model_type": "w_shaped",
  "touchpoint_count": 5,
  "status": "success"
}
```

### Example 2: Query LangChain Agent from n8n

Create an HTTP Request node:

```json
{
  "method": "POST",
  "url": "http://localhost:8000/n8n/agent/query",
  "body": {
    "query": "Should I use first-touch or w-shaped attribution for a SaaS customer with 8 touchpoints?",
    "context": {
      "industry": "SaaS",
      "touchpoint_count": 8,
      "customer_type": "enterprise"
    }
  }
}
```

Response:
```json
{
  "response": "For a SaaS customer with 8 touchpoints, I recommend using the W-shaped attribution model...",
  "correlation_id": "abc-123",
  "timestamp": "2025-01-10T12:00:00Z"
}
```

### Example 3: Trigger n8n Workflow from LangChain

In your Python code:

```python
from modules.n8n_integration import N8nIntegrationManager

n8n = N8nIntegrationManager(
    n8n_base_url="http://localhost:5678",
    webhook_base_url="http://localhost:8000"
)

result = n8n.trigger_attribution_workflow(
    contact_id="12345",
    total_value=5000,
    model_type="w_shaped",
    notify=True
)

print(f"Workflow triggered: {result.execution_id}")
```

### Example 4: Sync to Ad Platforms from n8n

Create an HTTP Request node:

```json
{
  "method": "POST",
  "url": "http://localhost:8000/n8n/ad-sync",
  "body": {
    "contact_id": "12345",
    "from_stage": "lead",
    "to_stage": "customer",
    "conversion_value": 5000
  }
}
```

Response:
```json
{
  "contact_id": "12345",
  "synced_platforms": ["google_ads", "facebook_ads", "linkedin_ads"],
  "status": "success"
}
```

## Common Workflows

### Workflow 1: Automated Attribution Pipeline

**Trigger:** HubSpot contact updated → Deal stage changed to "Closed Won"

**Flow:**
1. n8n detects HubSpot deal stage change
2. Calls LangChain to calculate attribution
3. If value > $10k, requires approval
4. Updates HubSpot contact properties
5. Syncs conversion to ad platforms
6. Notifies team via Slack

**Benefits:**
- Automated attribution on deal close
- Human review for high-value deals
- Multi-system synchronization
- Team visibility

### Workflow 2: Weekly Campaign Performance Report

**Trigger:** Schedule (Every Monday 9am)

**Flow:**
1. n8n triggers on schedule
2. Fetches campaign data from LangChain API
3. Formats HTML report with metrics
4. Emails report to stakeholders
5. Posts summary to Slack
6. Archives data to Google Sheets

**Benefits:**
- No manual reporting work
- Consistent delivery schedule
- Historical data tracking
- Stakeholder alignment

### Workflow 3: Data Quality Monitoring

**Trigger:** Schedule (Daily 8am)

**Flow:**
1. n8n triggers daily audit
2. LangChain analyzes data quality
3. If quality < 80%, alerts team
4. If critical (<60%), emails leadership
5. Logs all results to Google Sheets

**Benefits:**
- Proactive issue detection
- Escalation for critical issues
- Audit trail maintenance
- Data integrity assurance

## API Reference

### LangChain Intelligence Endpoints

#### POST /n8n/agent/query

Invoke the LangChain agent for intelligent decision-making.

**Request:**
```json
{
  "query": "Question or command for the agent",
  "context": {
    "optional": "context data"
  }
}
```

**Response:**
```json
{
  "response": "Agent's response",
  "correlation_id": "abc-123",
  "timestamp": "2025-01-10T12:00:00Z"
}
```

**Use Cases:**
- Attribution model recommendations
- UTM parameter validation
- Complex decision-making
- Natural language queries

#### POST /n8n/attribution

Calculate multi-touch attribution.

**Request:**
```json
{
  "contact_id": "12345",
  "total_value": 5000,
  "model_type": "w_shaped"
}
```

**Response:**
```json
{
  "contact_id": "12345",
  "total_value": 5000,
  "model_type": "w_shaped",
  "touchpoint_count": 5,
  "status": "success"
}
```

**Attribution Models:**
- `first_touch`: 100% to first touchpoint
- `last_touch`: 100% to last touchpoint
- `linear`: Equal distribution
- `w_shaped`: 30% first, 30% conversion, 30% opportunity, 10% distributed
- `full_path`: Full customer journey weighting

#### POST /n8n/ad-sync

Sync conversion events to ad platforms.

**Request:**
```json
{
  "contact_id": "12345",
  "from_stage": "lead",
  "to_stage": "customer",
  "conversion_value": 5000
}
```

**Response:**
```json
{
  "contact_id": "12345",
  "synced_platforms": ["google_ads", "facebook_ads", "linkedin_ads"],
  "status": "success"
}
```

**Lifecycle Stages:**
- `subscriber`
- `lead`
- `marketing_qualified_lead`
- `sales_qualified_lead`
- `opportunity`
- `customer`
- `evangelist`

#### POST /n8n/audit

Run data quality audit.

**Request:** (No body required)

**Response:**
```json
{
  "timestamp": "2025-01-10T12:00:00Z",
  "quality_score": 95,
  "checks_passed": 23,
  "checks_failed": 2,
  "issues": [
    {"type": "missing_utm", "count": 5},
    {"type": "invalid_format", "count": 3}
  ]
}
```

### n8n Control Endpoints

#### POST /n8n/workflows/trigger

Trigger an n8n workflow from LangChain.

**Request:**
```json
{
  "workflow_name": "attribution_pipeline",
  "payload": {
    "contact_id": "12345",
    "total_value": 5000
  },
  "wait_for_completion": false
}
```

**Response:**
```json
{
  "status": "triggered",
  "execution_id": "abc-123",
  "workflow_name": "attribution_pipeline",
  "data": {}
}
```

#### GET /n8n/workflows

List all available n8n workflows.

**Response:**
```json
{
  "workflows": [
    {
      "id": "1",
      "name": "Attribution Pipeline",
      "active": true
    }
  ],
  "count": 1
}
```

### Webhook Endpoints

#### POST /webhooks/n8n

Receive generic webhooks from n8n.

**Request:**
```json
{
  "workflow_id": "1",
  "execution_id": "abc-123",
  "event_type": "attribution_complete",
  "data": {}
}
```

#### POST /webhooks/n8n/approval

Receive approval responses from n8n.

**Request:**
```json
{
  "execution_id": "abc-123",
  "approved": true,
  "data": {
    "contact_id": "12345"
  }
}
```

## Best Practices

### 1. Separation of Concerns

**LangChain handles:**
- Complex calculations (attribution models)
- AI reasoning (agent queries)
- Data validation (UTM standards)
- Intelligent analysis (anomaly detection)

**n8n handles:**
- System coordination (HubSpot → Ad Platforms)
- Human workflows (approvals, notifications)
- Scheduled jobs (reports, audits)
- Conditional routing (high value vs standard)

### 2. Error Handling

**In n8n workflows:**
- Use error workflows for global error handling
- Add "On Error" branches to critical nodes
- Set timeouts on HTTP requests (30-60 seconds)
- Log errors to monitoring systems

**In LangChain API:**
- Returns structured error responses
- Includes correlation IDs for tracing
- Implements retry logic with exponential backoff
- Logs all errors with context

### 3. Testing Strategy

**Development:**
- Test LangChain API endpoints with curl/Postman
- Test n8n workflows with manual execution
- Use test data to avoid production impact

**Staging:**
- Deploy both systems to staging environment
- Run end-to-end tests with realistic data
- Verify integrations work across network boundaries

**Production:**
- Gradual rollout with monitoring
- Keep fallback to manual processes ready
- Monitor error rates and performance
- Have rollback plan ready

### 4. Monitoring & Observability

**Key metrics to track:**
- Workflow execution success rate
- API response times
- Attribution calculation accuracy
- Ad platform sync success rate
- Data quality scores over time

**Set up alerts for:**
- Workflow execution failures
- API endpoint errors (>5% error rate)
- Data quality below threshold
- Missing or delayed syncs

### 5. Security

**API Security:**
- Use API keys for n8n → LangChain communication
- Implement rate limiting
- Validate all input data
- Use HTTPS in production

**n8n Security:**
- Enable basic auth or SSO
- Restrict workflow editing to admins
- Use credential system (never hardcode secrets)
- Regular security updates

## Troubleshooting

### Issue: n8n can't reach LangChain API

**Symptoms:**
- HTTP Request nodes timing out
- Connection refused errors

**Solutions:**
1. Verify API server is running: `curl http://localhost:8000/health`
2. Check Docker networking if using Docker
3. Update `LANGCHAIN_API_URL` in n8n environment
4. Check firewall settings

### Issue: Workflows executing but no results

**Symptoms:**
- Workflows show "success" but nothing happens
- Data not updating in target systems

**Solutions:**
1. Check execution logs in n8n
2. Verify credentials are properly linked
3. Test each node individually
4. Check API endpoint responses

### Issue: High-value approvals not triggering

**Symptoms:**
- All attributions processed without approval
- Slack notifications not sent

**Solutions:**
1. Check IF node condition threshold
2. Verify Slack credentials
3. Check channel ID is correct
4. Test Slack node separately

### Issue: Scheduled workflows not running

**Symptoms:**
- Workflows marked as "Active" but not executing
- No execution history

**Solutions:**
1. Verify workflow is activated (toggle on)
2. Check cron expression is valid
3. Check n8n server time zone
4. Review n8n logs for errors

## Migration Guide

### From Pure LangChain to Hybrid

If you have existing LangChain workflows:

1. **Identify orchestration logic** that should move to n8n:
   - Multi-system coordination
   - Scheduled jobs
   - Approval workflows
   - Conditional routing

2. **Keep intelligence in LangChain:**
   - Attribution calculations
   - Agent reasoning
   - RAG queries
   - Complex analysis

3. **Create n8n workflows** that call LangChain APIs

4. **Test thoroughly** before switching production traffic

### From Pure n8n to Hybrid

If you have existing n8n workflows:

1. **Identify complex logic** that should move to LangChain:
   - Complex calculations
   - AI-powered decisions
   - Natural language processing
   - Dynamic attribution models

2. **Keep orchestration in n8n:**
   - System integrations
   - Notifications
   - Approvals
   - Scheduling

3. **Implement LangChain endpoints** for complex logic

4. **Update n8n workflows** to call new endpoints

## Advanced Topics

### Custom Workflow Handlers

Register custom handlers for specific events:

```python
from modules.n8n_integration import N8nIntegrationManager

n8n = N8nIntegrationManager(...)

def handle_high_value_attribution(payload):
    """Custom handler for high-value attributions"""
    contact_id = payload.data.get('contact_id')
    value = payload.data.get('total_value')

    # Custom logic here
    logger.info(f"High value attribution: {contact_id} = ${value}")

    # Maybe trigger additional workflows
    # Maybe send custom notifications

    return {"status": "processed"}

n8n.register_webhook_handler('high_value_attribution', handle_high_value_attribution)
```

### Bidirectional Communication

LangChain can trigger n8n workflows:

```python
# In your LangChain code
from modules.n8n_integration import N8nIntegrationManager

n8n = N8nIntegrationManager(...)

# Detect anomaly in attribution
if attribution_looks_suspicious:
    n8n.trigger_workflow(
        workflow_name="review_attribution",
        payload={
            "contact_id": contact_id,
            "reason": "Unusual touchpoint pattern",
            "attribution_data": attribution_result
        }
    )
```

### Dynamic Workflow Selection

Use LangChain agent to decide which workflow to run:

```python
# Ask agent which workflow to use
agent_response = integration.chat(
    f"Which workflow should I use for a {customer_type} customer "
    f"with ${deal_value} deal value?"
)

# Parse response and trigger appropriate workflow
workflow_name = extract_workflow_from_response(agent_response)
n8n.trigger_workflow(workflow_name, payload)
```

## Performance Optimization

### Caching

Implement caching for frequently accessed data:

```python
# In LangChain API
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_campaign_metrics(campaign_name: str):
    # Expensive calculation
    return calculate_metrics(campaign_name)
```

### Async Processing

Use background tasks for long-running operations:

```python
from fastapi import BackgroundTasks

@app.post("/n8n/attribution")
async def calculate_attribution(request: Request, background_tasks: BackgroundTasks):
    # Start calculation in background
    background_tasks.add_task(process_attribution, request)

    # Return immediately
    return {"status": "processing", "execution_id": execution_id}
```

### Batch Processing

Process multiple items in a single workflow:

```python
# In n8n, loop through items
items = [
  {"contact_id": "1", "value": 1000},
  {"contact_id": "2", "value": 2000},
  {"contact_id": "3", "value": 3000}
]

# HTTP Request node processes each item
# Use n8n's loop functionality
```

## Support & Resources

### Documentation
- LangChain API: See `README.md` in root directory
- n8n Workflows: See `n8n_workflows/README.md`
- API Reference: See `/docs` endpoint when server is running

### Community
- n8n Community: https://community.n8n.io
- LangChain Docs: https://python.langchain.com

### Getting Help
1. Check execution logs in n8n
2. Review API server logs
3. Test components individually
4. Contact Marketing Operations team

## Changelog

### Version 1.0.0 (2025-01-10)
- Initial hybrid integration
- Attribution pipeline workflow
- Campaign reporting workflow
- Data quality audit workflow
- Full bidirectional communication
- Comprehensive API endpoints
- Documentation and examples
