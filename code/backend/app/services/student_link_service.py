"""Resolve login User to education-domain Student."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from app.models import Student


def resolve_student_id(session: Session, user_id: str | UUID | None) -> UUID | None:
    if not user_id:
        return None
    try:
        uid = UUID(str(user_id))
    except ValueError:
        return None
    student = session.exec(select(Student).where(Student.user_id == uid)).first()
    return student.id if student else None


def resolve_student_or_user_id(session: Session, user_id: str | UUID | None) -> UUID | None:
    """Prefer linked Student.id; fall back to User.id for legacy rows."""
    linked = resolve_student_id(session, user_id)
    if linked is not None:
        return linked
    try:
        return UUID(str(user_id))
    except ValueError:
        return None
