"""
n8n Integration Module

Provides bidirectional integration between LangChain and n8n:
- Trigger n8n workflows from LangChain
- Receive webhooks from n8n workflows
- Query workflow execution status
- Pass attribution intelligence to visual workflows
"""
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
import json
from pydantic import BaseModel, Field, HttpUrl

from modules.exceptions import HubSpotIntegrationError
from modules.logging_utils import get_correlation_id
from tenacity import retry, stop_after_attempt, wait_exponential


# ============================================================================
# Request/Response Models
# ============================================================================

class N8nWorkflowTrigger(BaseModel):
    """Model for triggering n8n workflows"""
    workflow_name: str = Field(..., description="Name of the workflow to trigger")
    payload: Dict[str, Any] = Field(..., description="Data to pass to the workflow")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracking")
    wait_for_completion: bool = Field(False, description="Wait for workflow to complete")


class N8nWebhookPayload(BaseModel):
    """Model for incoming webhooks from n8n"""
    workflow_id: str = Field(..., description="n8n workflow ID")
    execution_id: str = Field(..., description="n8n execution ID")
    event_type: str = Field(..., description="Event type (success, error, approval_needed)")
    data: Dict[str, Any] = Field(default_factory=dict, description="Workflow data")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None


class N8nWorkflowResponse(BaseModel):
    """Response from n8n workflow execution"""
    execution_id: str
    status: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ============================================================================
# n8n Integration Manager
# ============================================================================

