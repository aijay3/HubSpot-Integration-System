"""
Data models for attribution tracking
"""
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum
import re


class LifecycleStage(str, Enum):
    """HubSpot lifecycle stages"""
    SUBSCRIBER = "subscriber"
    LEAD = "lead"
    MARKETING_QUALIFIED_LEAD = "marketingqualifiedlead"
    SALES_QUALIFIED_LEAD = "salesqualifiedlead"
    OPPORTUNITY = "opportunity"
    CUSTOMER = "customer"
    EVANGELIST = "evangelist"
    OTHER = "other"


class TouchpointType(str, Enum):
    """Types of marketing touchpoints"""
    ORGANIC_SEARCH = "organic_search"
    PAID_SEARCH = "paid_search"
    SOCIAL_MEDIA = "social_media"
    PAID_SOCIAL = "paid_social"
    EMAIL = "email"
    DIRECT = "direct"
    REFERRAL = "referral"
    AFFILIATE = "affiliate"
    DISPLAY = "display"
    OTHER = "other"


class UTMParameters(BaseModel):
    """UTM tracking parameters with validation"""
    utm_source: Optional[str] = Field(None, max_length=255)
    utm_medium: Optional[str] = Field(None, max_length=255)
    utm_campaign: Optional[str] = Field(None, max_length=255)
    utm_term: Optional[str] = Field(None, max_length=255)
    utm_content: Optional[str] = Field(None, max_length=255)

    @field_validator('utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content')
    @classmethod
    def validate_utm_parameter(cls, v: Optional[str]) -> Optional[str]:
        """Validate UTM parameters - lowercase, no spaces, alphanumeric with hyphens/underscores"""
        if v is None:
            return v
        # Strip whitespace
        v = v.strip()
        if not v:
            return None
        # Check for invalid characters
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('UTM parameters must contain only letters, numbers, hyphens, and underscores')
        # Convert to lowercase for consistency
        return v.lower()


class ClickID(BaseModel):
    """Ad platform click IDs with validation"""
    gclid: Optional[str] = Field(None, max_length=500)  # Google Ads
    fbclid: Optional[str] = Field(None, max_length=500)  # Facebook Ads
    msclkid: Optional[str] = Field(None, max_length=500)  # Microsoft Ads
    li_fat_id: Optional[str] = Field(None, max_length=500)  # LinkedIn Ads

    @field_validator('gclid', 'fbclid', 'msclkid', 'li_fat_id')
    @classmethod
    def validate_click_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate click IDs - alphanumeric and basic special characters only"""
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        # Allow alphanumeric, hyphens, underscores, and dots
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError('Click IDs must contain only letters, numbers, hyphens, underscores, and dots')
        return v


class Touchpoint(BaseModel):
    """Individual marketing touchpoint"""
    touchpoint_id: str = Field(default_factory=lambda: f"tp_{datetime.utcnow().timestamp()}")
    contact_id: str
    timestamp: datetime
    touchpoint_type: TouchpointType
    utm_parameters: UTMParameters
    click_ids: ClickID = Field(default_factory=ClickID)
    session_id: Optional[str] = None
    page_url: Optional[str] = None
    referrer_url: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    partner_id: Optional[str] = None  # For affiliate/partner tracking
    lifecycle_stage_at_touch: Optional[LifecycleStage] = None
    additional_data: Dict = Field(default_factory=dict)


class Contact(BaseModel):
    """HubSpot contact with attribution data and validation"""
    contact_id: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=255)
    lifecycle_stage: LifecycleStage
    created_at: datetime
    updated_at: datetime
    first_touch: Optional[Touchpoint] = None
    last_touch: Optional[Touchpoint] = None
    all_touchpoints: List[Touchpoint] = Field(default_factory=list)
    attributed_revenue: Optional[float] = Field(None, ge=0)
    custom_properties: Dict = Field(default_factory=dict)

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format"""
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v.lower()

    @field_validator('contact_id')
    @classmethod
    def validate_contact_id(cls, v: str) -> str:
        """Validate contact ID is not empty"""
        if not v or not v.strip():
            raise ValueError('Contact ID cannot be empty')
        return v.strip()


class AttributionModel(BaseModel):
    """Attribution calculation result with validation"""
    contact_id: str = Field(..., min_length=1)
    model_type: str = Field(..., pattern=r'^(first_touch|last_touch|linear|w_shaped|full_path)$')
    touchpoint_credits: Dict[str, float] = Field(default_factory=dict)
    total_value: float = Field(..., ge=0)
    calculated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator('touchpoint_credits')
    @classmethod
    def validate_credits(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate that all credit values are non-negative"""
        for touchpoint_id, credit in v.items():
            if credit < 0:
                raise ValueError(f'Credit for {touchpoint_id} cannot be negative')
        return v


class ConversionEvent(BaseModel):
    """Lifecycle stage conversion event with validation"""
    event_id: str = Field(default_factory=lambda: f"ev_{datetime.utcnow().timestamp()}")
    contact_id: str = Field(..., min_length=1)
    from_stage: LifecycleStage
    to_stage: LifecycleStage
    timestamp: datetime
    attributed_touchpoints: List[str] = Field(default_factory=list)
    conversion_value: Optional[float] = Field(None, ge=0)
    synced_to_ad_platforms: List[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def validate_stage_progression(self) -> 'ConversionEvent':
        """Validate that from_stage and to_stage are different"""
        if self.from_stage == self.to_stage:
            raise ValueError('from_stage and to_stage must be different')
        return self
