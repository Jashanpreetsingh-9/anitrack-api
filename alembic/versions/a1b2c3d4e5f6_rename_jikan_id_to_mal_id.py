"""Rename jikan_id to mal_id on anime table."""

from typing import Sequence, Union

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "8bd6618c6c34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_anime_jikan_id", table_name="anime")
    op.alter_column("anime", "jikan_id", new_column_name="mal_id")
    op.create_index(op.f("ix_anime_mal_id"), "anime", ["mal_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_anime_mal_id"), table_name="anime")
    op.alter_column("anime", "mal_id", new_column_name="jikan_id")
    op.create_index("ix_anime_jikan_id", "anime", ["jikan_id"], unique=True)
