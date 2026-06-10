"""Add user_id link on student table."""

from alembic import op
import sqlalchemy as sa


revision = "004_add_student_user_id"
down_revision = "003_add_dashboard_resource_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "student",
        sa.Column("user_id", sa.Uuid(), nullable=True),
    )
    op.create_index("ix_student_user_id", "student", ["user_id"], unique=False)
    op.create_foreign_key(
        "fk_student_user_id_user",
        "student",
        "user",
        ["user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_student_user_id_user", "student", type_="foreignkey")
    op.drop_index("ix_student_user_id", table_name="student")
    op.drop_column("student", "user_id")
