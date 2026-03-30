from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Run, RunEvent, RunSummary, SummaryTask, SummaryTaskStatus


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
    events = list(db.scalars(select(RunEvent).where(RunEvent.run_id == run.id).order_by(RunEvent.sequence.asc())))
    tool_count = sum(1 for event in events if event.event_type == "tool_call")
    summary_text = (
        f"Assistant generated {len(events)} events with {tool_count} tool call(s)"
        f" and replied: {run.assistant_message or ''}"
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
