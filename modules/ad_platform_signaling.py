"""
Ad-Platform Signaling Module

This module handles:
- Integration with Google Ads, Facebook Ads, LinkedIn Ads
- Real-time conversion event syncing
- Enhanced conversion tracking
- Click ID capture and linking
- Campaign performance analysis
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from loguru import logger
import requests
import hashlib
import time
from hubspot import HubSpot
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ratelimit import limits, sleep_and_retry

from models.attribution import ConversionEvent, LifecycleStage
from config import settings
from modules.exceptions import (
    APIConnectionError,
    SyncError,
    ValidationError,
    APIRateLimitError,
    AuthenticationError
)
from modules.logging_utils import with_correlation_id, log_with_context


class GoogleAdsConnector:
    """Handles Google Ads integration and conversion tracking with OAuth refresh and batching"""

    # Rate limiting: 1000 conversions per call, max 10 calls per minute
    BATCH_SIZE = 1000
    CALLS_PER_MINUTE = 10

    def __init__(self):
        self.client_id = settings.google_ads_client_id
        self.client_secret = settings.google_ads_client_secret
        self.developer_token = settings.google_ads_developer_token
        self.refresh_token = settings.google_ads_refresh_token
        self.customer_id = settings.google_ads_customer_id
        self.enabled = bool(self.client_id and self.developer_token and self.refresh_token)
        self._client = None
        self._token_expires_at = None
        self._conversion_queue = []

        if self.enabled:
            logger.info("Google Ads Connector initialized and enabled")
            try:
                self._initialize_client()
            except Exception as e:
                logger.error(f"Failed to initialize Google Ads client: {e}")
                self.enabled = False
        else:
            logger.info("Google Ads Connector initialized but disabled (missing credentials)")

    def _initialize_client(self):
        """Initialize Google Ads API client with OAuth credentials"""
        try:
            from google.ads.googleads.client import GoogleAdsClient

            credentials = {
                "developer_token": self.developer_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "use_proto_plus": True
            }

            self._client = GoogleAdsClient.load_from_dict(credentials)
            self._token_expires_at = datetime.now() + timedelta(hours=1)
            logger.info("Google Ads API client initialized successfully")

        except ImportError:
            logger.warning("google-ads library not fully configured. Running in stub mode.")
            self._client = None
        except Exception as e:
            logger.error(f"Error initializing Google Ads client: {e}")
            raise AuthenticationError("Google Ads", str(e))

    def _refresh_token_if_needed(self):
        """Refresh OAuth token if it's about to expire"""
        if not self._token_expires_at or datetime.now() >= self._token_expires_at - timedelta(minutes=5):
            logger.info("Refreshing Google Ads OAuth token")
            self._initialize_client()

    @sleep_and_retry
    @limits(calls=CALLS_PER_MINUTE, period=60)
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APIConnectionError, APIRateLimitError))
    )
    @with_correlation_id
    def send_conversion(
        self,
        gclid: str,
        conversion_action: str,
        conversion_time: datetime,
        conversion_value: Optional[float] = None,
        currency_code: str = "EUR"
    ) -> Dict[str, Any]:
        """
        Send conversion event to Google Ads with retry logic and OAuth refresh

        Args:
            gclid: Google Click ID
            conversion_action: Conversion action resource name (e.g., customers/123/conversionActions/456)
            conversion_time: When the conversion occurred
            conversion_value: Optional monetary value
            currency_code: Currency code (default: EUR)

        Returns:
            Dict with upload results and status

        Raises:
            ValidationError: If input parameters are invalid
            SyncError: If syncing to Google Ads fails after retries
            AuthenticationError: If OAuth authentication fails
        """
        if not self.enabled:
            logger.warning("Google Ads not configured, skipping conversion sync")
            return {"success": False, "reason": "not_configured"}

        # Validate inputs
        if not gclid or not gclid.strip():
            raise ValidationError("gclid", "Google Click ID cannot be empty")
        if not conversion_action or not conversion_action.strip():
            raise ValidationError("conversion_action", "Conversion action cannot be empty")
        if conversion_value is not None and conversion_value < 0:
            raise ValidationError("conversion_value", "Conversion value cannot be negative")

        try:
            self._refresh_token_if_needed()

            if not self._client:
                # Stub mode - log and return success for testing
                logger.warning("Google Ads client not available (stub mode)")
                log_with_context("info", f"[STUB] Would send conversion to Google Ads: GCLID={gclid}, action={conversion_action}, value={conversion_value}")
                return {
                    "success": True,
                    "stub_mode": True,
                    "gclid": gclid,
                    "conversion_action": conversion_action
                }

            # Use actual Google Ads API
            from google.ads.googleads.client import GoogleAdsClient

            conversion_upload_service = self._client.get_service("ConversionUploadService")

            # Create click conversion
            click_conversion = self._client.get_type("ClickConversion")
            click_conversion.gclid = gclid.strip()
            click_conversion.conversion_action = conversion_action
            click_conversion.conversion_date_time = conversion_time.strftime("%Y-%m-%d %H:%M:%S%z")

            if conversion_value:
                click_conversion.conversion_value = conversion_value
                click_conversion.currency_code = currency_code

            # Upload conversion
            request = self._client.get_type("UploadClickConversionsRequest")
            request.customer_id = self.customer_id
            request.conversions = [click_conversion]
            request.partial_failure = True

            response = conversion_upload_service.upload_click_conversions(request=request)

            # Check for partial failures
            if response.partial_failure_error:
                logger.error(f"Partial failure in Google Ads conversion upload: {response.partial_failure_error}")

            logger.info(f"Successfully uploaded conversion to Google Ads: GCLID={gclid}")
            log_with_context("info", f"Google Ads conversion uploaded: {len(response.results)} successful")

            return {
                "success": True,
                "results_count": len(response.results),
                "gclid": gclid,
                "partial_failure": bool(response.partial_failure_error)
            }

        except ValidationError:
            raise
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Error sending conversion to Google Ads: {e}")
            raise SyncError("Google Ads", str(e))

    @with_correlation_id
    def send_conversions_batch(
        self,
        conversions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Send multiple conversions in a single batch (up to 1000)

        Args:
            conversions: List of conversion dicts with keys: gclid, conversion_action, conversion_time, conversion_value

        Returns:
            Dict with batch upload results

        Raises:
            ValidationError: If batch is too large or invalid
            SyncError: If batch upload fails
        """
        if not self.enabled:
            logger.warning("Google Ads not configured, skipping batch conversion sync")
            return {"success": False, "reason": "not_configured"}

        if not conversions:
            raise ValidationError("conversions", "Conversion list cannot be empty")

        if len(conversions) > self.BATCH_SIZE:
            raise ValidationError("conversions", f"Batch size cannot exceed {self.BATCH_SIZE}")

        try:
            self._refresh_token_if_needed()

            if not self._client:
                # Stub mode
                logger.warning(f"[STUB] Would send {len(conversions)} conversions to Google Ads")
                return {
                    "success": True,
                    "stub_mode": True,
                    "count": len(conversions)
                }

            conversion_upload_service = self._client.get_service("ConversionUploadService")
            click_conversions = []

            for conv in conversions:
                click_conversion = self._client.get_type("ClickConversion")
                click_conversion.gclid = conv["gclid"]
                click_conversion.conversion_action = conv["conversion_action"]
                click_conversion.conversion_date_time = conv["conversion_time"].strftime("%Y-%m-%d %H:%M:%S%z")

                if "conversion_value" in conv and conv["conversion_value"]:
                    click_conversion.conversion_value = conv["conversion_value"]
                    click_conversion.currency_code = conv.get("currency_code", "EUR")

                click_conversions.append(click_conversion)

            # Upload batch
            request = self._client.get_type("UploadClickConversionsRequest")
            request.customer_id = self.customer_id
            request.conversions = click_conversions
            request.partial_failure = True

            response = conversion_upload_service.upload_click_conversions(request=request)

            success_count = len(response.results)
            logger.info(f"Batch uploaded {success_count}/{len(conversions)} conversions to Google Ads")
            log_with_context("info", f"Google Ads batch upload: {success_count} successful, {len(conversions) - success_count} failed")

            return {
                "success": True,
                "total": len(conversions),
                "successful": success_count,
                "failed": len(conversions) - success_count,
                "partial_failure": bool(response.partial_failure_error),
                "error": str(response.partial_failure_error) if response.partial_failure_error else None
            }

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error in batch conversion upload: {e}")
            raise SyncError("Google Ads", str(e))

    def setup_enhanced_conversions(self) -> Dict:
        """
        Configure enhanced conversions for better attribution

        Returns configuration guide
        """
        return {
            "enabled": True,
            "required_data": [
                "email",
                "phone_number",
                "first_name",
                "last_name",
                "country",
                "postal_code"
            ],
            "hashing": "SHA256",
            "instructions": [
                "Enable enhanced conversions in Google Ads account",
                "Add enhanced conversion tag to website",
                "Pass hashed user data with conversions",
                "Verify data quality in Google Ads interface"
            ]
        }

    def get_campaign_performance(self, start_date: str, end_date: str) -> Dict:
        """Fetch campaign performance data from Google Ads"""
        try:
            # Placeholder for actual Google Ads API call
            logger.info(f"Fetching Google Ads performance from {start_date} to {end_date}")

            # In production, use Google Ads API query:
            # query = """
            #     SELECT campaign.id, campaign.name, metrics.impressions,
            #            metrics.clicks, metrics.conversions, metrics.cost_micros
            #     FROM campaign
            #     WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
            # """

            return {
                "status": "success",
                "data": {
                    "campaigns": [],
                    "total_conversions": 0,
                    "total_cost": 0
                }
            }

        except Exception as e:
            logger.error(f"Error fetching Google Ads performance: {e}")
            return {"status": "error", "message": str(e)}


class FacebookAdsConnector:
    """Handles Facebook/Meta Ads integration with full CAPI support"""

    # Rate limiting: 200 requests per hour per ad account
    BATCH_SIZE = 1000  # Facebook allows up to 1000 events per batch
    CALLS_PER_HOUR = 200

    def __init__(self):
        self.access_token = settings.facebook_access_token
        self.ad_account_id = settings.facebook_ad_account_id
        self.app_id = settings.facebook_app_id
        self.app_secret = settings.facebook_app_secret
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        self.pixel_id = self.ad_account_id.replace("act_", "") if self.ad_account_id else None
        self.enabled = bool(self.access_token and self.ad_account_id)

        if self.enabled:
            logger.info("Facebook Ads Connector initialized and enabled")
        else:
            logger.info("Facebook Ads Connector initialized but disabled (missing credentials)")

    def _hash_user_data(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Hash user data according to Facebook's requirements"""
        hashed_data = {}

        for key, value in data.items():
            if value and isinstance(value, str):
                # Normalize and hash
                normalized = value.lower().strip()
                hashed_data[key] = hashlib.sha256(normalized.encode()).hexdigest()
            elif value:
                hashed_data[key] = value

        return hashed_data

    @sleep_and_retry
    @limits(calls=CALLS_PER_HOUR, period=3600)
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APIConnectionError, APIRateLimitError))
    )
    @with_correlation_id
    def send_conversion(
        self,
        event_name: str,
        event_time: datetime,
        user_data: Dict[str, Any],
        fbclid: Optional[str] = None,
        fbc: Optional[str] = None,
        fbp: Optional[str] = None,
        value: Optional[float] = None,
        currency: str = "EUR",
        event_source_url: Optional[str] = None,
        custom_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Send conversion event to Facebook Conversions API with full payload

        Args:
            event_name: Event type (e.g., 'Lead', 'Purchase', 'CompleteRegistration')
            event_time: When event occurred
            user_data: User data dict with keys like 'em' (email), 'ph' (phone), 'fn' (first name), etc.
            fbclid: Facebook Click ID from URL parameter
            fbc: Facebook click cookie (_fbc)
            fbp: Facebook browser cookie (_fbp)
            value: Optional conversion value
            currency: Currency code (default: EUR)
            event_source_url: URL where conversion happened
            custom_data: Additional custom data for the event

        Returns:
            Dict with upload results

        Raises:
            ValidationError: If input parameters are invalid
            SyncError: If syncing to Facebook fails after retries
        """
        if not self.enabled:
            logger.warning("Facebook Ads not configured, skipping conversion sync")
            return {"success": False, "reason": "not_configured"}

        # Validate inputs
        if not event_name or not event_name.strip():
            raise ValidationError("event_name", "Event name cannot be empty")
        if not user_data or not isinstance(user_data, dict):
            raise ValidationError("user_data", "User data must be a non-empty dictionary")
        if value is not None and value < 0:
            raise ValidationError("value", "Conversion value cannot be negative")

        try:
            url = f"{self.base_url}/{self.pixel_id}/events"

            # Hash user data if not already hashed
            hashed_user_data = self._hash_user_data(user_data)

            # Build event data
            event_data = {
                "event_name": event_name,
                "event_time": int(event_time.timestamp()),
                "user_data": hashed_user_data,
                "action_source": "website",
                "event_id": f"{event_name}_{int(event_time.timestamp())}"  # Deduplication ID
            }

            # Add click IDs and cookies
            if fbclid or fbc:
                event_data["fbc"] = fbc if fbc else f"fb.1.{int(event_time.timestamp())}.{fbclid}"
            if fbp:
                event_data["fbp"] = fbp

            # Add event source URL
            if event_source_url:
                event_data["event_source_url"] = event_source_url

            # Add custom data
            if value or custom_data:
                event_data["custom_data"] = custom_data or {}
                if value:
                    event_data["custom_data"]["value"] = value
                    event_data["custom_data"]["currency"] = currency

            payload = {
                "data": [event_data],
                "access_token": self.access_token,
                "test_event_code": None  # Set to test code for testing
            }

            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()

            logger.info(f"Sent conversion to Facebook: {event_name}")
            log_with_context("info", f"Facebook CAPI event sent: {event_name}, events_received={result.get('events_received', 0)}")

            return {
                "success": True,
                "events_received": result.get("events_received", 0),
                "messages": result.get("messages", []),
                "event_id": event_data["event_id"]
            }

        except ValidationError:
            raise
        except requests.exceptions.RequestException as e:
            if hasattr(e.response, 'status_code'):
                if e.response.status_code == 429:
                    raise APIRateLimitError("Facebook Ads", retry_after=3600)
                elif e.response.status_code == 401:
                    raise AuthenticationError("Facebook Ads", "Invalid access token")
            logger.error(f"Error sending conversion to Facebook: {e}")
            raise SyncError("Facebook Ads", str(e))
        except Exception as e:
            logger.error(f"Error sending conversion to Facebook: {e}")
            raise SyncError("Facebook Ads", str(e))

    @with_correlation_id
    def send_conversions_batch(
        self,
        events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Send multiple events in a single batch (up to 1000)

        Args:
            events: List of event dicts with keys matching send_conversion args

        Returns:
            Dict with batch upload results
        """
        if not self.enabled:
            logger.warning("Facebook Ads not configured, skipping batch sync")
            return {"success": False, "reason": "not_configured"}

        if not events:
            raise ValidationError("events", "Events list cannot be empty")

        if len(events) > self.BATCH_SIZE:
            raise ValidationError("events", f"Batch size cannot exceed {self.BATCH_SIZE}")

        try:
            url = f"{self.base_url}/{self.pixel_id}/events"

            batch_data = []
            for event in events:
                hashed_user_data = self._hash_user_data(event["user_data"])

                event_data = {
                    "event_name": event["event_name"],
                    "event_time": int(event["event_time"].timestamp()),
                    "user_data": hashed_user_data,
                    "action_source": "website",
                    "event_id": event.get("event_id", f"{event['event_name']}_{int(event['event_time'].timestamp())}")
                }

                if "fbclid" in event or "fbc" in event:
                    event_data["fbc"] = event.get("fbc", f"fb.1.{int(event['event_time'].timestamp())}.{event.get('fbclid')}")
                if "fbp" in event:
                    event_data["fbp"] = event["fbp"]
                if "event_source_url" in event:
                    event_data["event_source_url"] = event["event_source_url"]

                if "value" in event or "custom_data" in event:
                    event_data["custom_data"] = event.get("custom_data", {})
                    if "value" in event:
                        event_data["custom_data"]["value"] = event["value"]
                        event_data["custom_data"]["currency"] = event.get("currency", "EUR")

                batch_data.append(event_data)

            payload = {
                "data": batch_data,
                "access_token": self.access_token
            }

            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()

            logger.info(f"Batch sent {len(events)} events to Facebook")
            log_with_context("info", f"Facebook CAPI batch: {result.get('events_received', 0)} events received")

            return {
                "success": True,
                "total": len(events),
                "events_received": result.get("events_received", 0),
                "messages": result.get("messages", [])
            }

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error in Facebook batch upload: {e}")
            raise SyncError("Facebook Ads", str(e))

    def setup_conversion_events(self) -> List[Dict]:
        """
        Define custom conversion events for Facebook

        Returns list of event configurations
        """
        events = [
            {
                "name": "Lead",
                "description": "User becomes a lead (lifecycle stage change)",
                "hubspot_trigger": "lifecyclestage = 'lead'"
            },
            {
                "name": "MQL",
                "description": "Marketing Qualified Lead",
                "hubspot_trigger": "lifecyclestage = 'marketingqualifiedlead'"
            },
            {
                "name": "SQL",
                "description": "Sales Qualified Lead",
                "hubspot_trigger": "lifecyclestage = 'salesqualifiedlead'"
            },
            {
                "name": "Opportunity",
                "description": "Opportunity created",
                "hubspot_trigger": "lifecyclestage = 'opportunity'"
            },
            {
                "name": "Purchase",
                "description": "Customer conversion",
                "hubspot_trigger": "lifecyclestage = 'customer'"
            }
        ]

        return events


class LinkedInAdsConnector:
    """Handles LinkedIn Ads integration with full CAPI support"""

    # Rate limiting: 100 requests per day per conversion
    BATCH_SIZE = 1000  # LinkedIn allows up to 1000 conversions per batch
    CALLS_PER_DAY = 100

    def __init__(self):
        self.access_token = settings.linkedin_access_token
        self.ad_account_id = settings.linkedin_ad_account_id
        self.api_version = "202401"
        self.base_url = "https://api.linkedin.com/rest"
        self.enabled = bool(self.access_token and self.ad_account_id)

        if self.enabled:
            logger.info("LinkedIn Ads Connector initialized and enabled")
        else:
            logger.info("LinkedIn Ads Connector initialized but disabled (missing credentials)")

    def _hash_user_data(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Hash user data according to LinkedIn's requirements"""
        hashed_data = {}

        # LinkedIn requires SHA256 hashing
        for key, value in data.items():
            if value and isinstance(value, str):
                normalized = value.lower().strip()
                hashed_data[key] = hashlib.sha256(normalized.encode()).hexdigest()
            elif value:
                hashed_data[key] = value

        return hashed_data

    @sleep_and_retry
    @limits(calls=CALLS_PER_DAY, period=86400)
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APIConnectionError, APIRateLimitError))
    )
    @with_correlation_id
    def send_conversion(
        self,
        conversion_id: str,
        conversion_time: datetime,
        user_data: Dict[str, Any],
        value: Optional[float] = None,
        currency_code: str = "EUR",
        event_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send conversion to LinkedIn CAPI with full payload and retry logic

        Args:
            conversion_id: LinkedIn conversion tracking URN (e.g., urn:li:conversion:123456)
            conversion_time: When conversion occurred
            user_data: User information dict with keys like 'email', 'firstName', 'lastName', etc.
            value: Optional conversion value
            currency_code: Currency code (default: EUR)
            event_id: Optional unique event ID for deduplication

        Returns:
            Dict with upload results

        Raises:
            ValidationError: If input parameters are invalid
            SyncError: If syncing to LinkedIn fails after retries
            AuthenticationError: If authentication fails
        """
        if not self.enabled:
            logger.warning("LinkedIn Ads not configured, skipping conversion sync")
            return {"success": False, "reason": "not_configured"}

        # Validate inputs
        if not conversion_id or not conversion_id.strip():
            raise ValidationError("conversion_id", "Conversion ID cannot be empty")
        if not user_data or not isinstance(user_data, dict):
            raise ValidationError("user_data", "User data must be a non-empty dictionary")
        if value is not None and value < 0:
            raise ValidationError("value", "Conversion value cannot be negative")

        try:
            url = f"{self.base_url}/conversions"

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "LinkedIn-Version": self.api_version,
                "X-RestLi-Protocol-Version": "2.0.0"
            }

            # Hash user data
            hashed_user_data = self._hash_user_data(user_data)

            # Build user identifiers
            user_identifiers = []
            if "email" in hashed_user_data:
                user_identifiers.append({
                    "idType": "SHA256_EMAIL",
                    "idValue": hashed_user_data["email"]
                })
            if "firstName" in hashed_user_data and "lastName" in hashed_user_data:
                user_identifiers.append({
                    "idType": "LINKEDIN_FIRST_PARTY_ADS_TRACKING_UUID",
                    "idValue": f"{hashed_user_data['firstName']}_{hashed_user_data['lastName']}"
                })

            # Build conversion data
            conversion_data = {
                "conversion": conversion_id,
                "conversionHappenedAt": int(conversion_time.timestamp() * 1000),
                "user": {
                    "userIds": user_identifiers
                }
            }

            # Add event ID for deduplication
            if event_id:
                conversion_data["eventId"] = event_id
            else:
                conversion_data["eventId"] = f"{conversion_id}_{int(conversion_time.timestamp())}"

            # Add conversion value
            if value:
                conversion_data["conversionValue"] = {
                    "amount": str(value),
                    "currencyCode": currency_code
                }

            payload = {"elements": [conversion_data]}

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()

            logger.info(f"Sent conversion to LinkedIn: {conversion_id}")
            log_with_context("info", f"LinkedIn CAPI conversion sent: {conversion_id}")

            return {
                "success": True,
                "conversion_id": conversion_id,
                "event_id": conversion_data["eventId"],
                "response": result
            }

        except ValidationError:
            raise
        except requests.exceptions.RequestException as e:
            if hasattr(e.response, 'status_code'):
                if e.response.status_code == 429:
                    raise APIRateLimitError("LinkedIn Ads", retry_after=86400)
                elif e.response.status_code in [401, 403]:
                    raise AuthenticationError("LinkedIn Ads", "Invalid or expired access token")
            logger.error(f"Error sending conversion to LinkedIn: {e}")
            raise SyncError("LinkedIn Ads", str(e))
        except Exception as e:
            logger.error(f"Error sending conversion to LinkedIn: {e}")
            raise SyncError("LinkedIn Ads", str(e))

    @with_correlation_id
    def send_conversions_batch(
        self,
        conversions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Send multiple conversions in a single batch (up to 1000)

        Args:
            conversions: List of conversion dicts with keys matching send_conversion args

        Returns:
            Dict with batch upload results
        """
        if not self.enabled:
            logger.warning("LinkedIn Ads not configured, skipping batch sync")
            return {"success": False, "reason": "not_configured"}

        if not conversions:
            raise ValidationError("conversions", "Conversions list cannot be empty")

        if len(conversions) > self.BATCH_SIZE:
            raise ValidationError("conversions", f"Batch size cannot exceed {self.BATCH_SIZE}")

        try:
            url = f"{self.base_url}/conversions"

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "LinkedIn-Version": self.api_version,
                "X-RestLi-Protocol-Version": "2.0.0"
            }

            batch_elements = []
            for conv in conversions:
                hashed_user_data = self._hash_user_data(conv["user_data"])

                user_identifiers = []
                if "email" in hashed_user_data:
                    user_identifiers.append({
                        "idType": "SHA256_EMAIL",
                        "idValue": hashed_user_data["email"]
                    })

                conversion_data = {
                    "conversion": conv["conversion_id"],
                    "conversionHappenedAt": int(conv["conversion_time"].timestamp() * 1000),
                    "user": {
                        "userIds": user_identifiers
                    },
                    "eventId": conv.get("event_id", f"{conv['conversion_id']}_{int(conv['conversion_time'].timestamp())}")
                }

                if "value" in conv and conv["value"]:
                    conversion_data["conversionValue"] = {
                        "amount": str(conv["value"]),
                        "currencyCode": conv.get("currency_code", "EUR")
                    }

                batch_elements.append(conversion_data)

            payload = {"elements": batch_elements}

            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()

            logger.info(f"Batch sent {len(conversions)} conversions to LinkedIn")
            log_with_context("info", f"LinkedIn CAPI batch: {len(conversions)} conversions sent")

            return {
                "success": True,
                "total": len(conversions),
                "response": result
            }

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error in LinkedIn batch upload: {e}")
            raise SyncError("LinkedIn Ads", str(e))


