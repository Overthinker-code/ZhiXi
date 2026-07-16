"""Add student hub tables: notifications, groups, practice, achievements."""

from alembic import op
import sqlalchemy as sa


revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def _create_table_if_missing(inspector, name: str, create_fn) -> None:
    if not inspector.has_table(name):
        create_fn()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    _create_table_if_missing(
        inspector,
        "student_notification",
        lambda: op.create_table(
            "student_notification",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("body", sa.String(length=2000), nullable=False),
            sa.Column("category", sa.String(length=50), nullable=False),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("link", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        ),
    )

    _create_table_if_missing(
        inspector,
        "study_group",
        lambda: op.create_table(
            "study_group",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.String(length=1000), nullable=False),
            sa.Column("tc_id", sa.Uuid(), nullable=True),
            sa.Column("owner_student_id", sa.Uuid(), nullable=True),
            sa.Column("member_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["tc_id"], ["tc.id"]),
            sa.ForeignKeyConstraint(["owner_student_id"], ["student.id"]),
            sa.PrimaryKeyConstraint("id"),
        ),
    )

    _create_table_if_missing(
        inspector,
        "study_group_member",
        lambda: op.create_table(
            "study_group_member",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("group_id", sa.Uuid(), nullable=False),
            sa.Column("student_id", sa.Uuid(), nullable=False),
            sa.Column("role", sa.String(length=20), nullable=False),
            sa.Column("joined_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["group_id"], ["study_group.id"]),
            sa.ForeignKeyConstraint(["student_id"], ["student.id"]),
            sa.PrimaryKeyConstraint("id"),
        ),
    )

    _create_table_if_missing(
        inspector,
        "practice_record",
        lambda: op.create_table(
            "practice_record",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("student_id", sa.Uuid(), nullable=True),
            sa.Column("subject", sa.String(length=120), nullable=False),
            sa.Column("topic", sa.String(length=120), nullable=False),
            sa.Column("total_questions", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("practiced_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["student_id"], ["student.id"]),
            sa.PrimaryKeyConstraint("id"),
        ),
    )

    _create_table_if_missing(
        inspector,
        "student_achievement",
        lambda: op.create_table(
            "student_achievement",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("code", sa.String(length=80), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.String(length=500), nullable=False),
            sa.Column("icon", sa.String(length=50), nullable=False),
            sa.Column("points_awarded", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("earned_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        ),
    )

    _create_table_if_missing(
        inspector,
        "student_points",
        lambda: op.create_table(
            "student_points",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("total_points", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id"),
        ),
    )

    inspector = sa.inspect(bind)
    index_specs = [
        ("student_notification", "ix_student_notification_user_id", ["user_id"]),
        ("study_group", "ix_study_group_tc_id", ["tc_id"]),
        ("study_group_member", "ix_study_group_member_group_id", ["group_id"]),
        ("study_group_member", "ix_study_group_member_student_id", ["student_id"]),
        ("practice_record", "ix_practice_record_user_id", ["user_id"]),
        ("practice_record", "ix_practice_record_student_id", ["student_id"]),
        ("student_achievement", "ix_student_achievement_user_id", ["user_id"]),
        ("student_points", "ix_student_points_user_id", ["user_id"]),
    ]
    for table, index_name, columns in index_specs:
        if inspector.has_table(table):
            existing = {idx["name"] for idx in inspector.get_indexes(table)}
            if index_name not in existing:
                op.create_index(index_name, table, columns, unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    tables = [
        "student_points",
        "student_achievement",
        "practice_record",
        "study_group_member",
        "study_group",
        "student_notification",
    ]
    for table in tables:
        if inspector.has_table(table):
            for idx in inspector.get_indexes(table):
                op.drop_index(idx["name"], table_name=table)
            op.drop_table(table)
