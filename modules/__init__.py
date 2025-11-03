"""Modules package for HubSpot Integration System"""
from .crm_attribution import CRMAttributionManager, AttributionCalculator
from .ad_platform_signaling import (
    AdPlatformSignalingManager,
    GoogleAdsConnector,
    FacebookAdsConnector,
    LinkedInAdsConnector
)
from .governance_enablement import (
    UTMStandardsManager,
    TrackingURLBuilder,
    DataQualityAuditor,
    TeamEnablement,
    SystemScalability
)

__all__ = [
    'CRMAttributionManager',
    'AttributionCalculator',
    'AdPlatformSignalingManager',
    'GoogleAdsConnector',
    'FacebookAdsConnector',
    'LinkedInAdsConnector',
    'UTMStandardsManager',
    'TrackingURLBuilder',
    'DataQualityAuditor',
    'TeamEnablement',
    'SystemScalability'
]
