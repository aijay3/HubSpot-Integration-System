# n8n Workflow Templates

This directory contains pre-built n8n workflow templates that integrate with the LangChain attribution system. These workflows demonstrate the hybrid architecture where n8n handles orchestration and LangChain provides intelligence.

## Available Workflows

### 1. Attribution Pipeline with Approval (`attribution_pipeline.json`)

**Purpose:** Calculate attribution using LangChain and sync to systems with approval workflow for high-value conversions.

**Flow:**
1. Webhook trigger receives attribution request
2. Calls LangChain API to calculate attribution
3. Checks if value is above $10,000 threshold
4. **Low value:** Updates HubSpot immediately
5. **High value:** Sends Slack notification and waits for approval
6. After approval, updates HubSpot
7. Syncs conversion to ad platforms (Google Ads, Facebook, LinkedIn)
8. Sends completion notification to Slack

**Use Cases:**
- Automated attribution processing with human-in-the-loop for large deals
- Ensures high-value attributions are reviewed before syncing
- Multi-platform coordination (HubSpot + Ad Platforms + Slack)

### 2. Weekly Campaign Performance Report (`campaign_reporting.json`)

**Purpose:** Automated weekly reporting of campaign performance with distribution via email and Slack.

**Flow:**
1. Schedule trigger (Monday 9am)
2. Fetches campaign metrics from LangChain API
3. Fetches attribution summary for last 7 days
4. Formats HTML report with tables and charts
5. Sends email report to marketing and sales teams
6. Posts summary to Slack
7. Archives data to Google Sheets for historical tracking

**Use Cases:**
- Regular performance reporting without manual work
- Consistent data distribution to stakeholders
- Historical data archival for trend analysis

### 3. Daily Data Quality Audit (`data_quality_audit.json`)

**Purpose:** Daily automated data quality checks with alerting for issues.

**Flow:**
1. Schedule trigger (Daily 8am)
2. Calls LangChain API to run data quality audit
3. Checks quality score against threshold (80%)
4. **Good quality:** Sends success notification to Slack
5. **Low quality:** Sends alert to Slack
6. **Critical (<60%):** Sends email alert to leadership
7. Logs all results to Google Sheets

**Use Cases:**
- Proactive data quality monitoring
- Early detection of tracking issues
- Compliance and audit trail

## Installation

### Prerequisites

1. **n8n Instance:** Running n8n (local or cloud)
2. **LangChain API:** API server running at configured URL
3. **Credentials Configured:**
   - HubSpot API
   - Slack API
   - Email SMTP
   - Google Sheets (optional)

### Setup Steps

#### 1. Configure Environment Variables in n8n

Go to n8n Settings → Environments and add:

```bash
LANGCHAIN_API_URL=http://localhost:8000
HUBSPOT_PORTAL_ID=your_portal_id
```

#### 2. Import Workflows

1. Open n8n
2. Click "+" to create a new workflow
3. Click the "..." menu in top right
4. Select "Import from File"
5. Choose one of the JSON files from this directory
6. Click "Import"

#### 3. Configure Credentials

Each workflow uses credentials that need to be configured:

- **HubSpot:** Settings → Credentials → Add Credential → HubSpot
- **Slack:** Settings → Credentials → Add Credential → Slack
- **Email:** Settings → Credentials → Add Credential → SMTP
- **Google Sheets:** Settings → Credentials → Add Credential → Google Sheets

#### 4. Update Node Settings

After import, update these nodes with your specific values:

**Slack Nodes:**
- Replace channel ID `C12345678` with your actual Slack channel ID
- Find channel ID in Slack: Right-click channel → View channel details

**Google Sheets Nodes (if using):**
- Replace document ID with your Google Sheet ID
- Configure sheet name and column mappings

**Email Nodes:**
- Update recipient email addresses
- Update sender email address

#### 5. Activate Workflows

1. Click the toggle in top right to "Active"
2. Workflows with schedule triggers will run automatically
3. Workflows with webhook triggers will be available at the webhook URL

## Testing Workflows

### Test Attribution Pipeline

Send a POST request to trigger the workflow:

```bash
curl -X POST http://localhost:5678/webhook/attribution_pipeline \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "12345",
    "total_value": 5000,
    "model_type": "w_shaped"
  }'
```

### Test Campaign Reporting

