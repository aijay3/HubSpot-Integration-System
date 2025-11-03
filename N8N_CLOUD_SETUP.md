# n8n Cloud Setup Guide

Your n8n instance: **https://your-instance.app.n8n.cloud**

## Overview

Since you're running n8n on the cloud, your local LangChain API server needs to be accessible from the internet so n8n can call it. This guide shows you how to set that up.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  n8n Cloud (https://your-instance.app.n8n.cloud) │
│                                                       │
│  Workflows send HTTP requests to your API            │
└───────────────────────┬──────────────────────────────┘
                        │
                        │ HTTPS
                        │
                        ▼
┌──────────────────────────────────────────────────────┐
│  Public Tunnel (ngrok/Cloudflare Tunnel)             │
│  Example: https://abc123.ngrok.io                    │
└───────────────────────┬──────────────────────────────┘
                        │
                        │ Local
                        │
                        ▼
┌──────────────────────────────────────────────────────┐
│  Your Local Machine                                   │
│  LangChain API: http://localhost:8000                │
└──────────────────────────────────────────────────────┘
```

## Setup Options

### Option 1: ngrok (Recommended - Easiest)

**Pros:** Easy setup, free tier available, persistent URLs on paid plan
**Cons:** Free tier URL changes on restart, rate limits

#### Steps:

1. **Install ngrok:**
   ```bash
   # Download from https://ngrok.com/download
   # Or use chocolatey on Windows:
   choco install ngrok
   ```

2. **Sign up for free account:**
   - Go to https://dashboard.ngrok.com/signup
   - Copy your auth token

3. **Configure ngrok:**
   ```bash
   ngrok config add-authtoken YOUR_AUTH_TOKEN
   ```

4. **Start your API server:**
   ```bash
   python api_server.py
   ```

5. **Start ngrok tunnel:**
   ```bash
   ngrok http 8000
   ```

6. **Copy the HTTPS URL:**
   ```
   Forwarding  https://abc123.ngrok.io -> http://localhost:8000
                      ^^^^^^^^^^^^^^^^^^^^
                      Copy this URL
   ```

7. **Configure n8n:**
   - Go to https://your-instance.app.n8n.cloud
   - Settings → Environments → Variables
   - Add: `LANGCHAIN_API_URL` = `https://abc123.ngrok.io`

8. **Update your .env:**
   ```bash
   N8N_WEBHOOK_BASE_URL=https://abc123.ngrok.io
   ```

#### Keep it Running:

Free ngrok URLs change when you restart. For persistent URLs, upgrade to ngrok paid plan or use Option 2.

### Option 2: Cloudflare Tunnel (Free, Persistent)

**Pros:** Free, persistent URLs, no rate limits
**Cons:** Slightly more setup, requires Cloudflare account

#### Steps:

1. **Install cloudflared:**
   ```bash
   # Download from https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
   # Or use chocolatey:
   choco install cloudflared
   ```

2. **Login to Cloudflare:**
   ```bash
   cloudflared tunnel login
   ```

3. **Create a tunnel:**
   ```bash
   cloudflared tunnel create langchain-api
   ```

4. **Create config file** (`C:\Users\YourUser\.cloudflared\config.yml`):
   ```yaml
   tunnel: YOUR_TUNNEL_ID
   credentials-file: C:\Users\YourUser\.cloudflared\YOUR_TUNNEL_ID.json

   ingress:
     - hostname: langchain-api.yourdomain.com
       service: http://localhost:8000
     - service: http_status:404
   ```

5. **Route tunnel to domain:**
   ```bash
   cloudflared tunnel route dns langchain-api langchain-api.yourdomain.com
   ```

6. **Run the tunnel:**
   ```bash
   cloudflared tunnel run langchain-api
   ```

7. **Configure n8n:**
   - Settings → Environments → Variables
   - Add: `LANGCHAIN_API_URL` = `https://langchain-api.yourdomain.com`

### Option 3: Deploy API to Cloud (Production)

**Pros:** Production-ready, no tunnels needed, always available
**Cons:** Costs money, more complex setup

#### Popular Options:

1. **Railway.app** (Easiest for Python)
   - Connect GitHub repo
   - Auto-deploys on push
   - ~$5/month

2. **Render.com** (Good free tier)
   - Free tier available
   - Easy Python deployment
   - Auto-sleep after inactivity

3. **Heroku** (Classic choice)
   - Well-documented
   - Easy deployment
   - ~$7/month

4. **AWS/GCP/Azure** (Enterprise)
   - Full control
   - More complex
   - Variable pricing

I can provide detailed deployment guides for any of these if needed.

## Configuration

### 1. Environment Variables in n8n Cloud

Go to n8n Cloud Settings → Environments → Variables and add:

```bash
LANGCHAIN_API_URL=https://your-tunnel-url.ngrok.io
```

**Important:** Use your actual ngrok/Cloudflare tunnel URL, not localhost!

### 2. Update Your Local .env

```bash
# n8n Cloud Configuration
N8N_BASE_URL=https://your-instance.app.n8n.cloud
N8N_API_KEY=  # Get from n8n Cloud settings if API access needed
N8N_WEBHOOK_BASE_URL=https://your-tunnel-url.ngrok.io  # Your public URL
```

## Import Workflows to n8n Cloud

### 1. Access n8n Cloud
Go to https://your-instance.app.n8n.cloud

### 2. Import Each Workflow

**Attribution Pipeline:**
- Click "Add workflow" → "Import from File"
- Select `n8n_workflows/attribution_pipeline.json`
- Click "Import"

**Campaign Reporting:**
- Repeat for `campaign_reporting.json`

**Data Quality Audit:**
- Repeat for `data_quality_audit.json`

### 3. Update Workflow Settings

