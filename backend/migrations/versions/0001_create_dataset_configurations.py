"""create the dataset_configurations table

Revision ID: 0001
Revises:
Create Date: 2026-11-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dataset_configurations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("team", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("manifest", sa.LargeBinary(), nullable=False),
        sa.UniqueConstraint(
            "team", "name", name="uq_dataset_configurations_team_name"
        ),
    )


def downgrade() -> None:
    op.drop_table("dataset_configurations")
