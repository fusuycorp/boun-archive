"""align schema indexes and trgm

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-30 14:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Composite indexes matching models.py & init_db.sql
    op.create_index('idx_courses_term_dept', 'courses', ['term_id', 'dept_kisaadi'], unique=False, if_not_exists=True)
    op.create_index('idx_slots_course_room', 'course_slots', ['course_id', 'room_id'], unique=False, if_not_exists=True)
    op.create_index('idx_quota_course_captured', 'quota_snapshots', ['course_code', 'captured_at'], unique=False, if_not_exists=True)

    # 2. Enforce NOT NULL and ON DELETE CASCADE on course_slots.course_id (PostgreSQL)
    if is_postgres:
        op.execute("DELETE FROM course_slots WHERE course_id IS NULL")
        op.alter_column('course_slots', 'course_id', existing_type=sa.Integer(), nullable=False)
        op.execute("ALTER TABLE course_slots DROP CONSTRAINT IF EXISTS course_slots_course_id_fkey")
        op.create_foreign_key(
            'course_slots_course_id_fkey',
            'course_slots',
            'courses',
            ['course_id'],
            ['id'],
            ondelete='CASCADE',
        )

        # 3. Enable pg_trgm and GIN trigram indexes for fallback search performance
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute("CREATE INDEX IF NOT EXISTS idx_courses_title_trgm ON courses USING gin (title gin_trgm_ops)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_courses_code_trgm ON courses USING gin (course_code gin_trgm_ops)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_instructors_name_trgm ON instructors USING gin (full_name gin_trgm_ops)")


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.execute("DROP INDEX IF EXISTS idx_instructors_name_trgm")
        op.execute("DROP INDEX IF EXISTS idx_courses_code_trgm")
        op.execute("DROP INDEX IF EXISTS idx_courses_title_trgm")
        op.drop_constraint('course_slots_course_id_fkey', 'course_slots', type_='foreignkey')
        op.create_foreign_key(
            'course_slots_course_id_fkey',
            'course_slots',
            'courses',
            ['course_id'],
            ['id'],
        )
        op.alter_column('course_slots', 'course_id', existing_type=sa.Integer(), nullable=True)

    op.drop_index('idx_quota_course_captured', table_name='quota_snapshots', if_exists=True)
    op.drop_index('idx_slots_course_room', table_name='course_slots', if_exists=True)
    op.drop_index('idx_courses_term_dept', table_name='courses', if_exists=True)
