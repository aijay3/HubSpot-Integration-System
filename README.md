# HubSpot Integration System

**Status: ✅ PRODUCTION READY + 🎯 HYBRID n8n INTEGRATION**

A comprehensive **Hybrid LangChain + n8n** system for HubSpot CRM attribution, ad-platform signaling, and marketing governance with enterprise-grade error handling, validation, and monitoring.

## 🚀 Hybrid Architecture + n8n Cloud

This system uses a **hybrid architecture** combining:
- **LangChain** for intelligent attribution reasoning and AI-powered decisions
- **n8n Cloud** (https://your-instance.app.n8n.cloud) for visual workflow orchestration

**Why hybrid?** Each tool excels at different things:
- **n8n** is perfect for orchestrating work across systems—visual workflows that your teams can see and modify
- **LangChain** is perfect for the intelligent parts—the attribution reasoning that requires AI

### 🎯 Quick Start (5 minutes)
See **[QUICK_START_CLOUD.md](QUICK_START_CLOUD.md)** for fastest setup with your n8n Cloud instance!

### 📚 Complete Documentation
- **[QUICK_START_CLOUD.md](QUICK_START_CLOUD.md)** - 5-minute setup guide
- **[N8N_CLOUD_SETUP.md](N8N_CLOUD_SETUP.md)** - Detailed cloud setup & tunneling
- **[N8N_INTEGRATION.md](N8N_INTEGRATION.md)** - Complete integration documentation

## Overview

This system implements a complete HubSpot integration with the following capabilities:

### 🎯 CRM Attribution & Data Model
- Multi-touch attribution models (First Touch, Last Touch, Linear, W-Shaped, Full Path)
- HubSpot tracking code installation with UTM and click ID capture
- Multi-session tracking across the customer journey
- Lifecycle stage management and automation
- Partner/affiliate tracking and attribution

### 📡 Ad-Platform Signaling
- Real-time conversion event syncing to Google Ads, Facebook Ads, and LinkedIn Ads
- Enhanced conversion tracking with hashed user data
- Click ID capture and linking (GCLID, FBCLID, etc.)
- Cross-platform campaign performance analysis
- Automated conversion event mapping

### 📊 Governance & Enablement
- Standardized UTM parameter naming conventions
- Compliant tracking URL builder
- Team training documentation and guides
- Data quality auditing and reporting
- System scalability planning

### 🤖 RAG (Retrieval-Augmented Generation)
- Supabase vector store integration
- OpenAI embeddings for semantic search
- Document ingestion and knowledge base management
- Context-aware responses using organization documentation
- Scalable vector similarity search

### 🔄 n8n Hybrid Integration (NEW!)
- Visual workflow orchestration for operations teams
- Bidirectional communication with LangChain intelligence
- Pre-built workflows: Attribution pipeline, Campaign reporting, Data quality audits
- Human-in-the-loop approval workflows for high-value attributions
- Multi-system coordination (HubSpot → LangChain → Ad Platforms → Slack)
- Scheduled jobs with monitoring and alerting
- Team-friendly workflow builder—no coding required for ops teams

### 🛡️ Production Features
- **Error Handling**: Comprehensive custom exceptions with retry logic
- **Input Validation**: Strict Pydantic validators for all data models
- **Health Monitoring**: Real-time system health checks for all components
- **Logging**: Correlation ID support for request tracing
- **Configuration Validation**: Automatic validation of API keys and settings
- **Test Coverage**: 37 passing tests across all modules

## Architecture

### Hybrid System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    n8n Workflows                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐        │
│  │Attribution │  │  Campaign  │  │Data Quality│        │
│  │  Pipeline  │  │  Reporting │  │   Audit    │        │
│  └──────┬─────┘  └──────┬─────┘  └──────┬─────┘        │
│         │                │                │              │
│         │    Orchestration Layer          │              │
└─────────┼────────────────┼────────────────┼──────────────┘
          │                │                │
          │   HTTP/Webhooks                 │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI REST API Server                     │
│  • Attribution endpoints    • n8n integration endpoints │
│  • Health checks           • Webhook receivers          │
│  • Campaign metrics        • RAG queries                │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│            LangChain Intelligence Layer                  │
│  • Attribution Agent    • Multi-touch models            │
│  • RAG Knowledge Base   • UTM validation                │
│  • Ad platform sync     • Decision making               │
└─────────────────────────────────────────────────────────┘
```

### File Structure

```
hubspot_integration/
├── api_server.py                    # FastAPI REST API server with n8n endpoints
├── config.py                        # Configuration with validation
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variables template
├── models/
│   ├── __init__.py
│   └── attribution.py              # Data models with validation
├── modules/
│   ├── __init__.py
│   ├── crm_attribution.py          # CRM & Attribution module
│   ├── ad_platform_signaling.py    # Ad platform integration with retry
│   ├── rag_system.py               # RAG knowledge base system
│   ├── n8n_integration.py          # n8n workflow integration
│   ├── health_check.py             # System health monitoring
│   ├── logging_utils.py            # Enhanced logging utilities
│   └── exceptions.py               # Custom exception classes
├── database/
│   ├── __init__.py
│   └── models.py                   # SQLAlchemy database models
├── n8n_workflows/                   # n8n workflow templates
│   ├── README.md                   # n8n workflow documentation
│   ├── attribution_pipeline.json   # Attribution with approval workflow
│   ├── campaign_reporting.json     # Weekly campaign reports
│   └── data_quality_audit.json     # Daily data quality checks
└── Documentation files:
    ├── README.md                    # This file - complete system documentation
    ├── START_HERE.md               # Quick start guide
    ├── QUICK_START_CLOUD.md        # 5-minute n8n Cloud setup
    ├── N8N_CLOUD_SETUP.md          # Detailed cloud setup with tunneling
    └── N8N_INTEGRATION.md          # Complete n8n integration guide
```

## Quick Start: n8n Cloud Hybrid System

**Your n8n Cloud:** https://your-instance.app.n8n.cloud

Get started in 5 minutes:

1. **Install ngrok** (for tunneling to cloud):
   ```bash
   choco install ngrok  # Windows
   ngrok config add-authtoken YOUR_TOKEN  # Get token from ngrok.com
   ```

2. **Start API + Tunnel:**
   ```bash
   # Terminal 1
   python api_server.py

   # Terminal 2
   ngrok http 8000
   ```

3. **Configure n8n Cloud:**
   - Go to https://your-instance.app.n8n.cloud
   - Settings → Environments → Add Variable
   - Name: `LANGCHAIN_API_URL`
   - Value: Your ngrok HTTPS URL (e.g., `https://abc123.ngrok-free.app`)

4. **Import workflows:**
   - Import from `n8n_workflows/` directory
   - Configure credentials (HubSpot, Slack, Email)
   - Activate workflows

**Complete 5-minute guide:** [QUICK_START_CLOUD.md](QUICK_START_CLOUD.md)
**Detailed setup:** [N8N_CLOUD_SETUP.md](N8N_CLOUD_SETUP.md)

## Installation

### Prerequisites

- Python 3.11 or 3.12 (recommended for best compatibility)
- HubSpot account with API access
- OpenAI API key (for LangChain agent and embeddings)
- **n8n Cloud account** (https://your-instance.app.n8n.cloud - configured)
- **ngrok account** (for tunneling to n8n Cloud - get free account at ngrok.com)
- Supabase account (optional, for RAG features)
- Google Ads, Facebook Ads, and/or LinkedIn Ads accounts (optional)
- PostgreSQL database (optional, for local attribution storage)

### Setup Steps

1. **Clone or download the repository:**
   ```bash
   cd hubspot_integration
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   # Copy the example env file
   cp .env.example .env

   # Edit .env and add your API keys and credentials
   ```

5. **Set up HubSpot:**
   - Generate HubSpot Private App access token
   - Add token to `.env` file
   - Note your HubSpot Portal ID

6. **Set up Supabase (Optional - for RAG features):**
   - Create a Supabase project at https://supabase.com
   - Enable pgvector extension in SQL Editor
   - Add Supabase URL and keys to `.env` file
   - Note: RAG features are optional and used for knowledge base queries

7. **Start the API server:**
   ```bash
   python api_server.py
   ```

   The server will start at: http://localhost:8000
   - View API docs at: http://localhost:8000/docs
   - Check health at: http://localhost:8000/health

8. **Set up n8n and workflows:**
   - See **[QUICK_START_CLOUD.md](QUICK_START_CLOUD.md)** for fastest 5-minute setup
   - See **[N8N_CLOUD_SETUP.md](N8N_CLOUD_SETUP.md)** for detailed setup instructions
   - See **[N8N_INTEGRATION.md](N8N_INTEGRATION.md)** for complete integration guide

## Configuration

### Environment Variables

Edit `.env` file with your credentials:

```env
# Required - HubSpot Configuration
HUBSPOT_API_KEY=your_hubspot_private_app_token_here
HUBSPOT_PORTAL_ID=your_hubspot_portal_id_here

# Required - OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Optional - Google Ads Integration
GOOGLE_ADS_CLIENT_ID=
GOOGLE_ADS_CLIENT_SECRET=
GOOGLE_ADS_DEVELOPER_TOKEN=
GOOGLE_ADS_REFRESH_TOKEN=
GOOGLE_ADS_CUSTOMER_ID=

# Optional - Facebook Ads Integration
FACEBOOK_ACCESS_TOKEN=
FACEBOOK_AD_ACCOUNT_ID=
FACEBOOK_APP_ID=
FACEBOOK_APP_SECRET=

# Optional - LinkedIn Ads Integration
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_AD_ACCOUNT_ID=

# Optional - Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/company_attribution

# Optional - Supabase Configuration (for RAG features)
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# Optional - Attribution Configuration
ATTRIBUTION_MODEL=w_shaped  # Options: first_touch, last_touch, linear, w_shaped, full_path
ATTRIBUTION_LOOKBACK_DAYS=90

# Optional - Logging Configuration
LOG_LEVEL=INFO
LOG_FILE_PATH=./logs/company_hubspot.log
```

### Attribution Models

Choose your attribution model in `.env`:

- **first_touch**: 100% credit to first touchpoint
- **last_touch**: 100% credit to last touchpoint
- **linear**: Equal credit to all touchpoints
- **w_shaped**: 30% first, 30% middle milestone, 30% last, 10% distributed
- **full_path**: 22.5% to each key milestone, 10% distributed

## Usage

### API Server

Start the FastAPI server:

```bash
python api_server.py
```

The API server provides endpoints for n8n workflows and direct programmatic access:
- **Health Check:** GET `/health`
- **Attribution:** POST `/n8n/attribution`
- **Ad Sync:** POST `/n8n/ad-sync`
- **AI Query:** POST `/n8n/agent/query`
- **Data Audit:** POST `/n8n/audit`
- **API Docs:** http://localhost:8000/docs

### Programmatic Usage

```python
from modules.crm_attribution import CRMAttributionManager
from modules.ad_platform_signaling import AdPlatformSignalingManager
from config import settings

# Initialize managers
crm_manager = CRMAttributionManager(settings)
ad_manager = AdPlatformSignalingManager(settings)

# Calculate attribution
attribution = crm_manager.calculate_attribution(
    contact_id="123456",
    total_value=5000.00,
    model_type="w_shaped"
)

# Sync conversion event
from models.attribution import LifecycleStage

conversion = ad_manager.sync_lifecycle_conversion(
    contact_id="123456",
    from_stage=LifecycleStage.LEAD,
    to_stage=LifecycleStage.CUSTOMER,
    conversion_value=5000.00
)
```

### Using with n8n Workflows

The primary usage pattern is through n8n workflows that call the API:

1. **Attribution Pipeline:** Automatically calculates attribution when deals close in HubSpot
2. **Campaign Reporting:** Generates weekly performance reports via scheduled workflow
3. **Data Quality Audit:** Runs daily data quality checks with automated alerts

See **[N8N_INTEGRATION.md](N8N_INTEGRATION.md)** for complete workflow documentation.

### Web Tracking Implementation

1. **Generate tracking code:**
   ```python
   from modules.crm_attribution import CRMAttributionManager
   from config import settings

   crm_manager = CRMAttributionManager(settings)
   tracking_code = crm_manager.install_tracking_code()
   ```

2. **Install on website:**
   Add the generated tracking code to all web pages, preferably in the `<head>` section.

3. **Verify installation:**
   - Visit your website with UTM parameters
   - Check HubSpot contact record for captured data
   - Verify custom properties are populated

## Key Features

### 1. Multi-Touch Attribution

Track and attribute revenue across multiple customer touchpoints:

```python
from modules.crm_attribution import CRMAttributionManager
from models.attribution import Touchpoint, UTMParameters, ClickID
from datetime import datetime
from config import settings

crm_manager = CRMAttributionManager(settings)

# Capture touchpoint
touchpoint = Touchpoint(
    contact_id="123456",
    timestamp=datetime.now(),
    touchpoint_type="paid_search",
    utm_parameters=UTMParameters(
        utm_source="google",
        utm_medium="cpc",
        utm_campaign="2025_q1_brand"
    ),
    click_ids=ClickID(gclid="abc123xyz")
)

crm_manager.capture_touchpoint("123456", touchpoint)
```

### 2. Real-Time Ad Platform Syncing

Automatically sync conversion events to ad platforms:

```python
from modules.ad_platform_signaling import AdPlatformSignalingManager
from models.attribution import LifecycleStage
from config import settings

ad_manager = AdPlatformSignalingManager(settings)

# Lifecycle changes automatically trigger ad platform syncing
conversion = ad_manager.sync_lifecycle_conversion(
    contact_id="123456",
    from_stage=LifecycleStage.MARKETING_QUALIFIED_LEAD,
    to_stage=LifecycleStage.CUSTOMER,
    conversion_value=5000.00
)

print(f"Synced to: {conversion.synced_to_ad_platforms}")
# Output: ['google_ads', 'facebook_ads', 'linkedin_ads']
```

### 3. AI-Powered Decision Support

Query the LangChain intelligence layer via API:

```bash
curl -X POST http://localhost:8000/n8n/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Which attribution model should I use for a SaaS customer with 8 touchpoints?",
    "context": {"industry": "SaaS", "touchpoint_count": 8}
  }'
```

### 4. n8n Workflow Orchestration

Visual workflows handle multi-system coordination:

- **Attribution Pipeline:** Automatic calculation on deal close with approval for high-value deals
- **Campaign Reporting:** Weekly performance reports sent to stakeholders
- **Data Quality Audit:** Daily monitoring with alerts for data issues

See **[n8n_workflows/README.md](n8n_workflows/README.md)** for complete workflow documentation.

## HubSpot Workflows

The system works with HubSpot workflows for lifecycle stage automation:

1. **Lead Enrichment**: Automatically enrich contact data from UTM parameters
2. **MQL Conversion**: Update lifecycle stage and trigger ad platform sync
3. **SQL Conversion**: Sales qualification triggers
4. **Opportunity Creation**: Deal creation and attribution update
5. **Customer Conversion**: Final attribution calculation and revenue sync

These workflows are configured in HubSpot and can trigger n8n workflows via webhooks for advanced orchestration. See **[N8N_INTEGRATION.md](N8N_INTEGRATION.md)** for webhook configuration.

## Ad Platform Setup

### Google Ads

1. Enable enhanced conversions in Google Ads
2. Set up conversion actions for each lifecycle stage
3. Configure API access and add credentials to `.env`
4. Map conversion actions in `ad_platform_signaling.py`

### Facebook Ads

1. Set up Facebook Pixel on website
2. Configure Conversions API
3. Create custom conversion events
4. Add credentials to `.env`

### LinkedIn Ads

1. Install LinkedIn Insight Tag
2. Set up conversion tracking in Campaign Manager
3. Configure API access
4. Add credentials to `.env`

## Data Model

### Contact Properties (Custom)

- `first_touch_utm_source`: First touchpoint source
- `first_touch_utm_campaign`: First touchpoint campaign
- `last_touch_utm_source`: Most recent touchpoint source
- `last_touch_utm_campaign`: Most recent touchpoint campaign
- `all_touchpoints_json`: Complete touchpoint history
- `gclid`: Google Click ID
- `fbclid`: Facebook Click ID
- `partner_id`: Partner/Affiliate ID
- `attributed_revenue`: Total attributed revenue

### Lifecycle Stages

- Subscriber
- Lead
- Marketing Qualified Lead (MQL)
- Sales Qualified Lead (SQL)
- Opportunity
- Customer
- Evangelist

## Documentation

The system includes comprehensive documentation:

### Getting Started
- **[START_HERE.md](START_HERE.md)**: Start here! Quick orientation to the hybrid system
- **[QUICK_START_CLOUD.md](QUICK_START_CLOUD.md)**: 5-minute setup guide for n8n Cloud
- **[N8N_CLOUD_SETUP.md](N8N_CLOUD_SETUP.md)**: Detailed cloud setup with tunneling options

### Reference Documentation
- **[README.md](README.md)**: This file - complete system documentation
- **[N8N_INTEGRATION.md](N8N_INTEGRATION.md)**: Complete n8n integration guide
- **[n8n_workflows/README.md](n8n_workflows/README.md)**: Workflow-specific documentation

## Monitoring & Logging

Logs are stored in `logs/company_hubspot.log` with rotation and retention policies.

Log levels:
- DEBUG: Detailed debugging information
- INFO: General information
- WARNING: Warning messages
- ERROR: Error messages

Configure log level in `.env`:
```env
LOG_LEVEL=INFO
```

## Scalability

The system is designed for scalability with:

- **Multi-domain tracking:** Support for tracking across multiple domains
- **Extensible ad platform integration:** Easy addition of new ad platforms
- **n8n orchestration:** Distribute workloads across multiple workflows
- **API rate limiting:** Built-in rate limiting for API endpoints
- **Horizontal scaling:** Deploy multiple API instances behind a load balancer
- **Cloud deployment:** Deploy n8n Cloud + API to cloud providers

For production deployment at scale, consider:
- Using PostgreSQL for attribution data storage
- Implementing Redis for caching
- Setting up monitoring with Datadog or New Relic
- Using message queues (RabbitMQ/Redis) for async processing

## Best Practices

1. **UTM Parameters**: Always use standardized, lowercase UTM parameters
2. **Testing**: Test all tracking URLs before launching campaigns
3. **Documentation**: Keep team documentation up to date
4. **Auditing**: Run data quality audits monthly
5. **Training**: Conduct quarterly team training sessions
6. **Monitoring**: Monitor logs for errors and warnings
7. **Compliance**: Ensure GDPR compliance for data collection

## Troubleshooting

### Common Issues

**Issue**: Custom properties not appearing in HubSpot
- **Solution**: Run `create_custom_contact_properties()` again
- **Check**: Verify API permissions

**Issue**: Conversion events not syncing to ad platforms
- **Solution**: Verify API credentials in `.env`
- **Check**: Ensure click IDs are being captured

**Issue**: Attribution calculations are incorrect
- **Solution**: Verify touchpoint data is complete
- **Check**: Run data quality audit

## API Server

The project includes a FastAPI REST API server for programmatic access and n8n integration:

### Starting the API Server

```bash
# Direct execution (recommended)
python api_server.py

# Using uvicorn directly (for development)
uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
```

The server will start at http://localhost:8000

### API Endpoints

- **GET /**: Root endpoint with service information
- **GET /health**: Comprehensive health check
- **GET /health/components/{component_name}**: Check specific component health
- **GET /attribution/contact/{contact_id}**: Get attribution for a contact
- **GET /attribution/summary**: Get attribution summary
- **GET /campaigns**: List all campaigns with metrics
- **GET /campaigns/{utm_campaign}**: Get specific campaign metrics
- **POST /rag/query**: Query the RAG knowledge base
- **GET /rag/stats**: Get RAG knowledge base statistics
- **GET /etl/jobs**: List ETL job executions
- **POST /etl/sync/contacts**: Trigger manual contact sync

### API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Development

For local development, you can use virtual environments:

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

For production deployment, consider:
- Containerizing the API with Docker
- Using environment-specific .env files
- Setting up proper logging and monitoring
- Implementing health checks and auto-restart
- Using a process manager like systemd or PM2

## Support

For issues or questions:
1. Check the documentation files (README.md, QUICKSTART.md, INSTALLATION.md)
2. Review logs in `logs/` folder
3. Check API documentation at `/docs` when server is running
4. Contact Marketing Operations team
