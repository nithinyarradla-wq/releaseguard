"""Initial schema.

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "releases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("service", sa.String(255), nullable=False, index=True),
        sa.Column("env", sa.String(50), nullable=False, index=True),
        sa.Column("git_sha", sa.String(40), nullable=False),
        sa.Column("build_id", sa.String(255), nullable=False),
        sa.Column("pipeline_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "policies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("service", sa.String(255), nullable=False, index=True),
        sa.Column("env", sa.String(50), nullable=False, index=True),
        sa.Column("rules_json", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "signals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("release_id", sa.String(36), sa.ForeignKey("releases.id"), nullable=False),
        sa.Column("type", sa.Enum("TEST", "COVERAGE", "PERF", "CANARY", "DEP", name="signaltype"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("value_num", sa.Float(), nullable=True),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("collected_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "evaluations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("release_id", sa.String(36), sa.ForeignKey("releases.id"), nullable=False),
        sa.Column("policy_id", sa.String(36), sa.ForeignKey("policies.id"), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("decision", sa.Enum("APPROVE", "WARN", "BLOCK", name="decision"), nullable=False),
        sa.Column("rationale_json", sa.JSON(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("evaluations")
    op.drop_table("signals")
    op.drop_table("policies")
    op.drop_table("releases")
