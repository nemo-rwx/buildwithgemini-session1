"""Minimal FastAPI proxy for a deployed A2A agent (Agent Runtime, agents-cli 1.1.0+).

The browser talks ONLY to this proxy (same origin, no CORS, no GCP creds in the
browser). The proxy authenticates with Application Default Credentials and
forwards chat to the deployed agent over the A2A protocol, returning replies as
structured parts the chat UI knows how to show.
"""

import os
import sys
import uuid
import json

# Add root directory to sys.path so app modules (db, dlp, webhooks) can be imported cleanly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    FilePart,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TextPart,
    TransportProtocol,
)
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.db import init_db, get_all_tickets
from app.dlp import sanitize_text
from app.webhooks import router as webhooks_router, set_broadcast_callback

RESOURCE = os.environ["AGENT_ENGINE_RESOURCE_NAME"]
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)
A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"
_A2UI_MIME = "application/json+a2ui"

_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }


app = FastAPI(title="WorkPulse Real-Time Enterprise Engine")

# WebSocket Connection Manager for Live Push Streaming
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

@app.on_event("startup")
def on_startup():
    init_db()
    set_broadcast_callback(manager.broadcast)

# Mount Webhooks APIRouter
app.include_router(webhooks_router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/v1/tickets")
async def fetch_tickets():
    return get_all_tickets()


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


_contexts: dict[str, str] = {}
_card: AgentCard | None = None


async def _get_card() -> AgentCard:
    global _card
    if _card is not None:
        return _card

    async with httpx.AsyncClient(timeout=30.0) as http:
        resp = await http.get(A2A_CARD_URL, headers=_auth_headers())
        resp.raise_for_status()
        _card = AgentCard.model_validate(resp.json())
        return _card


def _extract_parts(parts: list) -> list[dict]:
    out: list[dict] = []
    for p in parts or []:
        root = getattr(p, "root", p)
        if isinstance(root, TextPart) and getattr(root, "text", None):
            out.append({"kind": "text", "text": root.text})
        elif getattr(root, "data", None) is not None:
            meta = getattr(root, "metadata", None) or {}
            mime = meta.get("mimeType") if isinstance(meta, dict) else None
            if mime == _A2UI_MIME:
                out.append({"kind": "a2ui", "data": root.data})
            else:
                out.append({"kind": "text", "text": str(root.data)})
        elif isinstance(root, FilePart) and getattr(root, "file", None):
            f = root.file
            mime = getattr(f, "mime_type", None) or getattr(f, "mimeType", None)
            if mime == _A2UI_MIME:
                data_str = (
                    f.bytes.decode("utf-8")
                    if isinstance(f.bytes, bytes)
                    else str(f.bytes or "")
                )
                try:
                    out.append({"kind": "a2ui", "data": json.loads(data_str)})
                except Exception:
                    out.append({"kind": "text", "text": data_str})
            elif getattr(f, "uri", None):
                out.append({"kind": "text", "text": f.uri})
    return out


@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    user_msg = (body.get("message") or "").strip()
    session_id = body.get("session_id") or "default"

    if not user_msg:
        return JSONResponse({"parts": []})

    sanitized_msg = sanitize_text(user_msg)
    parts: list[dict] = []

    async with httpx.AsyncClient(headers=_auth_headers(), timeout=120.0) as http_client:
        card = await _get_card()
        factory = ClientFactory(
            ClientConfig(
                supported_transports=[
                    TransportProtocol.jsonrpc,
                    TransportProtocol.http_json,
                ],
                httpx_client=http_client,
            )
        )
        client = factory.create(card)

        msg = Message(
            message_id=str(uuid.uuid4()),
            role=Role.user,
            parts=[Part(root=TextPart(text=sanitized_msg))],
            context_id=_contexts.get(session_id),
        )

        last_task = None
        got_artifact_update = False
        async for event in client.send_message(msg):
            if not isinstance(event, tuple):
                continue
            task, update = event
            if task is not None:
                last_task = task
                if getattr(task, "context_id", None):
                    _contexts[session_id] = task.context_id
            if isinstance(update, TaskArtifactUpdateEvent) and getattr(update, "artifact", None):
                got_artifact_update = True
                parts.extend(_extract_parts(update.artifact.parts))

        if not got_artifact_update and last_task is not None:
            for artifact in getattr(last_task, "artifacts", None) or []:
                parts.extend(_extract_parts(artifact.parts))

    if not parts:
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": parts})
    return JSONResponse({"parts": parts})


@app.get("/dashboard")
async def dashboard():
    dashboard_path = os.path.join(os.path.dirname(__file__), "..", "app", "static", "dashboard.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return JSONResponse(status_code=404, content={"error": "Dashboard file not found"})


app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
