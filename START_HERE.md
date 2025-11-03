# 🚀 START HERE - n8n Cloud Integration

**Welcome to your Hybrid LangChain + n8n System!**

## Your Setup

- **n8n Cloud:** https://your-instance.app.n8n.cloud ✅
- **LangChain API:** Local (will expose via ngrok)
- **Architecture:** Hybrid (n8n orchestrates, LangChain provides intelligence)

## What You Get

### 3 Ready-to-Use Workflows

1. **Attribution Pipeline** - Calculate attribution with approval for high-value deals
2. **Campaign Reporting** - Automated weekly campaign performance reports
3. **Data Quality Audit** - Daily data quality monitoring with alerts

### 8 API Endpoints

Your LangChain API provides these endpoints for n8n:
- `/n8n/agent/query` - AI decision support
- `/n8n/attribution` - Attribution calculation
- `/n8n/ad-sync` - Sync to ad platforms
- `/n8n/audit` - Data quality checks
- `/webhooks/n8n` - Receive n8n webhooks
- And more...

## Step-by-Step Setup

### 🏃 Quick Path (5 minutes)

Follow **[QUICK_START_CLOUD.md](QUICK_START_CLOUD.md)** for the fastest setup.

**TL;DR:**
```bash
# 1. Install ngrok
choco install ngrok
ngrok config add-authtoken YOUR_TOKEN

# 2. Start everything
python api_server.py  # Terminal 1
ngrok http 8000       # Terminal 2

# 3. Configure n8n Cloud
# Add LANGCHAIN_API_URL environment variable with your ngrok URL

# 4. Import workflows from n8n_workflows/

# 5. Done!
```

### 📖 Detailed Path

Follow **[N8N_CLOUD_SETUP.md](N8N_CLOUD_SETUP.md)** for complete instructions including:
- Multiple tunneling options (ngrok, Cloudflare, cloud deployment)
- Security considerations
- Production deployment
- Troubleshooting

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│  n8n Cloud                                   │
│  https://your-instance.app.n8n.cloud    │
│                                             │
│  Workflows:                                 │
│  • Attribution Pipeline                     │
│  • Campaign Reporting                       │
│  • Data Quality Audit                       │
└────────────────┬────────────────────────────┘
                 │
                 │ HTTPS Requests
                 │
                 ▼
┌─────────────────────────────────────────────┐
│  ngrok Tunnel                               │
│  https://abc123.ngrok-free.app              │
└────────────────┬────────────────────────────┘
                 │
                 │ Local
                 │
                 ▼