Manually trigger the workflow in n8n:
1. Open the workflow
2. Click "Execute Workflow" button
3. Review the execution log

### Test Data Quality Audit

Manually trigger or wait for scheduled execution:
1. Open the workflow
2. Click "Execute Workflow" button
3. Check Slack for notification

## Customization

### Modify Approval Threshold

In `attribution_pipeline.json`, change the value in the "Check if High Value" node:

```json
{
  "value2": 10000  // Change this to your desired threshold
}
```

### Change Schedule

In `campaign_reporting.json` or `data_quality_audit.json`, modify the cron expression:

```json
{
  "expression": "0 9 * * 1"  // Monday at 9am
}
```

Common schedules:
- `0 8 * * *` - Daily at 8am
- `0 9 * * 1` - Monday at 9am
- `0 17 * * 5` - Friday at 5pm
- `0 0 1 * *` - First day of month at midnight

### Add More Recipients

In email or Slack nodes, add more recipients:

```json
{
  "toEmail": "marketing@company.com, sales@company.com, exec@company.com"
}
```

## Workflow Patterns

### Pattern 1: Intelligence + Orchestration

```
n8n (Orchestration) ─→ LangChain (Intelligence) ─→ n8n (Actions)
```

Example: Attribution pipeline calls LangChain to calculate attribution, then orchestrates updates across multiple systems.

### Pattern 2: Scheduled Intelligence

```
n8n Schedule ─→ LangChain Analysis ─→ n8n Distribution
```

Example: Campaign reporting fetches data from LangChain API and distributes formatted reports.

### Pattern 3: Monitoring + Alerting

```
n8n Schedule ─→ LangChain Audit ─→ n8n Conditional Alerts
```

Example: Data quality audit runs analysis and sends alerts based on thresholds.

## Best Practices

1. **Error Handling:** All workflows include error handling. Check execution logs if issues occur.

2. **Testing:** Always test workflows with sample data before activating.

3. **Credentials:** Never commit credentials to version control. Use n8n's credential system.

4. **Monitoring:** Set up Slack notifications for workflow failures (n8n Settings → Error Workflow).

5. **Documentation:** Document any customizations you make to workflows.

6. **Backup:** Export workflows regularly as backup (Workflows → ... → Export).

## Troubleshooting

### Workflow Not Triggering

**Issue:** Webhook workflows not receiving requests.

**Solution:**
- Check webhook URL: `http://your-n8n-url/webhook/workflow_name`
- Verify n8n is accessible from LangChain API
- Check n8n logs for errors

### LangChain API Connection Failed

**Issue:** HTTP request nodes failing to connect.

**Solution:**
- Verify `LANGCHAIN_API_URL` environment variable
- Test API endpoint with curl
- Check firewall/network settings

### Credential Errors

**Issue:** "Credentials not found" errors.

**Solution:**
- Re-configure credentials in n8n Settings
- Ensure credentials are linked to correct nodes
- Test credentials with a simple workflow

### Execution Timeout

**Issue:** Workflows timing out during execution.

**Solution:**
- Increase timeout in HTTP Request node options
- Check LangChain API performance
- Consider splitting into multiple workflows

## Advanced Usage

### Chaining Workflows

Trigger one workflow from another:

```json
{
  "method": "POST",
  "url": "http://localhost:5678/webhook/other_workflow",
  "body": {
    "data": "={{$json}}"
  }
}
```

### Conditional Logic

Add complex conditions:

```json
{
  "conditions": {
    "boolean": [
      {"value1": "={{$json.approved}}", "value2": true}
    ],
    "number": [
      {"value1": "={{$json.value}}", "operation": "larger", "value2": 1000}
    ]
  }
}
```

### Custom Code

Add JavaScript nodes for custom logic:

```javascript
// Example: Format data
const items = $input.all();
const formatted = items.map(item => ({
  ...item.json,
  formatted_value: `$${item.json.value.toLocaleString()}`
}));
return formatted;
```

## Support

For issues or questions:
1. Check n8n documentation: https://docs.n8n.io
2. Review LangChain API documentation in main README
3. Check execution logs in n8n
4. Contact Marketing Operations team

## Contributing

When creating new workflows:
1. Export as JSON
2. Add to this directory
3. Document in this README
4. Include configuration instructions
5. Test thoroughly before sharing
