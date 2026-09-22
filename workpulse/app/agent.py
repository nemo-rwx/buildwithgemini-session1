# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import urllib.request
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore, storage
from google.genai import types

from app.a2ui_utils import a2ui_callback
from app.auth import (
    get_email_oauth_headers,
    get_jira_oauth_headers,
    get_slack_oauth_client,
    get_teams_oauth_headers,
    verify_oauth_configuration,
)

# HARDCODED PROJECT, BUCKET & AGENT ENGINE RESOURCE CONFIGURATION
PROJECT_ID = "qwiklabs-gcp-03-9b8a9428b63e"
BUCKET_NAME = "qwiklabs-gcp-03-9b8a9428b63e-static-assets-bucket"
REASONING_ENGINE_RESOURCE_NAME = "projects/39876285796/locations/us-east1/reasoningEngines/3495402440281292800"


def _get_firestore_db():
    return firestore.Client(project=PROJECT_ID)


# WRITE: after each turn, send the session to Memory Bank for extraction.
async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None


def check_oauth_status() -> str:
    """Checks the OAuth 2.0 authentication status across Email, Slack, Teams, and Jira integrations.

    Returns:
        Structured text summary of OAuth authentication status per service.
    """
    statuses = verify_oauth_configuration()
    summary = ["OAuth 2.0 Integration Status:"]
    for service, status in statuses.items():
        summary.append(f"• {service}: {status}")
    return "\n".join(summary)


async def generate_workload_heatmap(
    prompt: str = "Daily workload heatmap chart showing task completion rates across teams",
    tool_context: ToolContext = None,
) -> str:
    """Generates a visual workload heatmap image chart using gemini-3.1-flash-lite-image in global region.

    Saves the generated image as an artifact in Playground via tool_context.save_artifact,
    and uploads the image bytes to a public Cloud Storage bucket, returning its public https URL.

    Args:
        prompt: Description of the workload visual or digest heatmap graphic to generate.
        tool_context: ADK ToolContext instance provided automatically at runtime.

    Returns:
        Public HTTPS URL (https://storage.googleapis.com/<bucket>/<object>) of the generated image.
    """
    genai_client = genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location="global",
    )
    res = genai_client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    candidate = res.candidates[0]
    image_part = candidate.content.parts[0]
    image_bytes = image_part.inline_data.data
    mime_type = image_part.inline_data.mime_type or "image/png"

    ext = "jpg" if "jpeg" in mime_type else "png"
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    object_name = f"workload_heatmap_{timestamp}.{ext}"

    # (1) Save with tool_context.save_artifact for Playground Artifacts panel
    if tool_context is not None:
        artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        await tool_context.save_artifact(object_name, artifact_part)

    # (2) Upload image bytes directly to public GCS bucket and return public HTTPS URL
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(object_name)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{object_name}"
    return public_url