┌─────────────────────────────────────────────┐
│  Your Machine                               │
│  LangChain API: http://localhost:8000       │
│                                             │
│  Intelligence:                              │
│  • Attribution calculation                  │
│  • AI decision support                      │
│  • Ad platform sync                         │
│  • Data quality audit                       │
└─────────────────────────────────────────────┘
```

## Why This Architecture?

### n8n Cloud (Orchestration)
✅ Visual workflows anyone can understand
✅ Multi-system coordination (HubSpot → Ad Platforms → Slack)
✅ Human approvals (wait for review before syncing)
✅ Scheduled jobs (daily audits, weekly reports)
✅ No coding required for operations teams

### LangChain (Intelligence)
✅ Complex attribution models (W-shaped, full-path)
✅ AI-powered decision support
✅ RAG knowledge base
✅ Sophisticated business logic
✅ Maintains in code (easier for developers)

## Example Workflow

**Attribution Pipeline:**

1. Deal closes in HubSpot → Webhook to n8n
2. n8n calls LangChain: "Calculate attribution"
3. LangChain returns: $15,000 with 8 touchpoints
4. n8n checks: $15,000 > $10,000 threshold
5. n8n sends Slack: "High-value deal needs approval"
6. Manager clicks "Approve" in Slack
7. n8n updates HubSpot with attribution data
8. n8n calls LangChain: "Sync to ad platforms"
9. LangChain syncs to Google Ads + Facebook + LinkedIn
10. n8n sends Slack: "Attribution complete!"

**All visible, all modifiable in n8n's visual editor!**

## Documentation Quick Links

### Getting Started
- **[QUICK_START_CLOUD.md](QUICK_START_CLOUD.md)** - Start here! 5-minute setup
- **[N8N_CLOUD_SETUP.md](N8N_CLOUD_SETUP.md)** - Detailed cloud setup

### Reference
- **[N8N_INTEGRATION.md](N8N_INTEGRATION.md)** - Complete integration guide
- **[n8n_workflows/README.md](n8n_workflows/README.md)** - Workflow documentation
- **[HYBRID_ONLY_SYSTEM.md](HYBRID_ONLY_SYSTEM.md)** - System overview

### Implementation
- **[HYBRID_SYSTEM_CHANGES.md](HYBRID_SYSTEM_CHANGES.md)** - What was built
- **[README.md](README.md)** - Main documentation

## Common Questions

### Q: Do I need to keep my computer on?

**Short term:** Yes, for testing with ngrok
**Long term:** No, deploy the API to cloud (Railway, Render, etc.)

See deployment options in [N8N_CLOUD_SETUP.md](N8N_CLOUD_SETUP.md)

### Q: Will my ngrok URL change?

**Free ngrok:** Yes, URL changes when you restart
**Solutions:**
- Upgrade to ngrok Pro ($8/month) for persistent URLs
- Use Cloudflare Tunnel (free, persistent)
- Deploy API to cloud

### Q: Can I modify the workflows?

**Yes!** That's the point of the hybrid architecture. In n8n Cloud:
- Drag and drop nodes
- Change thresholds, schedules, recipients
- Add new integrations
- No coding required

### Q: What if I need custom logic?

**Use both layers:**
- **Complex logic:** Add to LangChain (Python code)
- **Orchestration:** Add to n8n (visual workflow)
- They communicate via HTTP requests

### Q: Is this secure?

**Current setup:** Good for development/testing
**Production:** Add these security measures:
- API authentication (API keys)
- HTTPS only
- Firewall rules
- Deploy to secure cloud

See security section in [N8N_CLOUD_SETUP.md](N8N_CLOUD_SETUP.md)

## Next Steps

### Immediate (Next 10 minutes)
1. ✅ Follow [QUICK_START_CLOUD.md](QUICK_START_CLOUD.md)
2. ✅ Get ngrok running
3. ✅ Configure n8n Cloud
4. ✅ Import workflows
5. ✅ Test the integration

### This Week
1. 📊 Customize workflow thresholds
2. 📧 Configure email/Slack credentials
3. 🧪 Test with real HubSpot data
4. 👥 Show operations team the visual workflows

### This Month
1. 🚀 Deploy API to cloud for 24/7 availability
2. 🔒 Add authentication and security
3. 📈 Set up monitoring and alerts
4. 🎨 Create custom workflows for your needs

## Support

### Need Help?
1. Check documentation above
2. Review troubleshooting in [N8N_CLOUD_SETUP.md](N8N_CLOUD_SETUP.md)
3. Check logs:
   - API logs: Your terminal running `python api_server.py`
   - n8n logs: Executions tab in n8n Cloud
   - ngrok logs: Your terminal running `ngrok`

### Want to Extend?
- Add new workflows in n8n Cloud (visual editor)
- Add new endpoints in `api_server.py` (Python)
- Add new intelligence in modules (Python)

## What You'll Build

With this system, you can:

✅ **Automate attribution** - No manual calculation
✅ **Sync ad platforms** - Automatic conversion tracking
✅ **Generate reports** - Weekly performance emails
✅ **Monitor quality** - Daily data health checks
✅ **Get approvals** - High-value deal reviews
✅ **Notify teams** - Slack updates on everything
✅ **Scale operations** - Visual workflows anyone can modify

## Ready?

👉 **Start with [QUICK_START_CLOUD.md](QUICK_START_CLOUD.md)**

Your n8n Cloud is waiting: https://your-instance.app.n8n.cloud

---

**System Status:** ✅ Ready to configure
**Setup Time:** ~5 minutes
**Your Next Step:** [QUICK_START_CLOUD.md](QUICK_START_CLOUD.md)
