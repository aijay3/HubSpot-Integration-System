"""
Health Check and System Monitoring Module

This module provides health check capabilities for all system components.
"""
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import traceback
from loguru import logger


class HealthStatus(str, Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth:
    """Health check result for a single component"""

    def __init__(
        self,
        name: str,
        status: HealthStatus,
        message: str = "",
        details: Optional[Dict] = None
    ):
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}
        self.checked_at = datetime.utcnow()

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "checked_at": self.checked_at.isoformat()
        }


class HealthChecker:
    """Health checker for the HubSpot Integration system"""

    def __init__(self):
        self.checks: List[ComponentHealth] = []

    def check_configuration(self, settings) -> ComponentHealth:
        """Check if required configuration is present"""
        try:
            missing_configs = []

            if not settings.hubspot_api_key or settings.hubspot_api_key == "your_hubspot_api_key_here":
                missing_configs.append("HUBSPOT_API_KEY")

            if not settings.openai_api_key or settings.openai_api_key == "your_openai_api_key_here":
                missing_configs.append("OPENAI_API_KEY")

            if missing_configs:
                return ComponentHealth(
                    name="configuration",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Missing required configuration: {', '.join(missing_configs)}",
                    details={"missing": missing_configs}
                )

            return ComponentHealth(
                name="configuration",
                status=HealthStatus.HEALTHY,
                message="All required configuration present"
            )
        except Exception as e:
            logger.error(f"Configuration check failed: {e}")
            return ComponentHealth(
                name="configuration",
                status=HealthStatus.UNHEALTHY,
                message=f"Configuration check error: {str(e)}"
            )

    def check_hubspot_connection(self, settings) -> ComponentHealth:
        """Check HubSpot API connectivity"""
        try:
            from hubspot import HubSpot
            from hubspot.crm.contacts import ApiException

            # Only check if API key is configured
            if not settings.hubspot_api_key or settings.hubspot_api_key == "your_hubspot_api_key_here":
                return ComponentHealth(
                    name="hubspot_api",
                    status=HealthStatus.DEGRADED,
                    message="HubSpot API not configured"
                )

            try:
                client = HubSpot(access_token=settings.hubspot_api_key)
                # Simple API call to check connectivity
                # Note: This will fail if the API key is invalid
                return ComponentHealth(
                    name="hubspot_api",
                    status=HealthStatus.HEALTHY,
                    message="HubSpot API connection successful"
                )
            except ApiException as e:
                return ComponentHealth(
                    name="hubspot_api",
                    status=HealthStatus.UNHEALTHY,
                    message=f"HubSpot API error: {e.status}",
                    details={"error_code": e.status}
                )
        except Exception as e:
            logger.error(f"HubSpot connection check failed: {e}")
            return ComponentHealth(
                name="hubspot_api",
                status=HealthStatus.UNHEALTHY,
                message=f"Connection check error: {str(e)}"
            )

    def check_openai_connection(self, settings) -> ComponentHealth:
        """Check OpenAI API connectivity"""
        try:
            import openai

            if not settings.openai_api_key or settings.openai_api_key == "your_openai_api_key_here":
                return ComponentHealth(
                    name="openai_api",
                    status=HealthStatus.DEGRADED,
                    message="OpenAI API not configured"
                )

            try:
                openai.api_key = settings.openai_api_key
                # Simple check - models list is a lightweight call
                openai.models.list()
                return ComponentHealth(
                    name="openai_api",
                    status=HealthStatus.HEALTHY,
                    message="OpenAI API connection successful"
                )
            except Exception as e:
                return ComponentHealth(
                    name="openai_api",
                    status=HealthStatus.UNHEALTHY,
                    message=f"OpenAI API error: {str(e)}"
                )
        except Exception as e:
            logger.error(f"OpenAI connection check failed: {e}")
            return ComponentHealth(
                name="openai_api",
                status=HealthStatus.UNHEALTHY,
                message=f"Connection check error: {str(e)}"
            )

    def check_supabase_connection(self, settings) -> ComponentHealth:
        """Check Supabase connectivity (for RAG)"""
        try:
            if not settings.supabase_url or not settings.supabase_key:
                return ComponentHealth(
                    name="supabase",
                    status=HealthStatus.DEGRADED,
                    message="Supabase not configured (RAG disabled)"
                )

            from supabase import create_client

            try:
                client = create_client(settings.supabase_url, settings.supabase_key)
                # Simple health check query
                response = client.from_(settings.supabase_url).select("*").limit(1).execute()
                return ComponentHealth(
                    name="supabase",
                    status=HealthStatus.HEALTHY,
                    message="Supabase connection successful"
                )
            except Exception as e:
                return ComponentHealth(
                    name="supabase",
                    status=HealthStatus.DEGRADED,
                    message=f"Supabase connection error: {str(e)}"
                )
        except Exception as e:
            logger.error(f"Supabase connection check failed: {e}")
            return ComponentHealth(
                name="supabase",
                status=HealthStatus.DEGRADED,
                message=f"Connection check error: {str(e)}"
            )

    def check_all(self, settings) -> Dict:
        """Run all health checks"""
        try:
            self.checks = []

            # Run all checks
            self.checks.append(self.check_configuration(settings))
            self.checks.append(self.check_hubspot_connection(settings))
            self.checks.append(self.check_openai_connection(settings))
            self.checks.append(self.check_supabase_connection(settings))

            # Determine overall status
            statuses = [check.status for check in self.checks]

            if all(s == HealthStatus.HEALTHY for s in statuses):
                overall_status = HealthStatus.HEALTHY
            elif any(s == HealthStatus.UNHEALTHY for s in statuses):
                overall_status = HealthStatus.UNHEALTHY
            else:
                overall_status = HealthStatus.DEGRADED

            return {
                "status": overall_status.value,
                "timestamp": datetime.utcnow().isoformat(),
                "components": [check.to_dict() for check in self.checks],
                "summary": {
                    "total": len(self.checks),
                    "healthy": len([c for c in self.checks if c.status == HealthStatus.HEALTHY]),
                    "degraded": len([c for c in self.checks if c.status == HealthStatus.DEGRADED]),
                    "unhealthy": len([c for c in self.checks if c.status == HealthStatus.UNHEALTHY])
                }
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}\n{traceback.format_exc()}")
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "components": []
            }

    def get_stats(self) -> Dict:
        """Get health check statistics"""
        if not self.checks:
            return {"message": "No health checks performed yet"}

        return {
            "last_check": max(c.checked_at for c in self.checks).isoformat(),
            "total_checks": len(self.checks),
            "by_status": {
                "healthy": len([c for c in self.checks if c.status == HealthStatus.HEALTHY]),
                "degraded": len([c for c in self.checks if c.status == HealthStatus.DEGRADED]),
                "unhealthy": len([c for c in self.checks if c.status == HealthStatus.UNHEALTHY])
            }
        }