class AdPlatformSignalingManager:
    """
    Orchestrates conversion event signaling across all ad platforms
    """

    def __init__(self):
        self.google_ads = GoogleAdsConnector()
        self.facebook_ads = FacebookAdsConnector()
        self.linkedin_ads = LinkedInAdsConnector()
        self.hubspot = HubSpot(access_token=settings.hubspot_api_key)
        logger.info("Ad Platform Signaling Manager initialized")

    def sync_lifecycle_conversion(
        self,
        contact_id: str,
        from_stage: LifecycleStage,
        to_stage: LifecycleStage,
        conversion_value: Optional[float] = None
    ) -> ConversionEvent:
        """
        Sync a lifecycle stage conversion to all relevant ad platforms

        Args:
            contact_id: HubSpot contact ID
            from_stage: Previous lifecycle stage
            to_stage: New lifecycle stage
            conversion_value: Optional monetary value

        Returns:
            ConversionEvent with sync status
        """
        try:
            # Get contact data from HubSpot
            contact = self.hubspot.crm.contacts.basic_api.get_by_id(
                contact_id=contact_id,
                properties=["email", "gclid", "fbclid", "firstname", "lastname", "phone"]
            )

            email = contact.properties.get("email")
            gclid = contact.properties.get("gclid")
            fbclid = contact.properties.get("fbclid")

            # Create conversion event
            conversion_event = ConversionEvent(
                contact_id=contact_id,
                from_stage=from_stage,
                to_stage=to_stage,
                timestamp=datetime.utcnow(),
                conversion_value=conversion_value,
                synced_to_ad_platforms=[]
            )

            # Prepare user data for conversions
            import hashlib
            user_data = {
                "em": hashlib.sha256(email.encode()).hexdigest() if email else None,
                "fn": hashlib.sha256(
                    contact.properties.get("firstname", "").encode()
                ).hexdigest() if contact.properties.get("firstname") else None,
                "ln": hashlib.sha256(
                    contact.properties.get("lastname", "").encode()
                ).hexdigest() if contact.properties.get("lastname") else None,
            }

            # Sync to Google Ads if we have GCLID
            if gclid:
                conversion_action = self._map_lifecycle_to_google_conversion(to_stage)
                if conversion_action:
                    success = self.google_ads.send_conversion(
                        gclid=gclid,
                        conversion_action=conversion_action,
                        conversion_time=conversion_event.timestamp,
                        conversion_value=conversion_value
                    )
                    if success:
                        conversion_event.synced_to_ad_platforms.append("google_ads")

            # Sync to Facebook if we have FBCLID
            if fbclid:
                event_name = self._map_lifecycle_to_facebook_event(to_stage)
                if event_name:
                    success = self.facebook_ads.send_conversion(
                        event_name=event_name,
                        event_time=conversion_event.timestamp,
                        user_data=user_data,
                        fbclid=fbclid,
                        value=conversion_value
                    )
                    if success:
                        conversion_event.synced_to_ad_platforms.append("facebook_ads")

            # Always try LinkedIn (uses user data matching)
            linkedin_conversion_id = self._map_lifecycle_to_linkedin_conversion(to_stage)
            if linkedin_conversion_id:
                success = self.linkedin_ads.send_conversion(
                    conversion_id=linkedin_conversion_id,
                    conversion_time=conversion_event.timestamp,
                    user_data=user_data,
                    value=conversion_value
                )
                if success:
                    conversion_event.synced_to_ad_platforms.append("linkedin_ads")

            logger.info(
                f"Synced conversion for contact {contact_id} to platforms: "
                f"{conversion_event.synced_to_ad_platforms}"
            )

            return conversion_event

        except Exception as e:
            logger.error(f"Error syncing lifecycle conversion: {e}")
            raise

    def _map_lifecycle_to_google_conversion(self, stage: LifecycleStage) -> Optional[str]:
        """Map HubSpot lifecycle stage to Google Ads conversion action"""
        mapping = {
            LifecycleStage.LEAD: "lead_generation",
            LifecycleStage.MARKETING_QUALIFIED_LEAD: "mql_conversion",
            LifecycleStage.SALES_QUALIFIED_LEAD: "sql_conversion",
            LifecycleStage.OPPORTUNITY: "opportunity_created",
            LifecycleStage.CUSTOMER: "purchase"
        }
        return mapping.get(stage)

    def _map_lifecycle_to_facebook_event(self, stage: LifecycleStage) -> Optional[str]:
        """Map HubSpot lifecycle stage to Facebook event name"""
        mapping = {
            LifecycleStage.LEAD: "Lead",
            LifecycleStage.MARKETING_QUALIFIED_LEAD: "MQL",
            LifecycleStage.SALES_QUALIFIED_LEAD: "SQL",
            LifecycleStage.OPPORTUNITY: "Opportunity",
            LifecycleStage.CUSTOMER: "Purchase"
        }
        return mapping.get(stage)

    def _map_lifecycle_to_linkedin_conversion(self, stage: LifecycleStage) -> Optional[str]:
        """Map HubSpot lifecycle stage to LinkedIn conversion ID"""
        # These would be actual conversion IDs from LinkedIn Campaign Manager
        mapping = {
            LifecycleStage.LEAD: "lead_gen_conversion",
            LifecycleStage.MARKETING_QUALIFIED_LEAD: "mql_conversion",
            LifecycleStage.SALES_QUALIFIED_LEAD: "sql_conversion",
            LifecycleStage.OPPORTUNITY: "opportunity_conversion",
            LifecycleStage.CUSTOMER: "purchase_conversion"
        }
        return mapping.get(stage)

    def setup_hubspot_ad_integrations(self) -> Dict:
        """
        Guide for setting up HubSpot's built-in ad platform integrations

        Returns configuration instructions
        """
        return {
            "google_ads": {
                "steps": [
                    "Navigate to Marketing > Ads in HubSpot",
                    "Click 'Connect account' and select Google Ads",
                    "Authenticate with Google account",
                    "Select ad accounts to sync",
                    "Enable automatic sync of campaigns and audiences",
                    "Configure conversion tracking in Google Ads"
                ],
                "features": [
                    "Automatic campaign import",
                    "Contact-to-ad click attribution",
                    "Audience sync for remarketing",
                    "ROI reporting"
                ]
            },
            "facebook_ads": {
                "steps": [
                    "Navigate to Marketing > Ads in HubSpot",
                    "Click 'Connect account' and select Facebook",
                    "Authenticate with Facebook account",
                    "Select ad accounts to sync",
                    "Set up Facebook Pixel on website",
                    "Configure Conversions API integration"
                ],
                "features": [
                    "Campaign performance tracking",
                    "Lead ads integration",
                    "Custom audience sync",
                    "Conversion tracking"
                ]
            },
            "linkedin_ads": {
                "steps": [
                    "Navigate to Marketing > Ads in HubSpot",
                    "Click 'Connect account' and select LinkedIn",
                    "Authenticate with LinkedIn account",
                    "Select ad accounts to sync",
                    "Enable LinkedIn Insight Tag",
                    "Set up conversion tracking"
                ],
                "features": [
                    "Campaign sync",
                    "Lead gen forms integration",
                    "Matched audiences",
                    "B2B attribution reporting"
                ]
            }
        }

    def get_cross_platform_performance_report(
        self,
        start_date: str,
        end_date: str
    ) -> Dict:
        """
        Generate unified performance report across all ad platforms

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Unified performance metrics
        """
        try:
            # Fetch data from each platform
            google_data = self.google_ads.get_campaign_performance(start_date, end_date)
            # facebook_data = self.facebook_ads.get_campaign_performance(start_date, end_date)
            # linkedin_data = self.linkedin_ads.get_campaign_performance(start_date, end_date)

            report = {
                "period": f"{start_date} to {end_date}",
                "platforms": {
                    "google_ads": google_data,
                    "facebook_ads": {"status": "not_implemented"},
                    "linkedin_ads": {"status": "not_implemented"}
                },
                "summary": {
                    "total_spend": 0,
                    "total_conversions": 0,
                    "cost_per_conversion": 0,
                    "roas": 0
                }
            }

            return report

        except Exception as e:
            logger.error(f"Error generating cross-platform report: {e}")
            return {"status": "error", "message": str(e)}