class N8nIntegrationManager:
    """
    Manages integration with n8n for visual workflow orchestration

    This bridges LangChain's intelligence with n8n's visual workflow capabilities,
    allowing operations teams to design and modify workflows while leveraging
    AI-powered attribution logic.
    """

    def __init__(
        self,
        n8n_base_url: str,
        n8n_api_key: Optional[str] = None,
        webhook_base_url: Optional[str] = None
    ):
        """
        Initialize n8n integration

        Args:
            n8n_base_url: Base URL of n8n instance (e.g., http://localhost:5678)
            n8n_api_key: n8n API key for authentication
            webhook_base_url: Base URL for receiving webhooks from n8n
        """
        self.n8n_base_url = n8n_base_url.rstrip('/')
        self.n8n_api_key = n8n_api_key
        self.webhook_base_url = webhook_base_url.rstrip('/') if webhook_base_url else None

        # Webhook handlers registry
        self.webhook_handlers: Dict[str, callable] = {}

        logger.info(f"n8n Integration initialized: {self.n8n_base_url}")

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for n8n API requests"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.n8n_api_key:
            headers["X-N8N-API-KEY"] = self.n8n_api_key
        return headers

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def trigger_workflow(
        self,
        workflow_name: str,
        payload: Dict[str, Any],
        wait_for_completion: bool = False,
        timeout: int = 300
    ) -> N8nWorkflowResponse:
        """
        Trigger an n8n workflow via webhook

        Args:
            workflow_name: Name/ID of the workflow to trigger
            payload: Data to pass to the workflow
            wait_for_completion: Whether to wait for workflow completion
            timeout: Timeout in seconds (only if wait_for_completion=True)

        Returns:
            N8nWorkflowResponse with execution details

        Example:
            >>> manager = N8nIntegrationManager("http://localhost:5678")
            >>> result = manager.trigger_workflow(
            ...     "attribution_pipeline",
            ...     {"contact_id": "12345", "value": 5000}
            ... )
        """
        correlation_id = get_correlation_id() or f"n8n_{datetime.utcnow().timestamp()}"

        # Add correlation ID to payload
        payload_with_context = {
            **payload,
            "correlation_id": correlation_id,
            "triggered_at": datetime.utcnow().isoformat(),
            "triggered_by": "langchain"
        }

        # n8n webhook URL format: {base_url}/webhook/{workflow_name}
        webhook_url = f"{self.n8n_base_url}/webhook/{workflow_name}"

        logger.info(f"Triggering n8n workflow: {workflow_name} | Correlation ID: {correlation_id}")

        try:
            response = requests.post(
                webhook_url,
                json=payload_with_context,
                headers=self._get_headers(),
                timeout=timeout if wait_for_completion else 30
            )
            response.raise_for_status()

            result = response.json()

            logger.info(
                f"n8n workflow triggered successfully: {workflow_name} | "
                f"Execution ID: {result.get('executionId', 'unknown')}"
            )

            return N8nWorkflowResponse(
                execution_id=result.get('executionId', result.get('execution_id', 'unknown')),
                status=result.get('status', 'triggered'),
                data=result.get('data', result)
            )

        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to trigger n8n workflow {workflow_name}: {str(e)}"
            logger.error(error_msg)
            return N8nWorkflowResponse(
                execution_id='unknown',
                status='error',
                error=error_msg
            )

    def trigger_attribution_workflow(
        self,
        contact_id: str,
        total_value: float,
        model_type: str = "w_shaped",
        touchpoints: Optional[List[Dict]] = None,
        notify: bool = True
    ) -> N8nWorkflowResponse:
        """
        Trigger the n8n attribution workflow

        This is a convenience method for the most common workflow: calculating
        attribution and syncing to ad platforms with optional notifications.

        Args:
            contact_id: HubSpot contact ID
            total_value: Total attributed value
            model_type: Attribution model to use
            touchpoints: Optional list of touchpoints
            notify: Whether to send notifications (Slack, email, etc.)

        Returns:
            N8nWorkflowResponse with execution details
        """
        payload = {
            "contact_id": contact_id,
            "total_value": total_value,
            "model_type": model_type,
            "touchpoints": touchpoints or [],
            "notify": notify,
            "source": "langchain_attribution"
        }

        return self.trigger_workflow("attribution_pipeline", payload)

    def trigger_campaign_reporting_workflow(
        self,
        utm_campaign: str,
        date_range: Dict[str, str],
        recipients: List[str]
    ) -> N8nWorkflowResponse:
        """
        Trigger the n8n campaign reporting workflow

        Args:
            utm_campaign: Campaign to report on
            date_range: Dict with 'start_date' and 'end_date'
            recipients: List of email addresses for report

        Returns:
            N8nWorkflowResponse with execution details
        """
        payload = {
            "utm_campaign": utm_campaign,
            "date_range": date_range,
            "recipients": recipients,
            "report_type": "campaign_performance"
        }

        return self.trigger_workflow("campaign_reporting", payload)

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
    def get_workflow_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """
        Get the status of a workflow execution

        Args:
            execution_id: n8n execution ID

        Returns:
            Execution status details
        """
        url = f"{self.n8n_base_url}/api/v1/executions/{execution_id}"

        try:
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get execution status for {execution_id}: {e}")
            return {"status": "unknown", "error": str(e)}

    def register_webhook_handler(self, event_type: str, handler: callable):
        """
        Register a handler for specific webhook event types

        Args:
            event_type: Type of event to handle (e.g., 'attribution_complete', 'approval_needed')
            handler: Function to call when event is received

        Example:
            >>> def handle_attribution_complete(payload):
            ...     print(f"Attribution completed: {payload.data}")
            >>>
            >>> manager.register_webhook_handler('attribution_complete', handle_attribution_complete)
        """
        self.webhook_handlers[event_type] = handler
        logger.info(f"Registered webhook handler for event type: {event_type}")

    def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming webhook from n8n

        Args:
            payload: Webhook payload from n8n

        Returns:
            Processing result
        """
        try:
            webhook_payload = N8nWebhookPayload(**payload)

            logger.info(
                f"Processing n8n webhook: {webhook_payload.event_type} | "
                f"Workflow: {webhook_payload.workflow_id} | "
                f"Execution: {webhook_payload.execution_id}"
            )

            # Call registered handler if exists
            if webhook_payload.event_type in self.webhook_handlers:
                handler = self.webhook_handlers[webhook_payload.event_type]
                result = handler(webhook_payload)

                return {
                    "status": "processed",
                    "event_type": webhook_payload.event_type,
                    "result": result
                }
            else:
                logger.warning(f"No handler registered for event type: {webhook_payload.event_type}")
                return {
                    "status": "no_handler",
                    "event_type": webhook_payload.event_type,
                    "message": "Webhook received but no handler registered"
                }

        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def get_webhook_url(self, endpoint: str = "n8n") -> Optional[str]:
        """
        Get the webhook URL for n8n to call back to

        Args:
            endpoint: Webhook endpoint name

        Returns:
            Full webhook URL or None if webhook_base_url not configured
        """
        if not self.webhook_base_url:
            return None
        return f"{self.webhook_base_url}/webhooks/{endpoint}"

    def list_workflows(self) -> List[Dict[str, Any]]:
        """
        List all workflows in n8n instance

        Returns:
            List of workflow details
        """
        url = f"{self.n8n_base_url}/api/v1/workflows"

        try:
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            workflows = response.json()

            logger.info(f"Retrieved {len(workflows.get('data', []))} workflows from n8n")
            return workflows.get('data', [])

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list workflows: {e}")
            return []

    def get_workflow_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get workflow details by name

        Args:
            name: Workflow name

        Returns:
            Workflow details or None if not found
        """
        workflows = self.list_workflows()
        for workflow in workflows:
            if workflow.get('name') == name:
                return workflow
        return None


# ============================================================================
# Workflow Templates for Common Scenarios
# ============================================================================

