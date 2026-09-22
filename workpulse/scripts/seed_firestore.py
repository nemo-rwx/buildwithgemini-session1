#!/usr/bin/env python3
"""Seed script for WorkPulse Firestore task items.

HARDCODED PROJECT ID: qwiklabs-gcp-03-9b8a9428b63e
Do NOT use google.auth.default() or GOOGLE_CLOUD_PROJECT on Agent Platform.
"""

import subprocess
import google.oauth2.credentials
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-9b8a9428b63e"

SEED_TASKS = [
    {
        "task_id": "PROJ-102",
        "title": "Fix authentication timeout bug in production gateway",
        "source": "Jira",
        "owner": "Alex",
        "priority": "HIGH",
        "due_date": "Today (4 hours left)",
        "status": "pending",
        "category": "Engineering",
    },
    {
        "task_id": "PR-42",
        "title": "Review deployment pull request for payments v2 service",
        "source": "Slack",
        "owner": "You (pending review)",
        "priority": "MEDIUM",
        "due_date": "Tomorrow",
        "status": "pending",
        "category": "Engineering",
    },
    {
        "task_id": "COMP-99",
        "title": "Submit Q3 enterprise security compliance certification",
        "source": "Teams",
        "owner": "You",
        "priority": "HIGH",
        "due_date": "Today (2 hours left)",
        "status": "pending",
        "category": "Compliance",
    },
    {
        "task_id": "EXP-77",
        "title": "Approve annual travel expense report for Chris",
        "source": "Email",
        "owner": "You",
        "priority": "LOW",
        "due_date": "In 3 days",
        "status": "pending",
        "category": "Finance",
    },
]


def get_firestore_client():
    try:
        token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
        creds = google.oauth2.credentials.Credentials(token)
        return firestore.Client(project=PROJECT_ID, credentials=creds)
    except Exception:
        return firestore.Client(project=PROJECT_ID)


def seed():
    print(f"Connecting to Firestore for project: '{PROJECT_ID}'...")
    db = get_firestore_client()
    collection_ref = db.collection("tasks")

    for task in SEED_TASKS:
        doc_ref = collection_ref.document(task["task_id"])
        doc_ref.set(task)
        print(f"  [+] Seeded task {task['task_id']}: '{task['title']}' ({task['source']})")

    print("✅ Firestore seeding completed successfully!")


if __name__ == "__main__":
    seed()
