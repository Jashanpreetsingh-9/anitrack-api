"""Add profile_complete flag for post-OAuth onboarding."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("profile_complete", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Existing password users are fully set up.
    op.execute(
        "UPDATE users SET profile_complete = TRUE WHERE hashed_password IS NOT NULL"
    )
    op.alter_column("users", "profile_complete", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "profile_complete")
