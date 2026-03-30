from __future__ import annotations

import asyncio
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Run, RunEvent, RunSummary, SummaryTask, SummaryTaskStatus
from app.services.providers import build_provider, generate_summary


def process_one_summary_task(db: Session) -> bool:
    task = db.scalars(
        select(SummaryTask).where(SummaryTask.status == SummaryTaskStatus.pending).order_by(SummaryTask.created_at.asc())
    ).first()
    if task is None:
        return False

    task.status = SummaryTaskStatus.processing
    task.attempts += 1
    db.flush()
    run = db.scalars(select(Run).where(Run.id == task.run_id)).one()
    node = run.node
    events = list(db.scalars(select(RunEvent).where(RunEvent.run_id == run.id).order_by(RunEvent.sequence.asc())))
    tool_events = [
        {"event_type": event.event_type, "payload": json.loads(event.payload_json)}
        for event in events
        if event.event_type in {"tool_call", "tool_result"}
    ]
    provider = build_provider()
    summary_text = asyncio.run(
        generate_summary(
            provider,
            user_prompt=node.user_prompt,
            assistant_message=run.assistant_message or "",
            tool_events=tool_events,
            model=get_settings().summary_model,
        )
    )
    if run.summary is None:
        db.add(RunSummary(run_id=run.id, summary_text=summary_text, status="completed"))
    else:
        run.summary.summary_text = summary_text
        run.summary.status = "completed"
    task.status = SummaryTaskStatus.completed
    task.last_error = None
    db.commit()
    return True
