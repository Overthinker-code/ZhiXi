from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlmodel import Session, select

from app.models import Assignment, Course, Student, StudentTC, Submission, TC
from app.models.student_hub import (
    PracticeRecord,
    StudentAchievement,
    StudentNotification,
    StudentPoints,
    StudyGroup,
    StudyGroupMember,
)
from app.schemas.student_hub import (
    AchievementPublic,
    AchievementsPublic,
    PracticeSummaryPublic,
    PracticeTopicSummary,
    StudentNotificationPublic,
    StudentNotificationsPublic,
    StudyGroupMemberPublic,
    StudyGroupPublic,
    StudyGroupsPublic,
)
from app.services.student_link_service import resolve_student_id


class StudentHubService:
    def get_messages(
        self,
        session: Session,
        user_id: str,
        *,
        limit: int = 50,
    ) -> StudentNotificationsPublic:
        uid = UUID(user_id)
        rows = session.exec(
            select(StudentNotification)
            .where(StudentNotification.user_id == uid)
            .order_by(StudentNotification.created_at.desc())
            .limit(limit)
        ).all()
        data = [self._notification_to_public(row) for row in rows]
        unread = sum(1 for row in rows if not row.is_read)
        return StudentNotificationsPublic(data=data, count=len(data), unread_count=unread)

    def get_groups(self, session: Session, user_id: str) -> StudyGroupsPublic:
        student_id = resolve_student_id(session, user_id)
        if student_id is None:
            return StudyGroupsPublic(data=[], count=0)

        memberships = session.exec(
            select(StudyGroupMember).where(StudyGroupMember.student_id == student_id)
        ).all()
        if not memberships:
            return StudyGroupsPublic(data=[], count=0)

        group_ids = [m.group_id for m in memberships]
        role_by_group = {m.group_id: m.role for m in memberships}
        groups = session.exec(
            select(StudyGroup).where(StudyGroup.id.in_(group_ids))
        ).all()

        tc_ids = [g.tc_id for g in groups if g.tc_id]
        tc_map: dict[UUID, TC] = {}
        course_map: dict[UUID, Course] = {}
        if tc_ids:
            tcs = session.exec(select(TC).where(TC.id.in_(tc_ids))).all()
            tc_map = {tc.id: tc for tc in tcs}
            course_ids = [tc.course_id for tc in tcs]
            if course_ids:
                courses = session.exec(
                    select(Course).where(Course.id.in_(course_ids))
                ).all()
                course_map = {c.id: c for c in courses}

        data: list[StudyGroupPublic] = []
        for group in groups:
            members = session.exec(
                select(StudyGroupMember).where(StudyGroupMember.group_id == group.id)
            ).all()
            student_ids = [m.student_id for m in members]
            students = (
                session.exec(select(Student).where(Student.id.in_(student_ids))).all()
                if student_ids
                else []
            )
            student_name_map = {s.id: s.name for s in students}
            member_public = [
                StudyGroupMemberPublic(
                    student_id=str(m.student_id),
                    student_name=student_name_map.get(m.student_id, "同学"),
                    role=m.role,
                )
                for m in members
            ]
            course_name = None
            if group.tc_id and group.tc_id in tc_map:
                tc = tc_map[group.tc_id]
                course = course_map.get(tc.course_id)
                course_name = course.name if course else None

            data.append(
                StudyGroupPublic(
                    id=str(group.id),
                    name=group.name,
                    description=group.description or "",
                    tc_id=str(group.tc_id) if group.tc_id else None,
                    course_name=course_name,
                    member_count=group.member_count or len(members),
                    my_role=role_by_group.get(group.id, "member"),
                    members=member_public,
                    updated_at=group.updated_at.isoformat() if group.updated_at else "",
                )
            )
        return StudyGroupsPublic(data=data, count=len(data))

    def get_practice_summary(
        self, session: Session, user_id: str
    ) -> PracticeSummaryPublic:
        uid = UUID(user_id)
        student_id = resolve_student_id(session, user_id)

        records = session.exec(
            select(PracticeRecord)
            .where(PracticeRecord.user_id == uid)
            .order_by(PracticeRecord.practiced_at.desc())
        ).all()

        total_sessions = len(records)
        total_questions = sum(r.total_questions for r in records)
        total_correct = sum(r.correct_count for r in records)
        correct_rate = (
            round(total_correct / total_questions * 100, 1) if total_questions else 0.0
        )

        topic_stats: dict[tuple[str, str], dict] = defaultdict(
            lambda: {
                "sessions": 0,
                "total_questions": 0,
                "correct_count": 0,
                "score_sum": 0.0,
                "last_practiced_at": None,
            }
        )
        subjects: set[str] = set()
        for record in records:
            key = (record.subject, record.topic)
            subjects.add(record.subject)
            stats = topic_stats[key]
            stats["sessions"] += 1
            stats["total_questions"] += record.total_questions
            stats["correct_count"] += record.correct_count
            stats["score_sum"] += record.score
            if stats["last_practiced_at"] is None:
                stats["last_practiced_at"] = record.practiced_at

        topics = [
            PracticeTopicSummary(
                subject=subject,
                topic=topic,
                sessions=stats["sessions"],
                total_questions=stats["total_questions"],
                correct_count=stats["correct_count"],
                avg_score=round(stats["score_sum"] / stats["sessions"], 1)
                if stats["sessions"]
                else 0.0,
                last_practiced_at=stats["last_practiced_at"].isoformat()
                if stats["last_practiced_at"]
                else None,
            )
            for (subject, topic), stats in topic_stats.items()
        ]
        topics.sort(key=lambda t: t.last_practiced_at or "", reverse=True)

        assignment_completed = 0
        assignment_total = 0
        if student_id:
            tc_rows = session.exec(
                select(StudentTC.tc_id).where(StudentTC.student_id == student_id)
            ).all()
            course_ids = []
            if tc_rows:
                tcs = session.exec(select(TC).where(TC.id.in_(tc_rows))).all()
                course_ids = list({tc.course_id for tc in tcs})
            if course_ids:
                assignments = session.exec(
                    select(Assignment).where(Assignment.course_id.in_(course_ids))
                ).all()
                assignment_total = len(assignments)
                if assignments:
                    assignment_ids = [a.id for a in assignments]
                    submissions = session.exec(
                        select(Submission).where(
                            Submission.student_id == student_id,
                            Submission.assignment_id.in_(assignment_ids),
                        )
                    ).all()
                    assignment_completed = len(submissions)

        return PracticeSummaryPublic(
            total_sessions=total_sessions,
            total_questions=total_questions,
            correct_rate=correct_rate,
            subjects=sorted(subjects),
            topics=topics,
            assignment_completed=assignment_completed,
            assignment_total=assignment_total,
        )

    def get_achievements(self, session: Session, user_id: str) -> AchievementsPublic:
        uid = UUID(user_id)
        points_row = session.exec(
            select(StudentPoints).where(StudentPoints.user_id == uid)
        ).first()
        total_points = points_row.total_points if points_row else 0
        level = points_row.level if points_row else 1

        rows = session.exec(
            select(StudentAchievement)
            .where(StudentAchievement.user_id == uid)
            .order_by(StudentAchievement.earned_at.desc())
        ).all()
        data = [
            AchievementPublic(
                id=str(row.id),
                code=row.code,
                title=row.title,
                description=row.description or "",
                icon=row.icon or "trophy",
                points_awarded=row.points_awarded,
                earned_at=row.earned_at.isoformat() if row.earned_at else "",
            )
            for row in rows
        ]
        next_level_points = level * 100
        return AchievementsPublic(
            total_points=total_points,
            level=level,
            next_level_points=next_level_points,
            data=data,
            count=len(data),
        )

    def _notification_to_public(self, row: StudentNotification) -> StudentNotificationPublic:
        return StudentNotificationPublic(
            id=str(row.id),
            title=row.title,
            body=row.body or "",
            category=row.category or "system",
            is_read=row.is_read,
            link=row.link,
            created_at=row.created_at.isoformat() if row.created_at else "",
        )


student_hub_service = StudentHubService()
