"""
CRM Attribution & Data Model Module

This module handles:
- Multi-touch attribution models (W-shaped, full path, etc.)
- HubSpot tracking implementation
- UTM parameter capture and storage
- Multi-session tracking
- Lifecycle stage management
- Partner/affiliate tracking
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from hubspot import HubSpot
from hubspot.crm.contacts import ApiException
from loguru import logger

from models.attribution import (
    Contact, Touchpoint, AttributionModel, LifecycleStage,
    UTMParameters, ClickID, TouchpointType, ConversionEvent
)
from config import settings


class AttributionCalculator:
    """Calculates attribution credits based on different models"""

    @staticmethod
    def first_touch(touchpoints: List[Touchpoint], total_value: float) -> Dict[str, float]:
        """First-touch attribution - 100% credit to first touchpoint"""
        if not touchpoints:
            return {}
        return {touchpoints[0].touchpoint_id: total_value}

    @staticmethod
    def last_touch(touchpoints: List[Touchpoint], total_value: float) -> Dict[str, float]:
        """Last-touch attribution - 100% credit to last touchpoint"""
        if not touchpoints:
            return {}
        return {touchpoints[-1].touchpoint_id: total_value}

    @staticmethod
    def linear(touchpoints: List[Touchpoint], total_value: float) -> Dict[str, float]:
        """Linear attribution - equal credit to all touchpoints"""
        if not touchpoints:
            return {}
        credit_per_touch = total_value / len(touchpoints)
        return {tp.touchpoint_id: credit_per_touch for tp in touchpoints}

    @staticmethod
    def w_shaped(touchpoints: List[Touchpoint], total_value: float) -> Dict[str, float]:
        """
        W-shaped attribution:
        - 30% to first touch
        - 30% to lead creation touch
        - 30% to opportunity creation touch
        - 10% distributed among remaining touches
        """
        if not touchpoints:
            return {}

        credits = {}
        num_touches = len(touchpoints)

        if num_touches == 1:
            credits[touchpoints[0].touchpoint_id] = total_value
        elif num_touches == 2:
            credits[touchpoints[0].touchpoint_id] = total_value * 0.5
            credits[touchpoints[-1].touchpoint_id] = total_value * 0.5
        else:
            # First touch gets 30%
            credits[touchpoints[0].touchpoint_id] = total_value * 0.3

            # Middle touchpoint gets 30% (simplified - should be lead creation)
            middle_idx = num_touches // 2
            credits[touchpoints[middle_idx].touchpoint_id] = total_value * 0.3

            # Last touch gets 30%
            credits[touchpoints[-1].touchpoint_id] = total_value * 0.3

            # Remaining 10% distributed among other touches
            other_touches = [tp for i, tp in enumerate(touchpoints)
                           if i not in [0, middle_idx, num_touches - 1]]
            if other_touches:
                credit_per_other = (total_value * 0.1) / len(other_touches)
                for tp in other_touches:
                    credits[tp.touchpoint_id] = credit_per_other
            else:
                # If no other touches (e.g., exactly 3 touchpoints where all are key),
                # distribute remaining 10% equally among the 3 key touchpoints
                remaining_credit = (total_value * 0.1) / 3
                credits[touchpoints[0].touchpoint_id] += remaining_credit
                credits[touchpoints[middle_idx].touchpoint_id] += remaining_credit
                credits[touchpoints[-1].touchpoint_id] += remaining_credit

        return credits

    @staticmethod
    def full_path(touchpoints: List[Touchpoint], total_value: float) -> Dict[str, float]:
        """
        Full path attribution:
        - 22.5% to first touch
        - 22.5% to lead creation
        - 22.5% to opportunity creation
        - 22.5% to deal close
        - 10% distributed among remaining touches
        """
        if not touchpoints:
            return {}

        credits = {}
        num_touches = len(touchpoints)

        if num_touches <= 4:
            # If 4 or fewer touches, distribute equally
            credit_per_touch = total_value / num_touches
            return {tp.touchpoint_id: credit_per_touch for tp in touchpoints}

        # Key milestone indices
        first_idx = 0
        lead_idx = num_touches // 4
        opp_idx = num_touches // 2
        close_idx = num_touches - 1

        # Assign credits to milestones
        credits[touchpoints[first_idx].touchpoint_id] = total_value * 0.225
        credits[touchpoints[lead_idx].touchpoint_id] = total_value * 0.225
        credits[touchpoints[opp_idx].touchpoint_id] = total_value * 0.225
        credits[touchpoints[close_idx].touchpoint_id] = total_value * 0.225

        # Distribute remaining 10%
        milestone_indices = {first_idx, lead_idx, opp_idx, close_idx}
        other_touches = [tp for i, tp in enumerate(touchpoints) if i not in milestone_indices]

        if other_touches:
            credit_per_other = (total_value * 0.1) / len(other_touches)
            for tp in other_touches:
                credits[tp.touchpoint_id] = credit_per_other

        return credits


class CRMAttributionManager:
    """Manages CRM attribution and data model integration with HubSpot"""

    def __init__(self):
        self.hubspot = HubSpot(access_token=settings.hubspot_api_key)
        self.calculator = AttributionCalculator()
        logger.info("CRM Attribution Manager initialized")

    def install_tracking_code(self) -> str:
        """
        Generate HubSpot tracking code snippet for web properties
        Returns: JavaScript tracking code
        """
        tracking_code = f"""
