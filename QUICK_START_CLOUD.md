# Quick Start - n8n Cloud Integration

**Your n8n Cloud:** https://your-instance.app.n8n.cloud

This is your fastest path to getting the hybrid system running with n8n Cloud.

## 5-Minute Setup

### Step 1: Install ngrok (2 minutes)

```bash
# Download and install from https://ngrok.com/download
# Or use package manager:
choco install ngrok  # Windows
# brew install ngrok/ngrok/ngrok  # Mac
```

Sign up and get auth token:
```bash
# Get token from: https://dashboard.ngrok.com/get-started/your-authtoken
ngrok config add-authtoken YOUR_TOKEN_HERE
```

### Step 2: Start API Server (30 seconds)

```bash
# In your project directory
python api_server.py
```

Should show:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 3: Start ngrok Tunnel (30 seconds)

**In a new terminal:**
```bash
ngrok http 8000
```

You'll see:
```
Forwarding  https://abc123-xyz-789.ngrok-free.app -> http://localhost:8000
```

**Copy the https URL!** You'll need it in the next step.

### Step 4: Configure n8n Cloud (1 minute)

1. Go to https://your-instance.app.n8n.cloud
2. Click Settings (bottom left)
3. Go to "Environments"
4. Click "Add Variable"
5. Add:
   - **Variable:** `LANGCHAIN_API_URL`
   - **Value:** `https://abc123-xyz-789.ngrok-free.app` (your ngrok URL)
   - **Type:** String
6. Click "Save"

### Step 5: Test Connection (1 minute)

In n8n Cloud:
1. Create new workflow (click "+")
2. Add "HTTP Request" node
3. Configure:
   - Method: `GET`
   - URL: `{{$env.LANGCHAIN_API_URL}}/health`
4. Click "Execute Node"

✅ Should return:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-10T...",
  "components": [...]
}
```

🎉 **Integration working!**

## Import Workflows

### Option A: Upload Files

1. In n8n Cloud, click "Add workflow" (top right)
2. Click the "..." menu → "Import from File"
3. Select `n8n_workflows/attribution_pipeline.json`
4. Click "Import"
5. Repeat for:
   - `campaign_reporting.json`
   - `data_quality_audit.json`

### Option B: Copy-Paste JSON

1. Open workflow JSON file in text editor
2. Copy entire contents
3. In n8n Cloud, click "Add workflow"
4. Click "..." menu → "Import from URL or String"
5. Paste JSON
6. Click "Import"

## Configure Credentials

### HubSpot (Required)

1. In n8n Cloud: Settings → Credentials → Add Credential
2. Search "HubSpot" → Select it
3. Choose "API Key" authentication
4. Enter your HubSpot private app token
5. Click "Save"

### Slack (Optional - for notifications)

1. Settings → Credentials → Add Credential
2. Search "Slack" → Select it
3. Choose "OAuth2" authentication
4. Click "Connect my account"
5. Follow OAuth flow
6. Save

### Gmail/SMTP (Optional - for email reports)

1. Settings → Credentials → Add Credential
2. Search "SMTP" → Select it
3. Configure:
   - **Host:** `smtp.gmail.com`
   - **Port:** `587`
   - **Secure:** Yes
   - **User:** your-email@gmail.com
   - **Password:** [Generate App Password](https://myaccount.google.com/apppasswords)
4. Click "Save"

**Note:** For Gmail, you MUST use an App Password, not your regular password.

## Update Workflow Credentials

For each imported workflow:

1. Open the workflow
2. Find nodes with red warning icon (❗)
3. Click the node
4. Select the credential you just created
5. Save the workflow

## Activate Workflows

1. **Attribution Pipeline:**
   - Open workflow
   - Toggle "Active" (top right)
   - Set to ON ✅

2. **Campaign Reporting:**
   - Open workflow
   - Toggle "Active"
   - Runs every Monday at 9am

3. **Data Quality Audit:**
   - Open workflow
   - Toggle "Active"
   - Runs daily at 8am

## Test Attribution Pipeline

Trigger the workflow manually:

```bash
curl -X POST https://your-instance.app.n8n.cloud/webhook/attribution_pipeline \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "test123",
    "total_value": 5000,
    "model_type": "w_shaped"
  }'
```

Check n8n Cloud executions tab to see the result!

## Common Issues

### ❌ "ECONNREFUSED" or "Timeout"

**Problem:** n8n can't reach your API

**Solution:**
1. Make sure API server is running: `http://localhost:8000/health`
2. Make sure ngrok is running
3. Verify `LANGCHAIN_API_URL` in n8n matches your ngrok URL exactly
4. Check ngrok logs for incoming requests

### ❌ "Credential not found"

**Problem:** Workflow can't find credential

**Solution:**
1. Open the workflow in n8n Cloud
2. Click nodes with warning icon
3. Select the credential from dropdown
4. Save workflow

### ❌ ngrok URL keeps changing

**Problem:** Free ngrok URLs change on restart

**Solutions:**
1. **Paid ngrok** ($8/month): Persistent URLs
2. **Cloudflare Tunnel** (free): See `N8N_CLOUD_SETUP.md`
3. **Deploy API to cloud:** See deployment guide

### ❌ "Invalid API key" for Gmail

**Problem:** Gmail rejects password

**Solution:**
1. Go to https://myaccount.google.com/apppasswords
2. Generate a new App Password
3. Use that instead of your regular password
4. Update credential in n8n

## What's Next?

### Customize Workflows

1. **Change approval threshold** (Attribution Pipeline):
   - Open workflow
   - Click "Check if High Value" node
   - Change `10000` to your preferred amount

2. **Change report schedule** (Campaign Reporting):
   - Open workflow
   - Click "Schedule Trigger" node
   - Modify cron expression

3. **Add more recipients**:
   - Open workflow with email/Slack nodes
   - Update recipient lists

### Add More Workflows

Create custom workflows in n8n Cloud that call your API:

```
Example: Deal Close Trigger
1. HubSpot Trigger: Deal stage → Closed Won
2. HTTP Request: POST to /n8n/attribution
3. Condition: Check attribution value
4. Update HubSpot with attribution data
5. Sync to ad platforms
6. Notify team via Slack
```

### Monitor Performance

In n8n Cloud:
- **Executions:** See all workflow runs
- **Logs:** Check for errors
- **Metrics:** Track success rate

## Keep It Running

### Option 1: Keep Terminal Open

Simple but requires computer to stay on:
```bash
# Terminal 1
python api_server.py

# Terminal 2
ngrok http 8000
```

### Option 2: Deploy to Cloud

For 24/7 availability, deploy your API:
- **Railway:** Easiest, ~$5/month
- **Render:** Free tier available
- **Heroku:** Classic choice, ~$7/month

I can provide deployment guides if needed!

## Your URLs

- **n8n Cloud:** https://your-instance.app.n8n.cloud
- **API Server:** http://localhost:8000
- **ngrok Tunnel:** https://[your-id].ngrok-free.app (changes on restart)
- **API Docs:** https://[your-id].ngrok-free.app/docs

## Support

Need help?
1. Check `N8N_CLOUD_SETUP.md` for detailed troubleshooting
2. Review n8n execution logs in cloud UI
3. Check API logs: Your terminal running `api_server.py`
4. Check ngrok logs: Your terminal running `ngrok`

---

**Status:** ✅ Ready to use
**Time to complete:** ~5 minutes
**Next:** Import workflows and test!
