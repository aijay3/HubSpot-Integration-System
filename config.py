"""
Configuration module for HubSpot Integration System
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator, Field
from typing import Literal
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables with validation"""

    # HubSpot
    hubspot_api_key: str = Field(..., min_length=1)
    hubspot_portal_id: str = Field(..., min_length=1)

    # Google Ads
    google_ads_client_id: str = ""
    google_ads_client_secret: str = ""
    google_ads_developer_token: str = ""
    google_ads_refresh_token: str = ""
    google_ads_customer_id: str = ""

    # Facebook Ads
    facebook_access_token: str = ""
    facebook_ad_account_id: str = ""
    facebook_app_id: str = ""
    facebook_app_secret: str = ""

    # LinkedIn Ads
    linkedin_access_token: str = ""
    linkedin_ad_account_id: str = ""

    # Database
    database_url: str = "postgresql://user:password@localhost:5432/company_attribution"

    # OpenAI
    openai_api_key: str = Field(..., min_length=1)

    # Supabase Configuration (for RAG)
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_role_key: str = ""

    # Attribution Configuration
    attribution_model: Literal["first_touch", "last_touch", "linear", "w_shaped", "full_path"] = "w_shaped"
    attribution_lookback_days: int = Field(default=90, ge=1, le=365)

    # Logging
    log_level: str = Field(default="INFO", pattern=r'^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$')
    log_file_path: str = "./logs/company_hubspot.log"

    # n8n Integration (Optional)
    n8n_base_url: str = ""
    n8n_api_key: str = ""
    n8n_webhook_base_url: str = ""  # URL where this API server receives webhooks from n8n

    @field_validator('hubspot_api_key', 'openai_api_key')
    @classmethod
    def validate_api_keys(cls, v: str) -> str:
        """Validate API keys are not placeholder values"""
        if 'your_' in v.lower() or '_here' in v.lower():
            raise ValueError('API key appears to be a placeholder. Please provide a valid API key.')
        return v

    @field_validator('log_file_path')
    @classmethod
    def validate_log_path(cls, v: str) -> str:
        """Ensure log directory exists"""
        log_dir = os.path.dirname(v)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        return v

    model_config = {
        "env_file": ".env",
        "case_sensitive": False
    }


# Global settings instance
settings = Settings()
