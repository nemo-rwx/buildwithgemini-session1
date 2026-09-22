# WorkPulse — Enterprise Action & Task Radar

> **WorkPulse** is a conversational workspace assistant that helps enterprise teams track, aggregate, and resolve pending action items across Jira, Microsoft Teams, Slack, and Email with real-time priority scoring, SLA countdowns, and automated task extraction.


---

## 🌟 Wired Features & Google Cloud Services

The agent is powered by Google's **Agent Development Kit (ADK 1.1.0)** and deployed on **Agent Runtime (Reasoning Engines)**.

### 🧠 Google Cloud & Vertex AI Integration
- **Vertex AI Memory Bank (`google.adk.tools.PreloadMemoryTool`)**: Cross-session long-term memory that automatically persists employee role, team focus, working hours, notification preferences, and snoozed task rules across turns.
- **Google Cloud Firestore (`google.cloud.firestore`)**: Database persistence for task items (`list_tasks_from_firestore`, `create_or_update_task_in_firestore`, `complete_task`, `extract_and_save_task_from_text`).
- **Google Cloud Storage (`google.cloud.storage`)**: Public static assets bucket (`qwiklabs-gcp-03-9b8a9428b63e-static-assets-bucket`) hosting generated visual workload heatmaps and video briefings.
- **Imagen 3 / GenAI (`gemini-3.1-flash-lite-image`)**: Visual image generation tool (`generate_workload_heatmap`) for daily workload charts.
- **Google Omni Model (`gemini-omni-flash-preview`)**: Short video briefing generator tool (`generate_task_briefing_video`) operating in the global region.
- **Agent Engine Sandbox Code Executor (`AgentEngineSandboxCodeExecutor`)**: Isolated execution sandbox for math, urgency score calculations, and data processing.
- **A2UI Cards & Tables (`a2ui`)**: Declarative UI surface rendering via A2UI v0.8 basic catalog.

### 🔌 Enterprise Connectors & Real-Time Engine
- **OAuth 2.0 Integration**: Authentication status verification across Jira, Slack, Teams, and Email.
- **FastAPI A2A Proxy**: Secure backend proxy handling Agent-to-Agent (A2A) protocol communication.
- **SQLite Task Database & Audit Logs (`workpulse_prod.db`)**: Real-time production task storage.
- **WebSockets Live Stream (`/ws`)**: Real-time bidirectional push notifications for incoming webhooks (`/api/v1/webhooks/slack`, `/api/v1/webhooks/jira`, `/api/v1/webhooks/teams`, `/api/v1/webhooks/gmail`).

---

## 📋 Status of Planned Capabilities

- **Vertex AI RAG Engine**: *Planned, not yet implemented* (relying on direct Firestore and OAuth REST connectors).

---

## 🚀 Local Setup & Run Instructions

### Prerequisites
- Python 3.10+
- `uv` package manager

### Environment Configuration
Set your deployed Reasoning Engine resource name and app directory:

```bash
export AGENT_ENGINE_RESOURCE_NAME="projects/39876285796/locations/us-east1/reasoningEngines/3495402440281292800"
export AGENT_DIRECTORY="app"
export PORT=8080
```

### Running the Application

1. **Start the FastAPI Proxy & Web Server**:
   ```bash
   cd workpulse/frontend
   uv run python main.py
   ```

2. **Access Interfaces in Browser**:
   - **Cognizant WorkPulse Chat UI:** Navigate to port `8080` in your web browser.
   - **All Tickets & Developer Workstation:** Navigate to port `8080` path `/dashboard` in your browser.

---

## 🧪 Evaluation Queries

- *"What are my top 3 high-priority pending items due today across Slack and Jira, and who is blocked on me?"*
- *"Identify what are left across Jira, Teams, Slack, and Email and show developer workload."*
- *"Generate a visual daily workload heatmap chart showing task completion rates across teams."*
