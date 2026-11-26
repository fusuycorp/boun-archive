
from sqlalchemy import func, literal_column
from sqlalchemy.orm import Session

from . import models


class MacroEngine:
    """
    High-performance engine for university-wide historical analytics.
    Uses SQLAlchemy for direct DB aggregations.
    """

    @staticmethod
    def get_department_evolution(db: Session):
        # Count of courses per department per academic year (extracted from term_id prefix)
        year_expr = func.substr(models.Course.term_id, literal_column("1"), literal_column("4"))
        results = (
            db.query(
                models.Course.dept_kisaadi,
                year_expr.label("year"),
                func.count(models.Course.id).label("count"),
            )
            .filter(models.Course.term_id.isnot(None))
            .group_by(models.Course.dept_kisaadi, year_expr)
            .all()
        )

        data: dict[str, dict[str, int]] = {}
        all_years = sorted({r.year for r in results if r.year})

        for r in results:
            if not r.year:
                continue
            if r.dept_kisaadi not in data:
                data[r.dept_kisaadi] = {y: 0 for y in all_years}
            data[r.dept_kisaadi][r.year] = r.count

        return {
            "years": all_years,
            "departments": data,
        }

    @staticmethod
    def get_scheduling_heatmap(db: Session, decade: int | None = None):
        query = db.query(
            models.CourseSlot.day_code,
            models.CourseSlot.slot_hour,
            func.count(models.CourseSlot.id).label("count"),
        ).join(models.Course)

        if decade is not None:
            start_year = f"{int(decade):04d}"
            end_year_bound = f"{int(decade) + 10:04d}"
            query = query.filter(
                models.Course.term_id.isnot(None),
                func.substr(models.Course.term_id, literal_column("1"), literal_column("4")) >= start_year,
                func.substr(models.Course.term_id, literal_column("1"), literal_column("4")) < end_year_bound,
            )

        results = query.group_by(
            models.CourseSlot.day_code,
            models.CourseSlot.slot_hour,
        ).all()

        return [r._asdict() for r in results]
