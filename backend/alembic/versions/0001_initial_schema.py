"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-08-28 17:54:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. terms
    op.create_table(
        'terms',
        sa.Column('id', sa.String(length=15), nullable=False),
        sa.Column('academic_year', sa.String(length=9), nullable=False),
        sa.Column('semester_num', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. departments
    op.create_table(
        'departments',
        sa.Column('kisaadi', sa.String(length=10), nullable=False),
        sa.Column('bolum', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('kisaadi')
    )

    # 3. instructors
    op.create_table(
        'instructors',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('full_name')
    )
    op.create_index(op.f('ix_instructors_id'), 'instructors', ['id'], unique=False)
    op.create_index(op.f('ix_instructors_full_name'), 'instructors', ['full_name'], unique=True)

    # 4. rooms
    op.create_table(
        'rooms',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('building', sa.String(length=50), nullable=True),
        sa.Column('capacity', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_rooms_id'), 'rooms', ['id'], unique=False)
    op.create_index(op.f('ix_rooms_name'), 'rooms', ['name'], unique=True)

    # 5. courses
    op.create_table(
        'courses',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('term_id', sa.String(length=15), nullable=True),
        sa.Column('dept_kisaadi', sa.String(length=10), nullable=True),
        sa.Column('course_code', sa.String(length=20), nullable=False),
        sa.Column('section', sa.String(length=5), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('instructor_id', sa.Integer(), nullable=True),
        sa.Column('credits', sa.Integer(), nullable=True),
        sa.Column('ects', sa.Integer(), nullable=True),
        sa.Column('delivery_method', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['dept_kisaadi'], ['departments.kisaadi'], ),
        sa.ForeignKeyConstraint(['instructor_id'], ['instructors.id'], ),
        sa.ForeignKeyConstraint(['term_id'], ['terms.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('term_id', 'course_code', 'section', name='uq_courses_term_code_section')
    )
    op.create_index(op.f('ix_courses_id'), 'courses', ['id'], unique=False)
    op.create_index(op.f('ix_courses_term_id'), 'courses', ['term_id'], unique=False)
    op.create_index(op.f('ix_courses_dept_kisaadi'), 'courses', ['dept_kisaadi'], unique=False)
    op.create_index(op.f('ix_courses_course_code'), 'courses', ['course_code'], unique=False)
    op.create_index(op.f('ix_courses_instructor_id'), 'courses', ['instructor_id'], unique=False)
    op.create_index('idx_courses_lookup', 'courses', ['term_id', 'course_code', 'section'], unique=False)

    # 6. course_slots
    op.create_table(
        'course_slots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=True),
        sa.Column('day_code', sa.String(length=10), nullable=True),
        sa.Column('slot_hour', sa.Integer(), nullable=True),
        sa.Column('slot_title', sa.String(length=255), nullable=True),
        sa.Column('room_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
        sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_course_slots_id'), 'course_slots', ['id'], unique=False)
    op.create_index(op.f('ix_course_slots_course_id'), 'course_slots', ['course_id'], unique=False)
    op.create_index(op.f('ix_course_slots_day_code'), 'course_slots', ['day_code'], unique=False)
    op.create_index(op.f('ix_course_slots_slot_hour'), 'course_slots', ['slot_hour'], unique=False)
    op.create_index(op.f('ix_course_slots_room_id'), 'course_slots', ['room_id'], unique=False)

    # 7. quota_snapshots
    op.create_table(
        'quota_snapshots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('term_id', sa.String(length=15), nullable=True),
        sa.Column('course_code', sa.String(length=20), nullable=False),
        sa.Column('section', sa.String(length=5), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('quota', sa.String(length=20), nullable=True),
        sa.Column('current', sa.String(length=20), nullable=True),
        sa.Column('quota_numeric', sa.Integer(), nullable=True),
        sa.Column('current_numeric', sa.Integer(), nullable=True),
        sa.Column('is_consent', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('is_unlimited', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('available', sa.Integer(), nullable=True),
        sa.Column('captured_at', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['term_id'], ['terms.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('term_id', 'course_code', 'section', 'department', 'captured_at', name='uq_quota_snapshot_entry')
    )
    op.create_index(op.f('ix_quota_snapshots_id'), 'quota_snapshots', ['id'], unique=False)
    op.create_index(op.f('ix_quota_snapshots_term_id'), 'quota_snapshots', ['term_id'], unique=False)
    op.create_index(op.f('ix_quota_snapshots_course_code'), 'quota_snapshots', ['course_code'], unique=False)
    op.create_index(op.f('ix_quota_snapshots_captured_at'), 'quota_snapshots', ['captured_at'], unique=False)
    op.create_index('idx_quota_code_term_captured', 'quota_snapshots', ['course_code', 'term_id', 'captured_at'], unique=False)

    # 8. course_changes
    op.create_table(
        'course_changes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('change_type', sa.String(length=20), nullable=False),
        sa.Column('term_id', sa.String(length=15), nullable=False),
        sa.Column('dept_kisaadi', sa.String(length=10), nullable=True),
        sa.Column('course_code', sa.String(length=20), nullable=False),
        sa.Column('section', sa.String(length=5), nullable=True),
        sa.Column('timestamp', sa.String(length=50), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('details', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_course_changes_id'), 'course_changes', ['id'], unique=False)
    op.create_index(op.f('ix_course_changes_change_type'), 'course_changes', ['change_type'], unique=False)
    op.create_index(op.f('ix_course_changes_term_id'), 'course_changes', ['term_id'], unique=False)
    op.create_index(op.f('ix_course_changes_dept_kisaadi'), 'course_changes', ['dept_kisaadi'], unique=False)
    op.create_index(op.f('ix_course_changes_course_code'), 'course_changes', ['course_code'], unique=False)
    op.create_index(op.f('ix_course_changes_timestamp'), 'course_changes', ['timestamp'], unique=False)
    op.create_index('idx_changes_code_timestamp', 'course_changes', ['course_code', 'timestamp'], unique=False)

    # 9. sync_state
    op.create_table(
        'sync_state',
        sa.Column('feed_name', sa.String(length=50), nullable=False),
        sa.Column('last_cursor', sa.String(length=100), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('feed_name')
    )


def downgrade() -> None:
    op.drop_table('sync_state')
    op.drop_table('course_changes')
    op.drop_table('quota_snapshots')
    op.drop_table('course_slots')
    op.drop_table('courses')
    op.drop_table('rooms')
    op.drop_table('instructors')
    op.drop_table('departments')
    op.drop_table('terms')
