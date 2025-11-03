"""
SQLAlchemy Database Models

This module defines the database schema for storing attribution data,
touchpoints, conversions, and analytics locally in PostgreSQL.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, JSON, Text,
    ForeignKey, Index, Enum as SQLEnum, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
import enum


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class LifecycleStageEnum(str, enum.Enum):
    """Lifecycle stage enumeration"""
    SUBSCRIBER = "subscriber"
    LEAD = "lead"
    MARKETING_QUALIFIED_LEAD = "marketingqualifiedlead"
    SALES_QUALIFIED_LEAD = "salesqualifiedlead"
    OPPORTUNITY = "opportunity"
    CUSTOMER = "customer"
    EVANGELIST = "evangelist"
    OTHER = "other"


class AttributionModelEnum(str, enum.Enum):
    """Attribution model enumeration"""
    FIRST_TOUCH = "first_touch"
    LAST_TOUCH = "last_touch"
    LINEAR = "linear"
    W_SHAPED = "w_shaped"
    FULL_PATH = "full_path"


# ============================================================================
# Core Models
# ============================================================================

class Contact(Base):
    """
    HubSpot contact with attribution data

    Stores locally for analytics and reporting
    """
    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # HubSpot contact ID
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    lifecycle_stage: Mapped[Optional[LifecycleStageEnum]] = mapped_column(
        SQLEnum(LifecycleStageEnum),
        index=True
    )

    # Click IDs for ad platform attribution
    gclid: Mapped[Optional[str]] = mapped_column(String(255))
    fbclid: Mapped[Optional[str]] = mapped_column(String(255))
    msclkid: Mapped[Optional[str]] = mapped_column(String(255))

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced_from_hubspot: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # HubSpot metadata
    hubspot_owner_id: Mapped[Optional[str]] = mapped_column(String(50))
    hubspot_created_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    touchpoints: Mapped[List["Touchpoint"]] = relationship("Touchpoint", back_populates="contact", cascade="all, delete-orphan")
    conversions: Mapped[List["Conversion"]] = relationship("Conversion", back_populates="contact", cascade="all, delete-orphan")
    attribution_results: Mapped[List["AttributionResult"]] = relationship("AttributionResult", back_populates="contact", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_contact_email', 'email'),
        Index('idx_contact_lifecycle', 'lifecycle_stage'),
        Index('idx_contact_gclid', 'gclid'),
    )


class Touchpoint(Base):
    """
    Marketing touchpoint (interaction)

    Each touchpoint represents a marketing interaction captured via UTM parameters
    """
    __tablename__ = "touchpoints"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    contact_id: Mapped[str] = mapped_column(String(50), ForeignKey("contacts.id"), index=True)

    # UTM Parameters
    utm_source: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    utm_term: Mapped[Optional[str]] = mapped_column(String(255))
    utm_content: Mapped[Optional[str]] = mapped_column(String(255))

    # Touchpoint metadata
    page_url: Mapped[Optional[str]] = mapped_column(Text)
    referrer_url: Mapped[Optional[str]] = mapped_column(Text)
    landing_page: Mapped[Optional[str]] = mapped_column(Text)

    # Click IDs
    gclid: Mapped[Optional[str]] = mapped_column(String(255))
    fbclid: Mapped[Optional[str]] = mapped_column(String(255))
    msclkid: Mapped[Optional[str]] = mapped_column(String(255))

    # Session info
    session_id: Mapped[Optional[str]] = mapped_column(String(100))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))  # IPv6 compatible

    # Timing
    occurred_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Attribution weight (calculated during attribution)
    attribution_weight: Mapped[Optional[float]] = mapped_column(Float)
    attributed_value: Mapped[Optional[float]] = mapped_column(Float)

    # Relationships
    contact: Mapped["Contact"] = relationship("Contact", back_populates="touchpoints")

    __table_args__ = (
        Index('idx_touchpoint_contact', 'contact_id'),
        Index('idx_touchpoint_utm_campaign', 'utm_campaign'),
        Index('idx_touchpoint_occurred', 'occurred_at'),
        Index('idx_touchpoint_utm_source_medium', 'utm_source', 'utm_medium'),
    )


class Conversion(Base):
    """
    Lifecycle stage conversion event

    Tracks when a contact moves between lifecycle stages
    """
    __tablename__ = "conversions"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    contact_id: Mapped[str] = mapped_column(String(50), ForeignKey("contacts.id"), index=True)

    # Conversion details
    from_stage: Mapped[Optional[LifecycleStageEnum]] = mapped_column(SQLEnum(LifecycleStageEnum))
    to_stage: Mapped[LifecycleStageEnum] = mapped_column(SQLEnum(LifecycleStageEnum), index=True)
    conversion_value: Mapped[Optional[float]] = mapped_column(Float)

    # Ad platform syncing
    synced_to_google_ads: Mapped[bool] = mapped_column(Boolean, default=False)
    synced_to_facebook: Mapped[bool] = mapped_column(Boolean, default=False)
    synced_to_linkedin: Mapped[bool] = mapped_column(Boolean, default=False)
    sync_errors: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Timing
    occurred_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    contact: Mapped["Contact"] = relationship("Contact", back_populates="conversions")

    __table_args__ = (
        Index('idx_conversion_contact', 'contact_id'),
        Index('idx_conversion_to_stage', 'to_stage'),
        Index('idx_conversion_occurred', 'occurred_at'),
    )


class AttributionResult(Base):
    """
    Attribution calculation result

    Stores the output of attribution model calculations
    """
    __tablename__ = "attribution_results"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    contact_id: Mapped[str] = mapped_column(String(50), ForeignKey("contacts.id"), index=True)

    # Attribution model used
    model_type: Mapped[AttributionModelEnum] = mapped_column(SQLEnum(AttributionModelEnum), index=True)

    # Results
    total_value: Mapped[float] = mapped_column(Float)
    touchpoint_count: Mapped[int] = mapped_column(Integer)
    touchpoint_attributions: Mapped[dict] = mapped_column(JSONB)  # touchpoint_id -> {weight, value}

    # Top channels (denormalized for quick queries)
    top_source: Mapped[Optional[str]] = mapped_column(String(255))
    top_medium: Mapped[Optional[str]] = mapped_column(String(255))
    top_campaign: Mapped[Optional[str]] = mapped_column(String(255))

    # Metadata
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    lookback_days: Mapped[int] = mapped_column(Integer)

    # Relationships
    contact: Mapped["Contact"] = relationship("Contact", back_populates="attribution_results")

    __table_args__ = (
        Index('idx_attribution_contact', 'contact_id'),
        Index('idx_attribution_model', 'model_type'),
        Index('idx_attribution_calculated', 'calculated_at'),
    )


# ============================================================================
# Campaign & Channel Models
# ============================================================================

class Campaign(Base):
    """
    Marketing campaign tracking

    Aggregates performance metrics by campaign
    """
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Campaign identifiers
    utm_campaign: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    utm_source: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(255), index=True)

    # Campaign metadata
    name: Mapped[Optional[str]] = mapped_column(String(500))
    description: Mapped[Optional[Text]] = mapped_column(Text)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    budget: Mapped[Optional[float]] = mapped_column(Float)

    # Performance metrics (cached/aggregated)
    total_touchpoints: Mapped[int] = mapped_column(Integer, default=0)
    total_conversions: Mapped[int] = mapped_column(Integer, default=0)
    total_attributed_value: Mapped[float] = mapped_column(Float, default=0.0)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_aggregated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    __table_args__ = (
        Index('idx_campaign_utm', 'utm_campaign'),
        Index('idx_campaign_source_medium', 'utm_source', 'utm_medium'),
    )


# ============================================================================
# ETL & Sync Models
# ============================================================================

class ETLJob(Base):
    """
    ETL job execution tracking

    Tracks HubSpot to PostgreSQL data synchronization jobs
    """
    __tablename__ = "etl_jobs"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Job details
    job_type: Mapped[str] = mapped_column(String(100), index=True)  # e.g., 'sync_contacts', 'sync_touchpoints'
    status: Mapped[str] = mapped_column(String(50), index=True)  # pending, running, completed, failed

    # Execution stats
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)

    # Results
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_created: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)

    # Error tracking
    error_message: Mapped[Optional[Text]] = mapped_column(Text)
    error_details: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_etl_job_type', 'job_type'),
        Index('idx_etl_status', 'status'),
        Index('idx_etl_created', 'created_at'),
    )


# ============================================================================
# GDPR & Compliance Models
# ============================================================================

class ConsentRecord(Base):
    """
    GDPR consent tracking

    Tracks user consent for data processing and marketing communications
    """
    __tablename__ = "consent_records"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    contact_id: Mapped[str] = mapped_column(String(50), ForeignKey("contacts.id"), index=True)

    # Consent details
    consent_type: Mapped[str] = mapped_column(String(100), index=True)  # e.g., 'marketing_email', 'analytics'
    consent_given: Mapped[bool] = mapped_column(Boolean, index=True)
    consent_source: Mapped[Optional[str]] = mapped_column(String(255))  # Where consent was captured

    # Timing
    granted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Legal basis
    legal_basis: Mapped[Optional[str]] = mapped_column(String(100))  # e.g., 'consent', 'legitimate_interest'
    notes: Mapped[Optional[Text]] = mapped_column(Text)

    __table_args__ = (
        Index('idx_consent_contact', 'contact_id'),
        Index('idx_consent_type', 'consent_type'),
        UniqueConstraint('contact_id', 'consent_type', name='uq_contact_consent_type'),
    )


class DataRetentionPolicy(Base):
    """
    Data retention policy tracking

    Defines when data should be deleted for GDPR compliance
    """
    __tablename__ = "data_retention_policies"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Policy details
    entity_type: Mapped[str] = mapped_column(String(100), index=True)  # e.g., 'contact', 'touchpoint'
    retention_days: Mapped[int] = mapped_column(Integer)
    description: Mapped[Optional[Text]] = mapped_column(Text)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_retention_entity_type', 'entity_type'),
    )
