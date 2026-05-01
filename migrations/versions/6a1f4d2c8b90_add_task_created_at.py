"""add task created_at

Revision ID: 6a1f4d2c8b90
Revises: dfbda890c243
Create Date: 2026-04-30 19:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6a1f4d2c8b90'
down_revision = 'dfbda890c243'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))

    op.execute("UPDATE tasks SET created_at = NOW() WHERE created_at IS NULL")

    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.alter_column('created_at', existing_type=sa.DateTime(), nullable=False)


def downgrade():
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_column('created_at')