async def generate_task_briefing_video(
    prompt: str = "A short video briefing summarizing pending high-priority sprint tasks and action radar status",
    tool_context: ToolContext = None,
) -> str:
    """Generates a short video briefing for task items using Google's Omni model (gemini-omni-flash-preview) in the global region.

    Saves the generated video as an artifact in Playground via tool_context.save_artifact,
    and uploads the video bytes directly to a public Cloud Storage bucket, returning its public https URL.

    Args:
        prompt: Description of the task briefing video to generate.
        tool_context: ADK ToolContext instance provided automatically at runtime.

    Returns:
        Public HTTPS URL (https://storage.googleapis.com/<bucket>/<object>) of the generated video.
    """
    genai_client = genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location="global",
    )
    res = genai_client.models.generate_content(
        model="gemini-omni-flash-preview",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["VIDEO"],
        ),
    )

    candidate = res.candidates[0]
    video_part = candidate.content.parts[0]
    video_bytes = video_part.inline_data.data
    mime_type = video_part.inline_data.mime_type or "video/mp4"

    ext = "mp4"
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    object_name = f"task_briefing_video_{timestamp}.{ext}"

    # (1) Save with tool_context.save_artifact for Playground Artifacts panel
    if tool_context is not None:
        artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
        await tool_context.save_artifact(object_name, artifact_part)

    # (2) Upload video bytes directly to public GCS bucket and return public HTTPS URL
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(object_name)
    blob.upload_from_string(video_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{object_name}"
    return public_url


def get_github_system_status() -> str:
    """Fetches real-time operational status for GitHub services (Git Operations, Actions, API, Issues).

    Returns:
        Structured text summary of current GitHub system health.
    """
    url = "https://www.githubstatus.com/api/v2/summary.json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WorkPulse/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            overall_status = data.get("status", {}).get("description", "Unknown")
            components = data.get("components", [])

            summary = [f"GitHub System Status: {overall_status}"]
            for comp in components:
                name = comp.get("name")
                status = comp.get("status")
                if name and status and "Visit" not in name and len(summary) <= 6:
                    summary.append(f"• {name}: {status}")
            return "\n".join(summary)
    except Exception as e:
        return f"Unable to fetch GitHub status: {e}"


def list_tasks_from_firestore(status: str = "", source: str = "") -> str:
    """Reads tasks from the Firestore database collection.

    Args:
        status: Filter tasks by status (e.g. 'pending', 'completed', 'snoozed').
        source: Filter tasks by source system (e.g. 'Jira', 'Slack', 'Teams', 'Email').

    Returns:
        Structured text representation of tasks stored in Firestore.
    """
    db = _get_firestore_db()
    query_ref = db.collection("tasks")

    docs = list(query_ref.stream())
    if not docs:
        return "No tasks found in Firestore database."

    results = []
    for doc in docs:
        d = doc.to_dict()
        if status and d.get("status") != status:
            continue
        if source and d.get("source") != source:
            continue
        results.append(
            f"• [{d.get('source', 'System')}] {d.get('task_id', doc.id)}: {d.get('title')} "
            f"| Owner: {d.get('owner')} | Priority: {d.get('priority')} | Due: {d.get('due_date')} | Status: {d.get('status')}"
        )
    if not results:
        return f"No tasks match filter status='{status}', source='{source}'."
    return "\n".join(results)


def create_or_update_task_in_firestore(
    task_id: str,
    title: str,
    source: str,
    owner: str,
    priority: str = "MEDIUM",
    due_date: str = "Today",
    status: str = "pending",
) -> str:
    """Creates or updates a task document in the Firestore database.

    Args:
        task_id: Unique identifier for the task (e.g. 'PROJ-105').
        title: Description or title of the task.
        source: System source (e.g. 'Jira', 'Slack', 'Teams', 'Email').
        owner: Assigned owner of the task.
        priority: Task priority level ('HIGH', 'MEDIUM', 'LOW').
        due_date: Deadline or due date description.
        status: Task status ('pending', 'in_progress', 'completed', 'snoozed').

    Returns:
        Confirmation message of the saved Firestore document.
    """
    db = _get_firestore_db()
    doc_data = {
        "task_id": task_id,
        "title": title,
        "source": source,
        "owner": owner,
        "priority": priority,
        "due_date": due_date,
        "status": status,
    }
    db.collection("tasks").document(task_id).set(doc_data)
    return f"Successfully saved task '{task_id}' ({title}) to Firestore database."


def extract_and_save_task_from_text(
    raw_text: str,
    source: str = "Email",
    task_id: str = "",
    title: str = "",
    owner: str = "You",
    priority: str = "MEDIUM",
    due_date: str = "Today",
) -> str:
    """Parses unstructured text from Email, Slack, Teams, or Jira and saves it as a pending task in Firestore.

    Args:
        raw_text: The raw email body, chat thread message, or issue description to parse.
        source: Originating platform ('Email', 'Slack', 'Teams', 'Jira').
        task_id: Unique task identifier (e.g. 'EMAIL-101', 'SLACK-88'). Auto-generated if omitted.
        title: Extracted concise task title or summary. Auto-summarized if omitted.
        owner: Assigned owner extracted from the text (default 'You').
        priority: Priority level ('HIGH', 'MEDIUM', 'LOW').
        due_date: Deadline or due date description (e.g. 'Today', 'Tomorrow', 'In 2 days').

    Returns:
        Confirmation message of the extracted task saved in Firestore.
    """
    if not task_id:
        timestamp_id = datetime.datetime.now(datetime.timezone.utc).strftime("%M%S")
        prefix = source.upper()[:4]
        task_id = f"{prefix}-{timestamp_id}"

    if not title:
        clean_text = raw_text.strip().split("\n")[0]
        title = (clean_text[:60] + "...") if len(clean_text) > 60 else clean_text

    return create_or_update_task_in_firestore(
        task_id=task_id,
        title=title,
        source=source,
        owner=owner,
        priority=priority,
        due_date=due_date,
        status="pending",
    )


def complete_task(task_id: str, resolution_notes: str = "") -> str:
    """Marks a task as completed in Firestore.

    Args:
        task_id: Unique identifier for the task to complete (e.g. 'COMP-99').
        resolution_notes: Optional resolution summary or notes.

    Returns:
        Confirmation message of completion.
    """
    db = _get_firestore_db()
    doc_ref = db.collection("tasks").document(task_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Task '{task_id}' not found in Firestore database."

    doc_ref.update({
        "status": "completed",
        "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "resolution_notes": resolution_notes,
    })
    return f"Task '{task_id}' marked as completed in Firestore."


def fetch_pending_tasks(query: str = "") -> str:
    """Scans pending tasks across Jira, Teams, Slack, and Email for the employee.

    Args:
        query: Optional filter for specific system or project (e.g. 'Jira', 'Slack').

    Returns:
        Structured string listing pending action items, assigned owner, deadline, and priority.
    """
    return list_tasks_from_firestore(status="pending")


def snooze_task(task_id: str, duration_hours: int = 24) -> str:
    """Snoozes a task reminder for a specified number of hours.

    Args:
        task_id: The ID of the task to snooze.
        duration_hours: Number of hours to snooze (default 24).

    Returns:
        Confirmation message.
    """
    return create_or_update_task_in_firestore(
        task_id=task_id,
        title=f"Snoozed task {task_id}",
        source="System",
        owner="You",
        priority="LOW",
        due_date=f"Snoozed for {duration_hours}h",
        status="snoozed",
    )


# BUILD A2UI SYSTEM PROMPT (v0.8 & Basic Catalog)
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are WorkPulse, an intelligent enterprise workspace assistant. "
        "You help company employees track pending tasks across Jira, Teams, Slack, and Email using Firestore tools, "
        "extract and save structured pending tasks from raw email text, Slack threads, Teams pings, or Jira issue descriptions, "
        "execute Python code safely in a sandbox to perform math or data analysis, "
        "manage OAuth 2.0 authentication status across services, generate visual workload heatmaps, "
        "generate short task briefing videos using Google's Omni model (gemini-omni-flash-preview), "
        "and monitor developer infrastructure health via the GitHub Status API. "
        "You remember the user's stated preferences, working hours, team focus, snoozed task rules, "
        "and ALL user allergies and dietary/health restrictions from previous conversations to personalize responses."
    ),
    workflow_description="Analyze the request and return structured A2UI cards or tables when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        fetch_pending_tasks,
        snooze_task,
        complete_task,
        extract_and_save_task_from_text,
        check_oauth_status,
        generate_workload_heatmap,
        generate_task_briefing_video,
        get_github_system_status,
        list_tasks_from_firestore,
        create_or_update_task_in_firestore,
    ],
    code_executor=AgentEngineSandboxCodeExecutor(
        agent_engine_resource_name=REASONING_ENGINE_RESOURCE_NAME
    ),
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
