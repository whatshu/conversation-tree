from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Branch, Workspace


def list_workspaces(db: Session) -> list[Workspace]:
    return list(db.scalars(select(Workspace).order_by(Workspace.created_at.asc())))


def create_workspace(db: Session, name: str, description: str | None = None) -> Workspace:
    workspace = Workspace(name=name, description=description)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


def get_workspace(db: Session, workspace_id: str) -> Workspace | None:
    return db.get(Workspace, workspace_id)


def ensure_main_branch(db: Session, workspace_id: str, head_node_id: str | None = None) -> Branch:
    branch = db.scalars(
        select(Branch).where(Branch.workspace_id == workspace_id, Branch.name == "main")
    ).first()
    if branch is None:
        branch = Branch(
            workspace_id=workspace_id,
            name="main",
            base_node_id=head_node_id,
            head_node_id=head_node_id,
            auto_named=False,
        )
        db.add(branch)
    else:
        if branch.base_node_id is None:
            branch.base_node_id = head_node_id
        branch.head_node_id = head_node_id
    db.flush()
    return branch


def build_auto_branch_name(prompt: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", prompt.strip().lower()).strip("-")
    slug = slug[:24] or "branch"
    return f"branch/{slug}"
