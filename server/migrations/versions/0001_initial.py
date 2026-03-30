"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_workspaces_name", "workspaces", ["name"], unique=True)
    op.create_table(
        "nodes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("parent_node_id", sa.String(length=36), sa.ForeignKey("nodes.id"), nullable=True),
        sa.Column("user_prompt", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_nodes_workspace_id", "nodes", ["workspace_id"], unique=False)
    op.create_index("ix_nodes_parent_node_id", "nodes", ["parent_node_id"], unique=False)
    op.create_table(
        "branches",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("base_node_id", sa.String(length=36), sa.ForeignKey("nodes.id"), nullable=True),
        sa.Column("head_node_id", sa.String(length=36), sa.ForeignKey("nodes.id"), nullable=True),
        sa.Column("auto_named", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_branches_workspace_id", "branches", ["workspace_id"], unique=False)
    op.create_index("ix_branches_name", "branches", ["name"], unique=False)
    op.create_table(
        "runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("node_id", sa.String(length=36), sa.ForeignKey("nodes.id"), nullable=False),
        sa.Column("branch_id", sa.String(length=36), sa.ForeignKey("branches.id"), nullable=True),
        sa.Column("provider_name", sa.String(length=60), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("assistant_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_runs_workspace_id", "runs", ["workspace_id"], unique=False)
    op.create_index("ix_runs_node_id", "runs", ["node_id"], unique=False)
    op.create_index("ix_runs_branch_id", "runs", ["branch_id"], unique=False)
    op.create_table(
        "run_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_run_events_run_id", "run_events", ["run_id"], unique=False)
    op.create_table(
        "run_summaries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("runs.id"), nullable=False, unique=True),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_run_summaries_run_id", "run_summaries", ["run_id"], unique=True)
    op.create_table(
        "summary_tasks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("runs.id"), nullable=False, unique=True),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_summary_tasks_run_id", "summary_tasks", ["run_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_summary_tasks_run_id", table_name="summary_tasks")
    op.drop_table("summary_tasks")
    op.drop_index("ix_run_summaries_run_id", table_name="run_summaries")
    op.drop_table("run_summaries")
    op.drop_index("ix_run_events_run_id", table_name="run_events")
    op.drop_table("run_events")
    op.drop_index("ix_runs_branch_id", table_name="runs")
    op.drop_index("ix_runs_node_id", table_name="runs")
    op.drop_index("ix_runs_workspace_id", table_name="runs")
    op.drop_table("runs")
    op.drop_index("ix_branches_name", table_name="branches")
    op.drop_index("ix_branches_workspace_id", table_name="branches")
    op.drop_table("branches")
    op.drop_index("ix_nodes_parent_node_id", table_name="nodes")
    op.drop_index("ix_nodes_workspace_id", table_name="nodes")
    op.drop_table("nodes")
    op.drop_index("ix_workspaces_name", table_name="workspaces")
    op.drop_table("workspaces")