class N8nWorkflowTemplates:
    """
    Provides workflow template configurations for common scenarios

    These templates can be imported into n8n to quickly set up
    standard workflows that integrate with LangChain.
    """

    @staticmethod
    def get_attribution_pipeline_template() -> Dict[str, Any]:
        """
        Template for the main attribution pipeline workflow

        Flow:
        1. Webhook Trigger (receives contact data from LangChain)
        2. HTTP Request to LangChain (calculate attribution)
        3. Conditional Split (high value vs standard)
        4. Approval Node (for high-value attributions)
        5. HubSpot Update (update contact properties)
        6. Ad Platform Sync (sync to Google/Facebook/LinkedIn)
        7. Slack Notification (notify team)
        """
        return {
            "name": "Attribution Pipeline",
            "description": "Calculate attribution and sync to systems with approval workflow",
            "trigger": "webhook",
            "webhook_path": "attribution_pipeline",
            "steps": [
                {
                    "step": "trigger",
                    "type": "webhook",
                    "config": {
                        "path": "attribution_pipeline",
                        "method": "POST"
                    }
                },
                {
                    "step": "calculate_attribution",
                    "type": "http_request",
                    "config": {
                        "url": "{{$env.LANGCHAIN_API_URL}}/n8n/attribution",
                        "method": "POST",
                        "body": {
                            "contact_id": "={{$json.contact_id}}",
                            "total_value": "={{$json.total_value}}",
                            "model_type": "={{$json.model_type}}"
                        }
                    }
                },
                {
                    "step": "check_value",
                    "type": "if",
                    "config": {
                        "condition": "={{$json.total_value}} > 10000"
                    }
                },
                {
                    "step": "approval_required",
                    "type": "wait",
                    "config": {
                        "approval_webhook": "={{$env.LANGCHAIN_API_URL}}/webhooks/n8n/approval"
                    }
                },
                {
                    "step": "update_hubspot",
                    "type": "hubspot",
                    "config": {
                        "operation": "update",
                        "resource": "contact",
                        "contact_id": "={{$json.contact_id}}",
                        "properties": "={{$json.attribution_data}}"
                    }
                },
                {
                    "step": "sync_ad_platforms",
                    "type": "http_request",
                    "config": {
                        "url": "{{$env.LANGCHAIN_API_URL}}/n8n/ad-sync",
                        "method": "POST",
                        "body": "={{$json}}"
                    }
                },
                {
                    "step": "notify_slack",
                    "type": "slack",
                    "config": {
                        "channel": "#marketing-ops",
                        "message": "Attribution calculated for contact {{$json.contact_id}}: ${{$json.total_value}}"
                    }
                }
            ]
        }

    @staticmethod
    def get_campaign_reporting_template() -> Dict[str, Any]:
        """
        Template for automated campaign reporting workflow

        Flow:
        1. Schedule Trigger (weekly)
        2. HTTP Request to LangChain (get campaign metrics)
        3. Format Report (transform data)
        4. Send Email (distribute report)
        5. Update Google Sheets (archive data)
        """
        return {
            "name": "Campaign Reporting",
            "description": "Automated weekly campaign performance reports",
            "trigger": "schedule",
            "schedule": "0 9 * * 1",  # Every Monday at 9 AM
            "steps": [
                {
                    "step": "get_campaigns",
                    "type": "http_request",
                    "config": {
                        "url": "{{$env.LANGCHAIN_API_URL}}/campaigns",
                        "method": "GET",
                        "qs": {
                            "sort_by": "total_attributed_value",
                            "limit": 50
                        }
                    }
                },
                {
                    "step": "format_report",
                    "type": "code",
                    "config": {
                        "language": "javascript",
                        "code": "// Format campaign data for email"
                    }
                },
                {
                    "step": "send_email",
                    "type": "email_send",
                    "config": {
                        "to": "={{$json.recipients}}",
                        "subject": "Weekly Campaign Performance Report",
                        "html": "={{$json.formatted_report}}"
                    }
                }
            ]
        }

    @staticmethod
    def get_data_quality_audit_template() -> Dict[str, Any]:
        """
        Template for data quality audit workflow

        Flow:
        1. Schedule Trigger (daily)
        2. HTTP Request to LangChain (run data audit)
        3. Check Quality Score
        4. If low quality: Send alert
        5. Log to database
        """
        return {
            "name": "Data Quality Audit",
            "description": "Daily data quality checks with alerting",
            "trigger": "schedule",
            "schedule": "0 8 * * *",  # Every day at 8 AM
            "steps": [
                {
                    "step": "run_audit",
                    "type": "http_request",
                    "config": {
                        "url": "{{$env.LANGCHAIN_API_URL}}/n8n/audit",
                        "method": "POST"
                    }
                },
                {
                    "step": "check_quality",
                    "type": "if",
                    "config": {
                        "condition": "={{$json.quality_score}} < 80"
                    }
                },
                {
                    "step": "alert_team",
                    "type": "slack",
                    "config": {
                        "channel": "#marketing-ops",
                        "message": "⚠️ Data quality alert: Score {{$json.quality_score}}%"
                    }
                }
            ]
        }


# ============================================================================
# Helper Functions
# ============================================================================

def create_n8n_manager_from_settings(settings) -> Optional[N8nIntegrationManager]:
    """
    Create n8n manager from application settings

    Args:
        settings: Application settings object

    Returns:
        N8nIntegrationManager instance or None if not configured
    """
    if not hasattr(settings, 'n8n_base_url') or not settings.n8n_base_url:
        logger.warning("n8n integration not configured")
        return None

    return N8nIntegrationManager(
        n8n_base_url=settings.n8n_base_url,
        n8n_api_key=getattr(settings, 'n8n_api_key', None),
        webhook_base_url=getattr(settings, 'n8n_webhook_base_url', None)
    )