In each workflow, update the HTTP Request nodes:

**Before (local):**
```
URL: http://localhost:8000/n8n/attribution
```

**After (cloud):**
```
URL: {{$env.LANGCHAIN_API_URL}}/n8n/attribution
```

The `{{$env.LANGCHAIN_API_URL}}` will use the environment variable you set in n8n Cloud.

## Configure Credentials in n8n Cloud

### HubSpot Credential
1. Settings → Credentials → Add Credential
2. Select "HubSpot"
3. Choose "API Key" method
4. Enter your HubSpot private app token
5. Test & Save

### Slack Credential
1. Settings → Credentials → Add Credential
2. Select "Slack"
3. Choose "OAuth2" method
4. Follow OAuth flow to connect workspace
5. Save

### Email (SMTP) Credential
1. Settings → Credentials → Add Credential
2. Select "SMTP"
3. Configure:
   - Host: `smtp.gmail.com` (or your provider)
   - Port: `587`
   - User: Your email
   - Password: App password (not regular password)
4. Test & Save

### Google Sheets Credential (Optional)
1. Settings → Credentials → Add Credential
2. Select "Google Sheets"
3. Follow OAuth flow
4. Save

## Test the Integration

### 1. Test API Connection

In n8n, create a new workflow with an HTTP Request node:

```json
{
  "method": "GET",
  "url": "{{$env.LANGCHAIN_API_URL}}/health"
}
```

Execute the node. You should see:
```json
{
  "status": "healthy",
  "timestamp": "...",
  "components": [...]
}
```

### 2. Test Attribution Endpoint

HTTP Request node:
```json
{
  "method": "POST",
  "url": "{{$env.LANGCHAIN_API_URL}}/n8n/attribution",
  "body": {
    "contact_id": "test123",
    "total_value": 5000,
    "model_type": "w_shaped"
  }
}
```

Should return attribution results.

### 3. Activate Workflows

Once tested:
1. Open each workflow
2. Toggle "Active" in top right
3. Monitor execution logs

## Troubleshooting

### Issue: n8n can't reach your API

**Error:** "Connection refused" or "Timeout"

**Solution:**
1. Verify tunnel is running: `curl https://your-tunnel.ngrok.io/health`
2. Check API server is running: `curl http://localhost:8000/health`
3. Verify `LANGCHAIN_API_URL` is correct in n8n environment variables
4. Check ngrok/Cloudflare logs for incoming requests

### Issue: Webhook not working

**Error:** Webhooks from n8n not received

**Solution:**
1. Verify `N8N_WEBHOOK_BASE_URL` in your .env matches your tunnel URL
2. Test webhook endpoint:
   ```bash
   curl -X POST https://your-tunnel.ngrok.io/webhooks/n8n \
     -H "Content-Type: application/json" \
     -d '{"workflow_id":"test","execution_id":"123","event_type":"test","data":{}}'
   ```
3. Check API server logs for incoming requests

### Issue: Credentials not working in n8n

**Error:** "Authentication failed"

**Solution:**
1. Re-authenticate credentials in n8n Cloud
2. For Gmail SMTP, use App Password (not regular password)
3. Test credentials individually before using in workflows

### Issue: ngrok URL keeps changing

**Problem:** Free ngrok URLs change on restart

**Solutions:**
1. Upgrade to ngrok paid plan ($8/month) for persistent URLs
2. Use Cloudflare Tunnel (free, persistent)
3. Deploy API to cloud

## Security Considerations

### 1. Secure Your Tunnel

**ngrok:**
- Use auth token (required)
- Consider IP restrictions on paid plan

**Cloudflare:**
- Enable Cloudflare Access for authentication
- Set up firewall rules

### 2. API Security

Add authentication to your API endpoints:

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(credentials = Depends(security)):
    if credentials.credentials != settings.api_key:
        raise HTTPException(status_code=401)
    return credentials

@app.post("/n8n/attribution", dependencies=[Depends(verify_token)])
async def attribution(...):
    ...
```

### 3. Environment Variables

Never commit:
- API keys
- Tokens
- Passwords
- Tunnel URLs

Use `.env` file (already in `.gitignore`)

## Production Deployment

For production use, I recommend:

1. **Deploy API to Cloud:** Railway, Render, or AWS
2. **Use Cloudflare Tunnel:** If keeping API local but want reliability
3. **Add Authentication:** Secure your API endpoints
4. **Set up Monitoring:** Track API uptime and errors
5. **Use ngrok Pro:** If you prefer ngrok ($8/month for persistent URLs)

Would you like me to create a deployment guide for any specific cloud provider?

## Workflow URLs

Once set up, your workflows will be accessible at:

- **Attribution Pipeline:** https://your-instance.app.n8n.cloud/workflow/[workflow-id]
- **Campaign Reporting:** https://your-instance.app.n8n.cloud/workflow/[workflow-id]
- **Data Quality Audit:** https://your-instance.app.n8n.cloud/workflow/[workflow-id]

## Next Steps

1. ✅ Choose a tunnel solution (ngrok recommended for quick start)
2. ✅ Start your API server
3. ✅ Start your tunnel
4. ✅ Configure n8n Cloud environment variables
5. ✅ Import workflows to n8n Cloud
6. ✅ Configure credentials
7. ✅ Test the integration
8. ✅ Activate workflows

## Support

If you encounter issues:
1. Check this guide's troubleshooting section
2. Review API logs: `logs/company_hubspot.log`
3. Review n8n execution logs in the cloud UI
4. Check tunnel logs (ngrok/Cloudflare)

---

**Your n8n Cloud:** https://your-instance.app.n8n.cloud
**Status:** Ready to configure
**Next:** Choose tunnel solution and follow setup steps above