<!-- HubSpot Tracking Code -->
<script type="text/javascript" id="hs-script-loader" async defer src="//js.hs-scripts.com/{settings.hubspot_portal_id}.js"></script>

<!-- Custom UTM and Click ID Capture -->
<script>
(function() {{
    // Parse URL parameters
    function getUrlParameter(name) {{
        name = name.replace(/[\\[]/, '\\\\[').replace(/[\\]]/, '\\\\]');
        var regex = new RegExp('[\\\\?&]' + name + '=([^&#]*)');
        var results = regex.exec(location.search);
        return results === null ? '' : decodeURIComponent(results[1].replace(/\\+/g, ' '));
    }}

    // Store UTM parameters and click IDs
    function captureTrackingParameters() {{
        var params = {{
            utm_source: getUrlParameter('utm_source'),
            utm_medium: getUrlParameter('utm_medium'),
            utm_campaign: getUrlParameter('utm_campaign'),
            utm_term: getUrlParameter('utm_term'),
            utm_content: getUrlParameter('utm_content'),
            gclid: getUrlParameter('gclid'),
            fbclid: getUrlParameter('fbclid'),
            msclkid: getUrlParameter('msclkid'),
            li_fat_id: getUrlParameter('li_fat_id'),
            partner_id: getUrlParameter('partner_id')
        }};

        // Store in sessionStorage for session tracking
        sessionStorage.setItem('tracking_params_' + Date.now(), JSON.stringify(params));

        // Send to HubSpot via Forms API or track as event
        if (window._hsq) {{
            window._hsq.push(['setPath', window.location.pathname]);
            window._hsq.push(['trackPageView']);

            // Set custom properties
            for (var key in params) {{
                if (params[key]) {{
                    window._hsq.push(['identify', {{[key]: params[key]}}]);
                }}
            }}
        }}
    }}

    // Execute on page load
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', captureTrackingParameters);
    }} else {{
        captureTrackingParameters();
    }}
}})();
</script>
"""
        return tracking_code

    def create_custom_contact_properties(self) -> None:
        """Create custom contact properties in HubSpot for attribution tracking"""
        custom_properties = [
            {
                "name": "first_touch_utm_source",
                "label": "First Touch UTM Source",
                "type": "string",
                "fieldType": "text",
                "groupName": "contactinformation"
            },
            {
                "name": "first_touch_utm_campaign",
                "label": "First Touch UTM Campaign",
                "type": "string",
                "fieldType": "text",
                "groupName": "contactinformation"
            },
            {
                "name": "last_touch_utm_source",
                "label": "Last Touch UTM Source",
                "type": "string",
                "fieldType": "text",
                "groupName": "contactinformation"
            },
            {
                "name": "last_touch_utm_campaign",
                "label": "Last Touch UTM Campaign",
                "type": "string",
                "fieldType": "text",
                "groupName": "contactinformation"
            },
            {
                "name": "all_touchpoints_json",
                "label": "All Touchpoints (JSON)",
                "type": "string",
                "fieldType": "textarea",
                "groupName": "contactinformation"
            },
            {
                "name": "gclid",
                "label": "Google Click ID (GCLID)",
                "type": "string",
                "fieldType": "text",
                "groupName": "contactinformation"
            },
            {
                "name": "fbclid",
                "label": "Facebook Click ID",
                "type": "string",
                "fieldType": "text",
                "groupName": "contactinformation"
            },
            {
                "name": "partner_id",
                "label": "Partner/Affiliate ID",
                "type": "string",
                "fieldType": "text",
                "groupName": "contactinformation"
            },
            {
                "name": "attributed_revenue",
                "label": "Attributed Revenue",
                "type": "number",
                "fieldType": "number",
                "groupName": "contactinformation"
            }
        ]

        for prop in custom_properties:
            try:
                self.hubspot.crm.properties.core_api.create(
                    object_type="contacts",
                    property_create=prop
                )
                logger.info(f"Created custom property: {prop['name']}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info(f"Property {prop['name']} already exists")
                else:
                    logger.error(f"Error creating property {prop['name']}: {e}")

    def capture_touchpoint(self, contact_id: str, touchpoint: Touchpoint) -> None:
        """
        Capture and store a touchpoint for a contact in HubSpot
        """
        try:
            # Get existing contact
            contact = self.hubspot.crm.contacts.basic_api.get_by_id(
                contact_id=contact_id,
                properties=["all_touchpoints_json", "lifecyclestage"]
            )

            # Parse existing touchpoints
            import json
            existing_touchpoints = []
            if contact.properties.get("all_touchpoints_json"):
                existing_touchpoints = json.loads(contact.properties["all_touchpoints_json"])

            # Add new touchpoint
            touchpoint_dict = touchpoint.model_dump(mode='json')
            existing_touchpoints.append(touchpoint_dict)

            # Update contact with new touchpoint data
            properties = {
                "all_touchpoints_json": json.dumps(existing_touchpoints),
                "last_touch_utm_source": touchpoint.utm_parameters.utm_source or "",
                "last_touch_utm_campaign": touchpoint.utm_parameters.utm_campaign or "",
            }

            # If this is the first touchpoint
            if len(existing_touchpoints) == 1:
                properties["first_touch_utm_source"] = touchpoint.utm_parameters.utm_source or ""
                properties["first_touch_utm_campaign"] = touchpoint.utm_parameters.utm_campaign or ""

            # Store click IDs
            if touchpoint.click_ids.gclid:
                properties["gclid"] = touchpoint.click_ids.gclid
            if touchpoint.click_ids.fbclid:
                properties["fbclid"] = touchpoint.click_ids.fbclid
            if touchpoint.partner_id:
                properties["partner_id"] = touchpoint.partner_id

            self.hubspot.crm.contacts.basic_api.update(
                contact_id=contact_id,
                simple_public_object_input={"properties": properties}
            )

            logger.info(f"Captured touchpoint for contact {contact_id}")

        except Exception as e:
            logger.error(f"Error capturing touchpoint: {e}")
            raise

    def calculate_attribution(
        self,
        contact_id: str,
        total_value: float,
        model_type: Optional[str] = None
    ) -> AttributionModel:
        """
        Calculate attribution for a contact based on specified model
        """
        if model_type is None:
            model_type = settings.attribution_model

        # Get contact touchpoints
        try:
            contact = self.hubspot.crm.contacts.basic_api.get_by_id(
                contact_id=contact_id,
                properties=["all_touchpoints_json"]
            )

            import json
            touchpoints_data = json.loads(
                contact.properties.get("all_touchpoints_json", "[]")
            )
            touchpoints = [Touchpoint(**tp) for tp in touchpoints_data]

            # Calculate credits based on model
            if model_type == "first_touch":
                credits = self.calculator.first_touch(touchpoints, total_value)
            elif model_type == "last_touch":
                credits = self.calculator.last_touch(touchpoints, total_value)
            elif model_type == "linear":
                credits = self.calculator.linear(touchpoints, total_value)
            elif model_type == "w_shaped":
                credits = self.calculator.w_shaped(touchpoints, total_value)
            elif model_type == "full_path":
                credits = self.calculator.full_path(touchpoints, total_value)
            else:
                raise ValueError(f"Unknown attribution model: {model_type}")

            attribution = AttributionModel(
                contact_id=contact_id,
                model_type=model_type,
                touchpoint_credits=credits,
                total_value=total_value
            )

            # Update contact with attributed revenue
            self.hubspot.crm.contacts.basic_api.update(
                contact_id=contact_id,
                simple_public_object_input={
                    "properties": {"attributed_revenue": str(total_value)}
                }
            )

            logger.info(f"Calculated {model_type} attribution for contact {contact_id}")
            return attribution

        except Exception as e:
            logger.error(f"Error calculating attribution: {e}")
            raise

    def setup_lifecycle_workflows(self) -> Dict:
        """
        Returns workflow configuration for HubSpot lifecycle stage management
        This needs to be configured in HubSpot UI, but this provides the logic
        """
        workflows = {
            "lead_enrichment": {
                "trigger": "Contact is created",
                "actions": [
                    "Enrich contact data from UTM parameters",
                    "Set lifecycle stage based on form submission type",
                    "Create touchpoint record",
                    "Assign to appropriate sales team"
                ]
            },
            "mql_conversion": {
                "trigger": "Lead score reaches threshold OR specific form submitted",
                "actions": [
                    "Update lifecycle stage to MQL",
                    "Create conversion event",
                    "Notify sales team",
                    "Trigger ad platform conversion sync"
                ]
            },
            "sql_conversion": {
                "trigger": "Sales accepted lead",
                "actions": [
                    "Update lifecycle stage to SQL",
                    "Create conversion event",
                    "Calculate interim attribution",
                    "Sync to ad platforms"
                ]
            },
            "opportunity_creation": {
                "trigger": "Deal is created",
                "actions": [
                    "Update lifecycle stage to Opportunity",
                    "Create conversion event",
                    "Update attribution model",
                    "Sync to ad platforms"
                ]
            },
            "customer_conversion": {
                "trigger": "Deal is won",
                "actions": [
                    "Update lifecycle stage to Customer",
                    "Calculate final attribution",
                    "Update attributed revenue",
                    "Sync conversion to all ad platforms",
                    "Trigger customer onboarding workflow"
                ]
            }
        }

        return workflows

    def get_contact_attribution_report(self, contact_id: str) -> Dict:
        """Get comprehensive attribution report for a contact"""
        try:
            contact = self.hubspot.crm.contacts.basic_api.get_by_id(
                contact_id=contact_id,
                properties=[
                    "email",
                    "lifecyclestage",
                    "all_touchpoints_json",
                    "attributed_revenue",
                    "first_touch_utm_source",
                    "last_touch_utm_source"
                ]
            )

            import json
            touchpoints_data = json.loads(
                contact.properties.get("all_touchpoints_json", "[]")
            )

            report = {
                "contact_id": contact_id,
                "email": contact.properties.get("email"),
                "lifecycle_stage": contact.properties.get("lifecyclestage"),
                "total_touchpoints": len(touchpoints_data),
                "attributed_revenue": contact.properties.get("attributed_revenue"),
                "first_touch_source": contact.properties.get("first_touch_utm_source"),
                "last_touch_source": contact.properties.get("last_touch_utm_source"),
                "touchpoints": touchpoints_data
            }

            return report

        except Exception as e:
            logger.error(f"Error generating attribution report: {e}")
            raise
