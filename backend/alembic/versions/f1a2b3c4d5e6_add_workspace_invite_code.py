"""add workspace invite code and move audit action

Revision ID: f1a2b3c4d5e6
Revises: e2f3a4b5c6d7
Create Date: 2026-09-10 14:00:00.000000

"""

import random
import string
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str | Sequence[str] | None = "e2f3a4b5c6d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _generate_code() -> str:
    """Generate a random 6-digit code."""
    return "".join(random.choices(string.digits, k=6))


def upgrade() -> None:
    """Add invite_code column to workspaces, backfill, then add audit action."""
    op.add_column("workspaces", sa.Column("invite_code", sa.String(6), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id FROM workspaces")).fetchall()

    seen: set[str] = set()
    for row in rows:
        code = _generate_code()
        while code in seen:
            code = _generate_code()
        seen.add(code)
        conn.execute(
            sa.text("UPDATE workspaces SET invite_code = :code WHERE id = :id"),
            {"code": code, "id": row[0]},
        )

    op.alter_column("workspaces", "invite_code", nullable=False)
    op.create_unique_constraint("uq_workspaces_invite_code", "workspaces", ["invite_code"])

    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'admin.workspace.regenerate_code'")
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'workspace.member.move'")


def downgrade() -> None:
    """Remove invite_code column."""
    op.drop_constraint("uq_workspaces_invite_code", "workspaces", type_="unique")
    op.drop_column("workspaces", "invite_code")
