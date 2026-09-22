from fastapi import APIRouter, Request, HTTPException
import json
import random
from app.db import insert_ticket, log_audit_event

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

# Global WebSocket broadcast manager callback (registered by main.py)
broadcast_callback = None

def set_broadcast_callback(fn):
    global broadcast_callback
    broadcast_callback = fn

async def notify_clients(event_data):
    if broadcast_callback:
        await broadcast_callback(event_data)

@router.post("/slack")
async def handle_slack_webhook(request: Request):
    payload = await request.json()
    log_audit_event("slack_webhook", payload)

    # Slack URL Verification Challenge
    if "challenge" in payload:
        return {"challenge": payload["challenge"]}

    event = payload.get("event", {})
    text = event.get("text", "New Slack mention requiring action")
    user = event.get("user", "U9988")

    ticket_id = f"SLACK-{random.randint(100, 999)}"
    ticket = {
        "id": ticket_id,
        "source": "slack",
        "source_label": f"Slack #{event.get('channel_type', 'dev-lounge')}",
        "priority": "badge-p2",
        "priority_label": "P2 Major",
        "title": text[:60],
        "description": text,
        "assigned_to": "alex",
        "assigned_name": "Alex Rivera",
        "state": "Action Required",
        "sla_remaining": "4h 00m remaining"
    }

    insert_ticket(ticket)
    await notify_clients({"type": "NEW_TICKET", "ticket": ticket})
    return {"status": "ok", "ticket_id": ticket_id}

@router.post("/jira")
async def handle_jira_webhook(request: Request):
    payload = await request.json()
    log_audit_event("jira_webhook", payload)

    issue = payload.get("issue", {})
    key = issue.get("key", f"JIRA-{random.randint(100, 999)}")
    fields = issue.get("fields", {})

    ticket = {
        "id": key,
        "source": "jira",
        "source_label": "Jira Sprint",
        "priority": "badge-p1",
        "priority_label": "P1 Critical",
        "title": fields.get("summary", "New Jira Issue Assigned"),
        "description": fields.get("description", "Action required for Jira ticket."),
        "assigned_to": "alex",
        "assigned_name": "Alex Rivera",
        "state": "Open",
        "sla_remaining": "2h 30m remaining"
    }

    insert_ticket(ticket)
    await notify_clients({"type": "NEW_TICKET", "ticket": ticket})
    return {"status": "ok", "ticket_id": key}

@router.post("/teams")
async def handle_teams_webhook(request: Request):
    payload = await request.json()
    log_audit_event("teams_webhook", payload)

    ticket_id = f"TEAMS-{random.randint(100, 999)}"
    ticket = {
        "id": ticket_id,
        "source": "teams",
        "source_label": "Teams Group",
        "priority": "badge-p1",
        "priority_label": "P1 Critical",
        "title": payload.get("title", "Urgent Teams Action Item"),
        "description": payload.get("text", "Group action item tagged in Teams."),
        "assigned_to": "elena",
        "assigned_name": "Elena Rostova",
        "state": "Awaiting Signoff",
        "sla_remaining": "1h 00m remaining"
    }

    insert_ticket(ticket)
    await notify_clients({"type": "NEW_TICKET", "ticket": ticket})
    return {"status": "ok", "ticket_id": ticket_id}

@router.post("/gmail")
async def handle_gmail_webhook(request: Request):
    payload = await request.json()
    log_audit_event("gmail_webhook", payload)

    ticket_id = f"GMAIL-{random.randint(100, 999)}"
    ticket = {
        "id": ticket_id,
        "source": "email",
        "source_label": "Gmail Action Item",
        "priority": "badge-p3",
        "priority_label": "P3 Moderate",
        "title": payload.get("subject", "Unread Gmail Action Item"),
        "description": payload.get("body", "Gmail notification needing response."),
        "assigned_to": "chris",
        "assigned_name": "Chris Vance",
        "state": "Pending Review",
        "sla_remaining": "1 Day remaining"
    }

    insert_ticket(ticket)
    await notify_clients({"type": "NEW_TICKET", "ticket": ticket})
    return {"status": "ok", "ticket_id": ticket_id}
