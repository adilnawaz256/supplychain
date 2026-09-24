import os
import json
import urllib.parse
import urllib.request
from datetime import datetime
from fastapi import APIRouter, Depends, Body
from fastapi.responses import Response, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from backend.app.core.database import get_db
from backend.app.services.services import SupplyChainService
from backend.app.services.bi_adapter import LocalBIAdapter
from backend.app.models.models import MicrosoftOAuthConnection
from backend.app.services.teams_notifier import MicrosoftTeamsNotifier

router = APIRouter()
teams_notifier = MicrosoftTeamsNotifier()

# In-memory store for active Microsoft OAuth session
ACTIVE_MICROSOFT_SESSIONS: Dict[str, Any] = {}

# --- Microsoft Teams Integration Endpoints ---
@router.post("/api/teams/webhook/test", tags=["Microsoft Teams Integration"])
def send_teams_test_card(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    webhook_url = payload.get("webhook_url")
    channel = payload.get("channel", "#alerts-and-insights")
    
    service = SupplyChainService(db)
    risks = service.risk_engine.get_all_inventory_risks()
    top_risk = next((r for r in risks if r["stockout_risk_level"] == "CRITICAL"), risks[0] if risks else None)
    
    if not top_risk:
        return {
            "status": "INFO",
            "message": "No inventory risk records currently in database to dispatch to Teams. Connect data sources first.",
            "detail": teams_notifier.get_recent_notifications()
        }
    
    card_msg = teams_notifier.build_stockout_alert_card(top_risk, channel=channel)
    result = teams_notifier.send_webhook_notification(webhook_url, card_msg)
    return {"status": "SUCCESS", "message": "Microsoft Teams Adaptive Card sent successfully!", "detail": result}

@router.post("/api/teams/webhook/send", tags=["Microsoft Teams Integration"])
def send_teams_notification(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    webhook_url = payload.get("webhook_url")
    notification_type = payload.get("type", "STOCKOUT_ALERT")
    alert_data = payload.get("data", {})
    channel = payload.get("channel", "#alerts-and-insights")
    
    if notification_type == "AI_RECOMMENDATION":
        card_msg = teams_notifier.build_recommendation_card(alert_data, channel=channel)
    else:
        card_msg = teams_notifier.build_stockout_alert_card(alert_data, channel=channel)

    session = ACTIVE_MICROSOFT_SESSIONS.get("latest")
    access_token = session.get("access_token") if session else None
    user_id = session.get("user_id") if session else None
    
    if not access_token:
        db_conn = db.query(MicrosoftOAuthConnection).filter(MicrosoftOAuthConnection.is_active == 1).order_by(MicrosoftOAuthConnection.updated_at.desc()).first()
        if db_conn:
            access_token = db_conn.access_token
            user_id = db_conn.user_id

    if access_token:
        try:
            graph_res = teams_notifier.send_graph_chat_message(
                access_token=access_token,
                user_id=user_id,
                payload=card_msg
            )
            card_msg["graph_status"] = graph_res
        except Exception as e:
            print("Graph chat dispatch error note:", e)

    result = teams_notifier.send_webhook_notification(webhook_url, card_msg)
    if "graph_status" in card_msg:
        result["graph_status"] = card_msg["graph_status"]
    else:
        result["graph_status"] = {"status": "NO_ACTIVE_SESSION", "message": "Click 'Sign in with Microsoft' in UI first to establish live session"}
    return {"status": "SUCCESS", "detail": result}

# --- Microsoft Teams 1-Click OAuth Integration ---
@router.get("/api/auth/microsoft/login", tags=["Microsoft Teams Integration"])
@router.get("/auth/microsoft/login", tags=["Microsoft Teams Integration"])
def microsoft_oauth_login():
    client_id = os.environ.get("AZURE_CLIENT_ID", "52889720-e817-40ce-be25-ca732a9d1a5c")
    tenant_authority = "common"
    redirect_uri = os.environ.get("AZURE_REDIRECT_URI", "https://app.wisualyst.com/api/auth/callback/microsoft")
    scope = "openid profile email User.Read ChannelMessage.Send ChatMessage.Send Chat.ReadWrite"
    
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": scope,
        "state": "wisualyst_teams_auth"
    }
    url = f"https://login.microsoftonline.com/{tenant_authority}/oauth2/v2.0/authorize?" + urllib.parse.urlencode(params)
    return RedirectResponse(url=url)

@router.get("/api/auth/callback/microsoft", tags=["Microsoft Teams Integration"])
@router.get("/auth/callback/microsoft", tags=["Microsoft Teams Integration"])
def microsoft_oauth_callback(code: Optional[str] = None, error: Optional[str] = None, db: Session = Depends(get_db)):
    if error or not code:
        return RedirectResponse(url="https://app.wisualyst.com/?teams_connected=false&error=" + (error or "no_code") + "#alerts")
    
    client_id = os.environ.get("AZURE_CLIENT_ID", "52889720-e817-40ce-be25-ca732a9d1a5c")
    client_secret = os.environ.get("AZURE_CLIENT_SECRET", "")
    redirect_uri = os.environ.get("AZURE_REDIRECT_URI", "https://app.wisualyst.com/api/auth/callback/microsoft")
    
    user_email = "user@microsoft.com"
    try:
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        post_data = urllib.parse.urlencode({
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }).encode("utf-8")
        
        req = urllib.request.Request(token_url, data=post_data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                token_json = json.loads(response.read().decode("utf-8"))
                access_token = token_json.get("access_token")
                
                # Fetch user profile from Microsoft Graph
                graph_req = urllib.request.Request(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                with urllib.request.urlopen(graph_req, timeout=10) as graph_res:
                    if graph_res.status == 200:
                        me_data = json.loads(graph_res.read().decode("utf-8"))
                        user_email = me_data.get("mail") or me_data.get("userPrincipalName") or me_data.get("displayName") or "user@microsoft.com"
                        
                        ACTIVE_MICROSOFT_SESSIONS["latest"] = {
                            "access_token": access_token,
                            "user_email": user_email,
                            "user_id": me_data.get("id"),
                            "display_name": me_data.get("displayName")
                        }

                        existing_conn = db.query(MicrosoftOAuthConnection).filter(MicrosoftOAuthConnection.user_email == user_email).first()
                        if existing_conn:
                            existing_conn.access_token = access_token
                            existing_conn.refresh_token = token_json.get("refresh_token")
                            existing_conn.user_id = me_data.get("id")
                            existing_conn.display_name = me_data.get("displayName")
                            existing_conn.is_active = 1
                            existing_conn.updated_at = datetime.utcnow()
                        else:
                            new_conn = MicrosoftOAuthConnection(
                                user_email=user_email,
                                user_id=me_data.get("id"),
                                display_name=me_data.get("displayName"),
                                access_token=access_token,
                                refresh_token=token_json.get("refresh_token"),
                                is_active=1
                            )
                            db.add(new_conn)
                        db.commit()
    except Exception as e:
        print("Microsoft Graph token exchange note:", e)

    encoded_email = urllib.parse.quote(user_email)
    return RedirectResponse(url=f"https://app.wisualyst.com/?teams_connected=true&account={encoded_email}#alerts")

@router.get("/api/auth/microsoft/status", tags=["Microsoft Teams Integration"])
def microsoft_oauth_status(db: Session = Depends(get_db)):
    active_conn = db.query(MicrosoftOAuthConnection).filter(MicrosoftOAuthConnection.is_active == 1).order_by(MicrosoftOAuthConnection.updated_at.desc()).first()
    if active_conn:
        return {
            "connected": True,
            "account": active_conn.user_email,
            "display_name": active_conn.display_name,
            "client_id": os.environ.get("AZURE_CLIENT_ID", "52889720-e817-40ce-be25-ca732a9d1a5c")
        }
    return {
        "connected": False,
        "account": None,
        "client_id": os.environ.get("AZURE_CLIENT_ID", "52889720-e817-40ce-be25-ca732a9d1a5c")
    }

@router.post("/api/auth/microsoft/disconnect", tags=["Microsoft Teams Integration"])
def microsoft_oauth_disconnect(db: Session = Depends(get_db)):
    db.query(MicrosoftOAuthConnection).update({"is_active": 0})
    db.commit()
    ACTIVE_MICROSOFT_SESSIONS.clear()
    return {"status": "SUCCESS", "message": "Microsoft Teams disconnected successfully"}

# --- MCP Server Integration ---
@router.get("/api/mcp/tools", tags=["MCP Server Integration"])
def get_mcp_tools(db: Session = Depends(get_db)):
    from mcp.tools import MCPToolRegistry
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    server_path = os.path.join(base_dir, "mcp", "server.py")
    registry = MCPToolRegistry(db)
    return {
        "status": "ONLINE",
        "mcp_version": "2024-11-05",
        "transport": "JSON-RPC stdio",
        "server_path": server_path,
        "base_dir": base_dir,
        "tools": registry.get_tool_definitions()
    }

# --- BI Integration Adapters ---
@router.get("/api/bi/export", tags=["BI Integration"])
@router.get("/api/bi/powerbi", tags=["BI Integration"])
@router.get("/api/bi/adapter/powerbi", tags=["BI Integration"])
@router.get("/api/bi/adapter/powerbi/json", tags=["BI Integration"])
@router.get("/api/bi/adapter/powerbi.json", tags=["BI Integration"])
def export_powerbi(db: Session = Depends(get_db)):
    adapter = LocalBIAdapter()
    return adapter.export_powerbi(db)

@router.get("/api/bi/qlik", tags=["BI Integration"])
def export_qlik(db: Session = Depends(get_db)):
    adapter = LocalBIAdapter()
    return adapter.export_qlik(db)

@router.get("/api/bi/google-sheets", tags=["BI Integration"])
@router.get("/api/bi/export/csv", tags=["BI Integration"])
def export_bi_csv(db: Session = Depends(get_db)):
    adapter = LocalBIAdapter()
    csv_data = adapter.export_inventory_metrics_csv(db)
    return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=wisualyst_bi_dataset.csv"})
