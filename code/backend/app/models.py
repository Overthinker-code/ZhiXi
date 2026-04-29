#import uuid
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from datetime import datetime
from typing import Optional, List

from enum import Enum

#from sqlmodel import SQLModel, Field, Relationship
#from typing import Optional, List
#from uuid import UUID, uuid4
#from datetime import datetime

# User / Item / Message：使用 app.models 包内定义，避免本文件被 importlib 加载时重复注册表
from app.models.user import User  # noqa: E402
from app.models.item import Item  # noqa: E402
from app.models.message import Message  # noqa: E402


# Generic message
class SimpleMessage(SQLModel):
    message: str


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


class Log(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: Optional[UUID] = Field(foreign_key="user.id")
    action: str = Field(max_length=100, nullable=False)
    details: Optional[str] = None
    object_type: Optional[str] = Field(max_length=50)
    object_id: Optional[UUID] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional[User] = Relationship()


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
    click_number: int = Field(default=0)  # 点击次数，用于热门课程统计


class CourseCreate(CourseBase):
    ud_id: UUID


class CourseUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    course_type: Optional[str] = Field(default=None, max_length=255)
    identifier: Optional[str] = Field(default=None, max_length=255)
    ud_id: Optional[UUID] = None
    click_number: Optional[int] = None


class Course(CourseBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    ud_id: UUID = Field(foreign_key="ud.id")
    ud: UD = Relationship(back_populates="courses")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    tcs: List["TC"] = Relationship(back_populates="course")
    resources: List["Resource"] = Relationship(back_populates="course")


class CoursePublic(CourseBase):
    id: UUID
    ud_id: UUID
    created_at: datetime
    updated_at: datetime
    click_number: int


class CoursesPublic(SQLModel):
    data: List[CoursePublic]
    count: int


# 教学班模型 (Teacher-Course关系)
class TCBase(SQLModel):
    name: Optional[str] = Field(default=None, max_length=255)


class TCCreate(TCBase):
    course_id: UUID = Field(foreign_key="course.id")
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


# ==================== 教育学参数联动新增模型 ====================

class BehaviorSummaryRecord(SQLModel, table=True):
    """课堂行为分析摘要记录（用于联动LLM学情诊断、复习计划、错题归因）"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    student_id: Optional[UUID] = Field(default=None, foreign_key="student.id")
    tc_id: Optional[UUID] = Field(default=None, foreign_key="tc.id")
    course_id: Optional[UUID] = Field(default=None, foreign_key="course.id")
    session_date: datetime = Field(default_factory=datetime.utcnow)
    
    # 课堂整体指标
    avg_lei: float = Field(default=0.0)                    # 学习投入指数
    avg_cognitive_depth: float = Field(default=0.0)        # 认知深度
    mind_wandering_rate: float = Field(default=0.0)        # 走神率
    contagion_index: float = Field(default=0.0)            # 传染指数
    on_task_rate: float = Field(default=0.0)               # 目标行为率
    
    # 布鲁姆认知层次分布（JSON存储）
    bloom_distribution: Optional[str] = None               # JSON: {"remembering":0.2,...}
    cognitive_state_distribution: Optional[str] = None     # JSON: {"shallow_attention":3,...}
    
    # 教学建议存档
    pedagogical_suggestions: Optional[str] = None          # JSON数组
    
    # 个体画像快照（JSON存储）
    student_profiles_snapshot: Optional[str] = None        # JSON: {student_id: {lei,bei,cei,...}}
    
    # 数据来源标识
    source_type: str = Field(default="video_analysis", max_length=50)  # video_analysis / realtime_ws
    analysis_duration_sec: Optional[float] = None
    
    student: Optional["Student"] = Relationship()
    tc: Optional["TC"] = Relationship()
    course: Optional["Course"] = Relationship()


class CourseEngagementRecord(SQLModel, table=True):
    """课程质量评估记录（用于教师课后反思、课程对比）"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    course_id: Optional[UUID] = Field(default=None, foreign_key="course.id")
    tc_id: Optional[UUID] = Field(default=None, foreign_key="tc.id")
    session_date: datetime = Field(default_factory=datetime.utcnow)
    
    # 课堂整体指标
    avg_lei: float = Field(default=0.0)
    avg_cognitive_depth: float = Field(default=0.0)
    mind_wandering_rate: float = Field(default=0.0)
    contagion_index: float = Field(default=0.0)
    
    # 布鲁姆分布
    bloom_distribution: Optional[str] = None
    cognitive_state_distribution: Optional[str] = None
    
    # 时序数据（JSON数组，每分钟一个点）
    lei_timeline: Optional[str] = None                     # JSON: [{"minute":1,"lei":0.82},...]
    
    # 教学建议
    pedagogical_suggestions: Optional[str] = None
    
    # 注意力周期相位
    attention_cycle_phase: Optional[str] = Field(default=None, max_length=20)
    class_attention_trend: Optional[str] = Field(default=None, max_length=20)
    
    # 参与人数
    student_count: int = Field(default=0)
    
    course: "Course" = Relationship()
    tc: "TC" = Relationship()


class StudentBehaviorAlert(SQLModel, table=True):
    """基于CV的真实行为预警记录（替代mock数据）"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    student_id: Optional[UUID] = Field(default=None, foreign_key="student.id")
    tc_id: Optional[UUID] = Field(default=None, foreign_key="tc.id")
    alert_time: datetime = Field(default_factory=datetime.utcnow)
    reason: str
    severity: str = Field(max_length=20)                   # low / medium / high
    alert_type: str = Field(max_length=50)                 # individual_overload / group_contagion / attention_trough / cognitive_shallow
    
    # 触发时的指标快照
    trigger_lei: Optional[float] = None
    trigger_attention_deviation: Optional[float] = None
    trigger_contagion_index: Optional[float] = None
    
    # 是否已处理
    resolved: bool = Field(default=False)
    resolved_at: Optional[datetime] = None
    
    student: Optional["Student"] = Relationship()
    tc: Optional["TC"] = Relationship()


class ResourceBase(SQLModel):
    title: str = Field(max_length=255)
    type: str = Field(max_length=50)  # pdf, ppt, pptx, doc, docx, image
    file_name: str = Field(max_length=255)
    file_path: str = Field(max_length=255)
    file_size: int
    content_type: str = Field(max_length=150)
    course_id: UUID = Field(foreign_key="course.id")


class ResourceCreate(ResourceBase):
    pass


class ResourceUpdate(SQLModel):
    title: Optional[str] = Field(default=None, max_length=255)
    type: Optional[str] = Field(default=None, max_length=50)


class Resource(ResourceBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    upload_time: datetime = Field(default_factory=datetime.utcnow)
    uploader_id: UUID = Field(foreign_key="user.id")

    course: "Course" = Relationship(back_populates="resources")
    uploader: User = Relationship(back_populates="resources")


class ResourcePublic(ResourceBase):
    id: UUID
    upload_time: datetime
    uploader_id: UUID


class ResourcesPublic(SQLModel):
    data: List[ResourcePublic]
    count: int
    

UD.teachers = Relationship(back_populates="ud")
UD.courses = Relationship(back_populates="ud")
UD.students = Relationship(back_populates="ud")
Teacher.tcs = Relationship(back_populates="lecturer")
Course.tcs = Relationship(back_populates="course")
TC.course_plans = Relationship(back_populates="tc")
TC.videos = Relationship(back_populates="tc")
TC.student_relations = Relationship(back_populates="tc")
Student.tc_relations = Relationship(back_populates="student")



