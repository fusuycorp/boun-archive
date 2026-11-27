"""optimize indexes, drop duplicates, and add compact course_code expression indexes

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-27 09:10:00.000000

"""
from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_REDUNDANT_INDEXES: tuple[tuple[str, str, list[str], bool], ...] = (
    ("ix_instructors_id", "instructors", ["id"], False),
    ("ix_instructors_full_name", "instructors", ["full_name"], True),
    ("ix_rooms_id", "rooms", ["id"], False),
    ("ix_rooms_name", "rooms", ["name"], True),
    ("ix_courses_id", "courses", ["id"], False),
    ("ix_courses_term_id", "courses", ["term_id"], False),
    ("ix_courses_dept_kisaadi", "courses", ["dept_kisaadi"], False),
    ("ix_courses_instructor_id", "courses", ["instructor_id"], False),
    ("ix_course_slots_id", "course_slots", ["id"], False),
    ("ix_course_slots_course_id", "course_slots", ["course_id"], False),
    ("ix_course_slots_day_code", "course_slots", ["day_code"], False),
    ("ix_quota_snapshots_id", "quota_snapshots", ["id"], False),
    ("ix_quota_snapshots_course_code", "quota_snapshots", ["course_code"], False),
    ("idx_quota_course_captured", "quota_snapshots", ["course_code", "captured_at"], False),
    ("ix_course_changes_id", "course_changes", ["id"], False),
    ("ix_course_changes_course_code", "course_changes", ["course_code"], False),
    ("ix_course_catalog_course_code", "course_catalog", ["course_code"], False),
)


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Add missing composite indexes for hot department, instructor, and heatmap queries
    op.create_index("idx_courses_dept_term", "courses", ["dept_kisaadi", "term_id"], unique=False, if_not_exists=True)
    op.create_index("idx_courses_instructor_term", "courses", ["instructor_id", "term_id"], unique=False, if_not_exists=True)
    op.create_index("idx_slots_day_hour", "course_slots", ["day_code", "slot_hour"], unique=False, if_not_exists=True)

    # 2. Drop redundant PK/UNIQUE and strict-prefix duplicate indexes
    for index_name, table_name, _, _ in _REDUNDANT_INDEXES:
        op.drop_index(index_name, table_name=table_name, if_exists=True)

    # 3. Add PostgreSQL functional indexes for space-insensitive course_code lookups
    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_courses_code_compact "
            "ON courses (upper(replace(course_code, ' ', '')))"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_quota_code_compact "
            "ON quota_snapshots (upper(replace(course_code, ' ', '')), term_id, captured_at)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_changes_code_compact "
            "ON course_changes (upper(replace(course_code, ' ', '')), timestamp)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_course_catalog_code_compact "
            "ON course_catalog (upper(replace(course_code, ' ', '')))"
        )


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS idx_course_catalog_code_compact")
        op.execute("DROP INDEX IF EXISTS idx_changes_code_compact")
        op.execute("DROP INDEX IF EXISTS idx_quota_code_compact")
        op.execute("DROP INDEX IF EXISTS idx_courses_code_compact")

    for index_name, table_name, columns, is_unique in _REDUNDANT_INDEXES:
        op.create_index(index_name, table_name, columns, unique=is_unique, if_not_exists=True)

    op.drop_index("idx_slots_day_hour", table_name="course_slots", if_exists=True)
    op.drop_index("idx_courses_instructor_term", table_name="courses", if_exists=True)
    op.drop_index("idx_courses_dept_term", table_name="courses", if_exists=True)
