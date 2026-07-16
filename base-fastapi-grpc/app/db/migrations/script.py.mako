<%
down_revision_text = (
    ", ".join(down_revision)
    if isinstance(down_revision, (list, tuple))
    else (down_revision or "")
)
%>
"""${message}${"." if not message.endswith(".") else ""}

Revision ID: ${up_revision}
Revises:${f" {down_revision_text}" if down_revision_text else ""}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    """Run the migration."""
    ${upgrades if upgrades else ""}


def downgrade() -> None:
    """Undo the migration."""
    ${downgrades if downgrades else ""}
