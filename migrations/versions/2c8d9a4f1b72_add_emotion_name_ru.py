"""add emotion name ru

Revision ID: 2c8d9a4f1b72
Revises: 141e10142152
Create Date: 2026-04-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2c8d9a4f1b72'
down_revision = '141e10142152'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('emotions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('name_ru', sa.String(length=100), nullable=True))


def downgrade():
    with op.batch_alter_table('emotions', schema=None) as batch_op:
        batch_op.drop_column('name_ru')
