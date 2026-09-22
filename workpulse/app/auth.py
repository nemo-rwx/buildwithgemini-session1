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

"""OAuth 2.0 Authentication Helper Module for WorkPulse.

Manages OAuth 2.0 credentials and token resolution across Slack, Jira,
Microsoft Teams, and Email APIs using GCP Secret Manager with environment variable fallback.
"""

import os
from typing import Any, Dict

from google.cloud import secretmanager
from slack_sdk import WebClient
import msal

PROJECT_ID = "qwiklabs-gcp-03-9b8a9428b63e"


def get_oauth_secret(secret_id: str, default_env_var: str = "") -> str:
    """Fetches an OAuth secret from GCP Secret Manager or environment variable.

    Args:
        secret_id: ID of the secret in Secret Manager (e.g. 'slack-oauth-token').
        default_env_var: Optional environment variable name to fall back to.

    Returns:
        The secret string or empty string if unconfigured.
    """
    if default_env_var and os.getenv(default_env_var):
        return os.getenv(default_env_var, "")

    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8").strip()
    except Exception:
        # Fall back to env var if Secret Manager access fails or secret does not exist
        return os.getenv(default_env_var, "") if default_env_var else ""


def get_slack_oauth_client() -> WebClient:
    """Returns an authorized Slack SDK WebClient using OAuth token."""
    token = get_oauth_secret("slack-oauth-token", "SLACK_OAUTH_TOKEN")
    return WebClient(token=token or "dummy-slack-token")


def get_jira_oauth_headers() -> Dict[str, str]:
    """Returns OAuth 2.0 Authorization headers for Atlassian Jira Cloud API."""
    token = get_oauth_secret("jira-oauth-token", "JIRA_OAUTH_TOKEN")
    if not token:
        return {"Content-Type": "application/json"}
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def get_teams_oauth_headers() -> Dict[str, str]:
    """Returns OAuth 2.0 Authorization headers for Microsoft Teams Graph API."""
    token = get_oauth_secret("teams-oauth-token", "TEAMS_OAUTH_TOKEN")
    if not token:
        return {"Content-Type": "application/json"}
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def get_email_oauth_headers() -> Dict[str, str]:
    """Returns OAuth 2.0 Authorization headers for Email API (Gmail / MS Graph)."""
    token = get_oauth_secret("email-oauth-token", "EMAIL_OAUTH_TOKEN")
    if not token:
        return {"Content-Type": "application/json"}
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def verify_oauth_configuration() -> Dict[str, str]:
    """Checks configuration status of all 4 workspace OAuth providers.

    Returns:
        Dictionary mapping provider name to status string.
    """
    providers = {
        "Slack": "slack-oauth-token",
        "Jira": "jira-oauth-token",
        "Teams": "teams-oauth-token",
        "Email": "email-oauth-token",
    }
    status = {}
    for name, secret_id in providers.items():
        env_var = f"{name.upper()}_OAUTH_TOKEN"
        token = get_oauth_secret(secret_id, env_var)
        status[name] = "Configured (OAuth 2.0)" if token else "Pending Setup (Mock Fallback)"
    return status
