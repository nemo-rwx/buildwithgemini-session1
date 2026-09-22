# My agent: WorkPulse (Enterprise Action & Task Radar)
One-liner: A conversational workspace assistant that helps company employees track pending tasks and action items across Jira, Teams, Slack, and Email with real-time priority and deadline countdowns.

Tool coverage:
- Memory: Remembers employee role, team focus, working hours, notification preferences, and snoozed task rules across sessions.
- Tools: fetch_pending_tasks (scans Jira/Slack/Teams/Email), get_task_details, update_task_priority, snooze_task.
- Catalog/UI: Pending task cards & tables with priority badges, owner avatars, source tags, and time-remaining countdowns (A2UI).
- Image gen: Generates visual daily workload heatmaps and weekly completion digest graphics on demand.
- Sandbox: Computes urgency score weighting based on time-to-deadline, task impact, and pending dependencies.

Core rails (everyone): memory, tools, eval, deploy, frontend
My stretch menu (pick later): A2UI cards/tables, workload heatmap image generation, urgency computation sandbox
First eval question: "What are my top 3 high-priority pending items due today across Slack and Jira, and who is blocked on me?"
