"""modification for messaging and updates

Revision ID: 09407ad39f12
Revises: fc8a4d1929cd
Create Date: 2024-09-16 18:51:24.049533

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '09407ad39f12'
down_revision: Union[str, None] = 'fc8a4d1929cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('books', sa.Column('isbn', sa.String(), nullable=True))
    op.add_column('books', sa.Column('description', sa.String(), nullable=True))
    op.create_unique_constraint(None, 'books', ['isbn'])
    op.drop_column('books', 'borrowed_until')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('books', sa.Column('borrowed_until', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'books', type_='unique')
    op.drop_column('books', 'description')
    op.drop_column('books', 'isbn')
    # ### end Alembic commands ###
