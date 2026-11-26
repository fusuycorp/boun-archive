"""add course_catalog, course enrichment columns, and widen course_changes

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-26 12:40:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect as sa_inspect

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "course_catalog" not in existing_tables:
        op.create_table(
            "course_catalog",
            sa.Column("course_code", sa.String(length=20), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("en_url", sa.Text(), nullable=True),
            sa.Column("tr_url", sa.Text(), nullable=True),
            sa.Column("en_text", sa.Text(), nullable=True),
            sa.Column("tr_text", sa.Text(), nullable=True),
            sa.Column("canonical_text", sa.Text(), nullable=True),
            sa.Column("content_hash", sa.String(length=64), nullable=True),
            sa.Column("updated_at", sa.String(length=50), nullable=True),
            sa.PrimaryKeyConstraint("course_code"),
        )
        op.create_index("ix_course_catalog_course_code", "course_catalog", ["course_code"], unique=False)

    course_cols = {c["name"] for c in inspector.get_columns("courses")}
    enrichment_cols = [
        ("desc_url", sa.Column("desc_url", sa.Text(), nullable=True)),
        ("syllabus_url", sa.Column("syllabus_url", sa.Text(), nullable=True)),
        ("syllabus_hash", sa.Column("syllabus_hash", sa.String(length=64), nullable=True)),
        ("syllabus_text", sa.Column("syllabus_text", sa.Text(), nullable=True)),
        ("has_syllabus", sa.Column("has_syllabus", sa.Boolean(), server_default=sa.text("false"), nullable=False)),
    ]
    for col_name, col_def in enrichment_cols:
        if col_name not in course_cols:
            op.add_column("courses", col_def)

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE course_changes ALTER COLUMN change_type TYPE VARCHAR(32)")
        op.execute("ALTER TABLE course_changes ALTER COLUMN details TYPE TEXT")
        op.execute("DROP INDEX IF EXISTS idx_courses_lookup")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    course_cols = {c["name"] for c in inspector.get_columns("courses")}
    for col_name in ("has_syllabus", "syllabus_text", "syllabus_hash", "syllabus_url", "desc_url"):
        if col_name in course_cols:
            op.drop_column("courses", col_name)
    if "course_catalog" in set(inspector.get_table_names()):
        op.drop_index("ix_course_catalog_course_code", table_name="course_catalog", if_exists=True)
        op.drop_table("course_catalog")
