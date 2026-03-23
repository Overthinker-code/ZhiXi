import uuid
from uuid import UUID, uuid4

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel

from datetime import datetime
from typing import Optional, List

from enum import Enum

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=40)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=True)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    full_name: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=True)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=40)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=True)

    sent_messages: List["Message"] = Relationship(
        back_populates="sender",
        sa_relationship_kwargs={"foreign_keys": "[Message.sender_id]"},
    )
    received_messages: List["Message"] = Relationship(
        back_populates="receiver",
        sa_relationship_kwargs={"foreign_keys": "[Message.receiver_id]"},
    )
    logs: List["Log"] = Relationship(back_populates="user")
    videos: List["Video"] = Relationship(back_populates="uploader")


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: Optional[datetime]


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class SimpleMessage(SQLModel):
    message: str


# Enums for message system
class MessageType(str, Enum):
    system = "system"
    reminder = "reminder"
    feedback = "feedback"


class MessageStatus(str, Enum):
    unread = "unread"
    read = "read"


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)


class Message(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    sender_id: Optional[UUID] = Field(foreign_key="user.id")
    receiver_id: Optional[UUID] = Field(foreign_key="user.id")
    content: str = Field(nullable=False)
    type: MessageType = Field(nullable=False)
    status: MessageStatus = Field(default=MessageStatus.unread)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    sender: Optional[User] = Relationship(
        back_populates="sent_messages",
        sa_relationship_kwargs={"foreign_keys": "[Message.sender_id]"},
    )
    receiver: Optional[User] = Relationship(
        back_populates="received_messages",
        sa_relationship_kwargs={"foreign_keys": "[Message.receiver_id]"},
    )

    # 非数据库字段，仅用于API响应
    sender_email: Optional[str] = None
    receiver_email: Optional[str] = None


class Log(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: Optional[UUID] = Field(foreign_key="user.id")
    action: str = Field(max_length=100, nullable=False)
    details: Optional[str] = None
    object_type: Optional[str] = Field(max_length=50)
    object_id: Optional[UUID] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional[User] = Relationship(back_populates="logs")


# ---- 帮助文档相关模型 ----


class DocumentCategory(str, Enum):
    user_guide = "user_guide"  # 用户指南
    admin_guide = "admin_guide"  # 管理员指南
    faq = "faq"  # 常见问题
    other = "other"  # 其他


class HelpDocumentBase(SQLModel):
    title: str = Field(max_length=100)
    description: Optional[str] = Field(default=None)
    category: DocumentCategory = Field(default=DocumentCategory.other)


class HelpDocumentCreate(HelpDocumentBase):
    pass


class HelpDocumentUpdate(SQLModel):
    title: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None)
    category: Optional[DocumentCategory] = None
    is_active: Optional[bool] = None


class HelpDocument(HelpDocumentBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    file_path: str = Field(max_length=255)  # 文件存储路径
    file_name: str = Field(max_length=100)  # 原始文件名
    file_size: int  # 文件大小（字节）
    content_type: str = Field(max_length=150)  # MIME类型
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    uploader_id: UUID = Field(foreign_key="user.id")
    is_active: bool = Field(default=True)  # 是否可见/有效

    uploader: User = Relationship()


class HelpDocumentPublic(HelpDocumentBase):
    id: UUID
    file_name: str
    file_size: int
    content_type: str
    created_at: datetime
    updated_at: Optional[datetime]
    uploader_id: UUID
    is_active: bool


class HelpDocumentsPublic(SQLModel):
    data: List[HelpDocumentPublic]
    count: int


# 从Django项目迁移的模型
# 教育系统模型


# UD模型 (大学-院系)
class UDBase(SQLModel):
    university: str = Field(max_length=255)
    department: str = Field(max_length=255)


class UDCreate(UDBase):
    pass


class UDUpdate(SQLModel):
    university: Optional[str] = Field(default=None, max_length=255)
    department: Optional[str] = Field(default=None, max_length=255)


class UD(UDBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    teachers: List["Teacher"] = Relationship(back_populates="ud")
    courses: List["Course"] = Relationship(back_populates="ud")
    students: List["Student"] = Relationship(back_populates="ud")


class UDPublic(UDBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class UDsPublic(SQLModel):
    data: List[UDPublic]
    count: int


# 教师模型
class TeacherBase(SQLModel):
    name: str = Field(max_length=255)
    identifier: str = Field(max_length=255)


class TeacherCreate(TeacherBase):
    ud_id: UUID


class TeacherUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=255)
    identifier: Optional[str] = Field(default=None, max_length=255)
    ud_id: Optional[UUID] = None


class Teacher(TeacherBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    ud_id: UUID = Field(foreign_key="ud.id")
    ud: UD = Relationship(back_populates="teachers")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    tcs: List["TC"] = Relationship(back_populates="lecturer")


class TeacherPublic(TeacherBase):
    id: UUID
    ud_id: UUID
    created_at: datetime
    updated_at: datetime


class TeachersPublic(SQLModel):
    data: List[TeacherPublic]
    count: int


# 课程模型
class CourseBase(SQLModel):
    name: str = Field(max_length=255)
    description: Optional[str] = None
    course_type: Optional[str] = Field(default=None, max_length=255)
    identifier: str = Field(max_length=255)


class CourseCreate(CourseBase):
    ud_id: UUID


class CourseUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    course_type: Optional[str] = Field(default=None, max_length=255)
    identifier: Optional[str] = Field(default=None, max_length=255)
    ud_id: Optional[UUID] = None


class Course(CourseBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    ud_id: UUID = Field(foreign_key="ud.id")
    ud: UD = Relationship(back_populates="courses")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    tcs: List["TC"] = Relationship(back_populates="course")


class CoursePublic(CourseBase):
    id: UUID
    ud_id: UUID
    created_at: datetime
    updated_at: datetime


class CoursesPublic(SQLModel):
    data: List[CoursePublic]
    count: int


# 教学班模型 (Teacher-Course关系)
class TCBase(SQLModel):
    name: Optional[str] = Field(default=None, max_length=255)


class TCCreate(TCBase):
    course_id: UUID
    lecturer_id: UUID


class TCUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=255)
    course_id: Optional[UUID] = None
    lecturer_id: Optional[UUID] = None


class TC(TCBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    course_id: UUID = Field(foreign_key="course.id")
    lecturer_id: UUID = Field(foreign_key="teacher.id")
    course: Course = Relationship(back_populates="tcs")
    lecturer: Teacher = Relationship(back_populates="tcs")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    course_plans: List["CoursePlan"] = Relationship(back_populates="tc")
    videos: List["Video"] = Relationship(back_populates="tc")
    student_relations: List["StudentTC"] = Relationship(back_populates="tc")


class TCPublic(TCBase):
    id: UUID
    course_id: UUID
    lecturer_id: UUID
    created_at: datetime
    updated_at: datetime
    course_name: Optional[str] = None
    lecturer_name: Optional[str] = None


class TCsPublic(SQLModel):
    data: List[TCPublic]
    count: int


# 课程计划模型
class CoursePlanBase(SQLModel):
    week: int = Field(ge=1, le=20)
    goal: str = Field(max_length=1000)
    key_point: str = Field(max_length=1000)


class CoursePlanCreate(CoursePlanBase):
    tc_id: UUID


class CoursePlanUpdate(SQLModel):
    week: Optional[int] = Field(default=None, ge=1, le=20)
    goal: Optional[str] = Field(default=None, max_length=1000)
    key_point: Optional[str] = Field(default=None, max_length=1000)
    tc_id: Optional[UUID] = None


class CoursePlan(CoursePlanBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tc_id: UUID = Field(foreign_key="tc.id")
    tc: TC = Relationship(back_populates="course_plans")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CoursePlanPublic(CoursePlanBase):
    id: UUID
    tc_id: UUID
    created_at: datetime
    updated_at: datetime


class CoursePlansPublic(SQLModel):
    data: List[CoursePlanPublic]
    count: int


# 学生模型
class StudentBase(SQLModel):
    name: str = Field(max_length=255)
    identifier: str = Field(max_length=255)


class StudentCreate(StudentBase):
    ud_id: UUID
    tc_ids: Optional[List[UUID]] = None


class StudentUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=255)
    identifier: Optional[str] = Field(default=None, max_length=255)
    ud_id: Optional[UUID] = None
    tc_ids: Optional[List[UUID]] = None


class Student(StudentBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    ud_id: UUID = Field(foreign_key="ud.id")
    ud: UD = Relationship(back_populates="students")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    tc_relations: List["StudentTC"] = Relationship(back_populates="student")


class StudentPublic(StudentBase):
    id: UUID
    ud_id: UUID
    created_at: datetime
    updated_at: datetime
    tcs: Optional[List[TCPublic]] = None


class StudentsPublic(SQLModel):
    data: List[StudentPublic]
    count: int


# 学生-教学班关系模型
class StudentTC(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    student_id: UUID = Field(foreign_key="student.id")
    tc_id: UUID = Field(foreign_key="tc.id")
    student: Student = Relationship(back_populates="tc_relations")
    tc: TC = Relationship(back_populates="student_relations")


# 视频模型
class VideoBase(SQLModel):
    title: str = Field(max_length=255)
    file_path: str = Field(max_length=255)
    file_name: str = Field(max_length=255)
    file_size: int
    content_type: str = Field(max_length=100)
    week: Optional[int] = Field(default=None, ge=1, le=20)


class VideoCreate(VideoBase):
    tc_id: UUID
    uploader_id: UUID


class VideoUpdate(SQLModel):
    title: Optional[str] = Field(default=None, max_length=255)
    week: Optional[int] = Field(default=None, ge=1, le=20)
    tc_id: Optional[UUID] = None


class Video(VideoBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tc_id: UUID = Field(foreign_key="tc.id")
    uploader_id: UUID = Field(foreign_key="user.id")
    tc: TC = Relationship(back_populates="videos")
    uploader: User = Relationship(back_populates="videos")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class VideoPublic(VideoBase):
    id: UUID
    tc_id: UUID
    uploader_id: UUID
    created_at: datetime
    updated_at: datetime


class VideosPublic(SQLModel):
    data: List[VideoPublic]
    count: int

class Assignment(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str
    description: Optional[str] = None
    due_date: datetime
    course_id: UUID = Field(foreign_key="course.id")

    course: "Course" = Relationship()
    submissions: List["Submission"] = Relationship(back_populates="assignment")


class Submission(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    assignment_id: UUID = Field(foreign_key="assignment.id")
    student_id: UUID = Field(foreign_key="student.id")
    submit_time: datetime
    score: Optional[float] = None
    file_path: str

    assignment: Assignment = Relationship(back_populates="submissions")
    student: "Student" = Relationship()


class LearningActivity(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    student_id: UUID = Field(foreign_key="student.id")
    timestamp: datetime
    activity_type: str
    content_id: Optional[UUID] = Field(default=None, foreign_key="resource.id")

    student: "Student" = Relationship()
    content: Optional["Resource"] = Relationship()


class ChatLog(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    student_id: UUID = Field(foreign_key="student.id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    query_text: str
    response_text: str

    student: "Student" = Relationship()


class Alert(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    student_id: UUID = Field(foreign_key="student.id")
    alert_time: datetime = Field(default_factory=datetime.utcnow)
    reason: str
    severity: str  

    student: "Student" = Relationship()


class Resource(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str
    type: str  # pdf, video, ppt
    upload_time: datetime = Field(default_factory=datetime.utcnow)
    course_id: UUID = Field(foreign_key="course.id")

    course: "Course" = Relationship()
    

User.videos = Relationship(back_populates="uploader")
UD.teachers = Relationship(back_populates="ud")
UD.courses = Relationship(back_populates="ud")
UD.students = Relationship(back_populates="ud")
Teacher.tcs = Relationship(back_populates="lecturer")
Course.tcs = Relationship(back_populates="course")
TC.course_plans = Relationship(back_populates="tc")
TC.videos = Relationship(back_populates="tc")
TC.student_relations = Relationship(back_populates="tc")
Student.tc_relations = Relationship(back_populates="student")



