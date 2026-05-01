"""add result palette json

Revision ID: 8f42b19d0c31
Revises: 6a1f4d2c8b90
Create Date: 2026-04-30 19:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8f42b19d0c31'
down_revision = '6a1f4d2c8b90'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('results', schema=None) as batch_op:
        batch_op.add_column(sa.Column('palette_json', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('results', schema=None) as batch_op:
        batch_op.drop_column('palette_json')
