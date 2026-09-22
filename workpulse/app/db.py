import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "workpulse_prod.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create Tickets Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        source_label TEXT NOT NULL,
        priority TEXT NOT NULL,
        priority_label TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        assigned_to TEXT NOT NULL,
        assigned_name TEXT NOT NULL,
        state TEXT NOT NULL,
        sla_remaining TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Create Audit Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        payload TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Seed Initial Demo Data if empty
    cursor.execute("SELECT COUNT(*) as count FROM tickets")
    if cursor.fetchone()["count"] == 0:
        demo_tickets = [
            ("PROJ-102", "jira", "Jira Sprint", "badge-p1", "P1 Critical", "Fix auth timeout bug in API gateway microservice", "Gateway connection drops under load spikes. Needs memory pool tuning.", "alex", "Alex Rivera", "Pending Fix", "3h 42m remaining"),
            ("PR-42", "slack", "Slack #frontend-pr", "badge-p2", "P2 Major", "Review deployment pull request for payments v2", "Stripe webhook retry UI component review.", "chris", "Chris Vance", "In Review", "18h remaining"),
            ("COMP-99", "teams", "Teams #security-ops", "badge-p1", "P1 Critical", "Submit Q3 security compliance certification signoff", "Audit blocker: Need digital signature for SOC2 checklist.", "elena", "Elena Rostova", "Awaiting Signoff", "1h 15m remaining"),
            ("EXP-77", "email", "Gmail Action Item", "badge-p3", "P3 Moderate", "Approve annual travel expense report & receipts", "Pending manager audit check for receipts.", "elena", "Elena Rostova", "Pending Audit", "2 Days remaining"),
            ("INFRA-501", "jira", "Jira Sprint", "badge-p2", "P2 Major", "Provision GKE cluster autoscaling policy for prod", "HPA autoscaling metrics configured for 80% CPU target.", "samir", "Samir Patel", "Resolved / Closed", "SLA Met")
        ]
        cursor.executemany("""
        INSERT INTO tickets (id, source, source_label, priority, priority_label, title, description, assigned_to, assigned_name, state, sla_remaining)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, demo_tickets)

    conn.commit()
    conn.close()

def get_all_tickets():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def insert_ticket(ticket_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO tickets (id, source, source_label, priority, priority_label, title, description, assigned_to, assigned_name, state, sla_remaining)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ticket_data["id"],
        ticket_data["source"],
        ticket_data["source_label"],
        ticket_data["priority"],
        ticket_data["priority_label"],
        ticket_data["title"],
        ticket_data["description"],
        ticket_data["assigned_to"],
        ticket_data["assigned_name"],
        ticket_data["state"],
        ticket_data["sla_remaining"]
    ))
    conn.commit()
    conn.close()

def log_audit_event(event_type, payload):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO audit_logs (event_type, payload) VALUES (?, ?)", (event_type, json.dumps(payload)))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("✔ WorkPulse production SQLite database initialized successfully.")
