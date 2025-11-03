"""
Custom Exception Classes for HubSpot Integration

This module defines custom exceptions for better error handling and debugging.
"""


class HubSpotIntegrationError(Exception):
    """Base exception for all HubSpot integration errors"""
    pass


class APIConnectionError(HubSpotIntegrationError):
    """Raised when unable to connect to external API"""
    def __init__(self, service: str, message: str):
        self.service = service
        super().__init__(f"Failed to connect to {service}: {message}")


class APIRateLimitError(HubSpotIntegrationError):
    """Raised when API rate limit is exceeded"""
    def __init__(self, service: str, retry_after: int = None):
        self.service = service
        self.retry_after = retry_after
        msg = f"Rate limit exceeded for {service}"
        if retry_after:
            msg += f". Retry after {retry_after} seconds"
        super().__init__(msg)


class AuthenticationError(HubSpotIntegrationError):
    """Raised when authentication fails"""
    def __init__(self, service: str, message: str = "Authentication failed"):
        self.service = service
        super().__init__(f"{service}: {message}")


class ValidationError(HubSpotIntegrationError):
    """Raised when data validation fails"""
    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"Validation error for {field}: {message}")


class ConfigurationError(HubSpotIntegrationError):
    """Raised when configuration is invalid or missing"""
    def __init__(self, message: str):
        super().__init__(f"Configuration error: {message}")


class AttributionCalculationError(HubSpotIntegrationError):
    """Raised when attribution calculation fails"""
    def __init__(self, contact_id: str, message: str):
        self.contact_id = contact_id
        super().__init__(f"Attribution calculation failed for contact {contact_id}: {message}")


class SyncError(HubSpotIntegrationError):
    """Raised when syncing data to external platforms fails"""
    def __init__(self, platform: str, message: str):
        self.platform = platform
        super().__init__(f"Failed to sync to {platform}: {message}")


class RAGSystemError(HubSpotIntegrationError):
    """Raised when RAG system operations fail"""
    def __init__(self, operation: str, message: str):
        self.operation = operation
        super().__init__(f"RAG system error during {operation}: {message}")


class DatabaseError(HubSpotIntegrationError):
    """Raised when database operations fail"""
    def __init__(self, operation: str, message: str):
        self.operation = operation
        super().__init__(f"Database error during {operation}: {message}")
