"""Create missing application tables without changing existing data.

Revision ID: 0001_additive_baseline
Revises:
"""

from alembic import op

from backend import models  # noqa: F401
from backend.database import Base

revision = "0001_additive_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # create_all checks existing tables, so this baseline safely adopts databases
    # previously initialized by the application and creates only missing tables.
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade():
    # Intentionally preserve application tables and user records. Schema rollback
    # is a forward-only operational action for this initial adoption revision.
    pass
