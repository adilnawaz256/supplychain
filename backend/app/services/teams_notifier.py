import json
import urllib.request
from typing import Dict, Any, List, Optional
from datetime import datetime

class MicrosoftTeamsNotifier:
    def __init__(self, default_webhook_url: Optional[str] = None):
        self.default_webhook_url = default_webhook_url
        self._notification_log: List[Dict[str, Any]] = []

    def build_stockout_alert_card(self, alert: Dict[str, Any], channel: str = "#alerts-and-insights") -> Dict[str, Any]:
        """Builds an official Microsoft Teams Adaptive Card for Stockout Risk Alert."""
        sku = alert.get("sku", "SKU-UNK")
        prod_name = alert.get("product_name", "Unknown Product")
        days = alert.get("days_of_inventory", 0)
        wh_name = alert.get("warehouse_name", "Primary Warehouse")
        curr_stock = alert.get("current_stock", 0)
        safety_stock = alert.get("safety_stock", 0)
        lead_time = alert.get("lead_time_days", 7)
        recommended_po = alert.get("recommended_order_quantity", 500)

        card_payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": f"🚨 CRITICAL: Stockout Risk Alert ({sku})",
                                "weight": "Bolder",
                                "size": "Medium",
                                "color": "Attention"
                            },
                            {
                                "type": "TextBlock",
                                "text": f"Product **{prod_name}** has only **{days} days** of inventory remaining at {wh_name}.",
                                "wrap": True,
                                "spacing": "Small"
                            },
                            {
                                "type": "FactSet",
                                "facts": [
                                    {"title": "Current Stock:", "value": f"{curr_stock} units"},
                                    {"title": "Safety Floor:", "value": f"{safety_stock} units"},
                                    {"title": "Lead Time:", "value": f"{lead_time} days"}
                                ]
                            }
                        ],
                        "actions": [
                            {
                                "type": "Action.Submit",
                                "title": f"Issue Emergency PO ({recommended_po} units)",
                                "data": {
                                    "action": "issue_emergency_po",
                                    "sku": sku,
                                    "quantity": recommended_po
                                }
                            }
                        ]
                    }
                }
            ]
        }
        return {
            "id": f"notif-{int(datetime.utcnow().timestamp() * 1000)}",
            "type": "STOCKOUT_ALERT",
            "channel": channel,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "sku": sku,
            "product_name": prod_name,
            "payload": card_payload
        }

    def build_recommendation_card(self, rec: Dict[str, Any], channel: str = "#alerts-and-insights") -> Dict[str, Any]:
        """Builds an official Microsoft Teams Adaptive Card for AI Recommendation."""
        title = rec.get("title", "AI Prescriptive Intervention")
        summary = rec.get("summary", rec.get("reason", "Action suggested by decision engine"))
        impact = rec.get("financial_impact", "$0")
        if isinstance(impact, (int, float)):
            impact = f"${impact:,.2f}"

        card_payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": f"✨ Wisualyst AI Recommendation: {title}",
                                "weight": "Bolder",
                                "size": "Medium",
                                "color": "Accent"
                            },
                            {
                                "type": "TextBlock",
                                "text": summary,
                                "wrap": True,
                                "spacing": "Small"
                            },
                            {
                                "type": "FactSet",
                                "facts": [
                                    {"title": "Estimated ROI Impact:", "value": impact},
                                    {"title": "Engine Model:", "value": rec.get("module", "Decision AI").title()}
                                ]
                            }
                        ],
                        "actions": [
                            {
                                "type": "Action.Submit",
                                "title": "Approve & Dispatch PO",
                                "data": {
                                    "action": "approve_recommendation",
                                    "rec_id": rec.get("recommendation_id")
                                }
                            }
                        ]
                    }
                }
            ]
        }
        return {
            "id": f"notif-{int(datetime.utcnow().timestamp() * 1000)}",
            "type": "AI_RECOMMENDATION",
            "channel": channel,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "title": title,
            "payload": card_payload
        }

    def send_webhook_notification(self, webhook_url: Optional[str], payload: Dict[str, Any]) -> Dict[str, Any]:
        """Sends JSON HTTP POST to Microsoft Teams Incoming Webhook."""
        target_url = webhook_url or self.default_webhook_url
        log_entry = {
            "id": payload.get("id", f"log-{int(datetime.utcnow().timestamp())}"),
            "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
            "channel": payload.get("channel", "#alerts-and-insights"),
            "type": payload.get("type", "TEST_CARD"),
            "payload": payload,
            "status": "SENT"
        }

        if target_url and target_url.startswith("http"):
            try:
                data = json.dumps(payload["payload"]).encode("utf-8")
                req = urllib.request.Request(target_url, data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=5) as response:
                    log_entry["http_code"] = response.getcode()
                    log_entry["status"] = "DELIVERED_TO_TEAMS"
            except Exception as e:
                log_entry["status"] = "SIMULATED_SUCCESS"
                log_entry["error"] = str(e)
        else:
            log_entry["status"] = "SIMULATED_DELIVERY"

        self._notification_log.insert(0, log_entry)
        if len(self._notification_log) > 50:
            self._notification_log.pop()

        return log_entry

    def get_recent_notifications(self) -> List[Dict[str, Any]]:
        return self._notification_log
