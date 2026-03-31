"""Add proper cascade and set null constraints for Alma

Revision ID: f71df0d27060
Revises: ddddb135a390
Create Date: 2026-03-30 07:56:35.072161

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f71df0d27060'
down_revision: Union[str, Sequence[str], None] = 'ddddb135a390'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Alma Prompt History (CASCADE)
    # We use a TRY/EXCEPT block equivalent logic (Alembic's drop_constraint if exists is tricky, so we'll just name it clearly)
    op.execute("ALTER TABLE alma_prompt_history DROP CONSTRAINT IF EXISTS alma_prompt_history_alma_id_fkey")
    op.execute("ALTER TABLE alma_prompt_history DROP CONSTRAINT IF EXISTS fk_alma_prompt_history_alma")
    op.create_foreign_key('fk_alma_prompt_history_alma', 'alma_prompt_history', 'ecosystem_resources', ['alma_id'], ['id'], ondelete='CASCADE')

    # 2. Projects (SET NULL)
    op.execute("ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_theoretical_alma_id_fkey")
    op.execute("ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_methodological_alma_id_fkey")
    op.execute("ALTER TABLE projects DROP CONSTRAINT IF EXISTS fk_projects_theoretical_alma")
    op.execute("ALTER TABLE projects DROP CONSTRAINT IF EXISTS fk_projects_methodological_alma")
    op.create_foreign_key('fk_projects_theoretical_alma', 'projects', 'ecosystem_resources', ['theoretical_alma_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_projects_methodological_alma', 'projects', 'ecosystem_resources', ['methodological_alma_id'], ['id'], ondelete='SET NULL')

    # 3. Chat Messages (SET NULL)
    op.execute("ALTER TABLE chat_messages DROP CONSTRAINT IF EXISTS fk_chat_messages_alma")
    op.create_foreign_key('fk_chat_messages_alma', 'chat_messages', 'ecosystem_resources', ['alma_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_chat_messages_alma', 'chat_messages', type_='foreignkey')
    op.drop_constraint('fk_projects_methodological_alma', 'projects', type_='foreignkey')
    op.drop_constraint('fk_projects_theoretical_alma', 'projects', type_='foreignkey')
    op.drop_constraint('fk_alma_prompt_history_alma', 'alma_prompt_history', type_='foreignkey')
    
    op.create_foreign_key('alma_prompt_history_alma_id_fkey', 'alma_prompt_history', 'ecosystem_resources', ['alma_id'], ['id'])
    op.create_foreign_key('projects_theoretical_alma_id_fkey', 'projects', 'ecosystem_resources', ['theoretical_alma_id'], ['id'])
    op.create_foreign_key('projects_methodological_alma_id_fkey', 'projects', 'ecosystem_resources', ['methodological_alma_id'], ['id'])
