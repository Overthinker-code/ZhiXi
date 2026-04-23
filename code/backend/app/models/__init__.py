"""Models package."""

from app.models.base import Base
from app.models.chat import Chat
from app.models.chat_feedback import ChatFeedback
from app.models.chat_artifact import ChatArtifact
from app.models.ai_usage_log import AIUsageLog
from app.models.item import Item
from app.models.chat_thread import ChatThread
from app.models.user import User
from app.models.user_memory_profile import UserMemoryProfile
from app.models.message import Message
from app.core.enums import MessageStatus, MessageType

# Re-export from schemas
from app.schemas.item import ItemCreate, ItemUpdate
from app.schemas.user import UserCreate, UserUpdate, UsersPublic, UserUpdateMe, UserRegister, NewPassword, UserPublic, UpdatePassword
from app.schemas.token import Token, TokenPayload
from app.schemas.ud import UDBase,UDCreate,UDPublic,UDPublicSingle,UDUpdate
from app.schemas.teachers import TeacherBase,TeacherCreate,TeacherPublic,TeachersPublic,TeacherUpdate
from app.schemas.course import CourseCreate, CourseUpdate, CoursePublic, CoursesPublic
from app.schemas.tc import TCCreate, TCUpdate, TCPublic, TCsPublic
from app.schemas.videos import VideoBase, VideoCreate, VideoPublic, VideosPublic,VideoUpdate
from app.schemas.course_plans import CoursePlanBase,CoursePlanCreate,CoursePlanPublic,CoursePlansPublic,CoursePlanUpdate
from app.schemas.students import StudentBase,StudentCreate,StudentInDBBase,StudentPublic,StudentsPublic,StudentUpdate

# 根目录 app/models.py 中的业务表（教育/视频等），经 business_tables 只加载一次
from app.models.business_tables import (
    Alert,
    Assignment,
    ChatLog,
    Course,
    CoursePlan,
    HelpDocument,
    LearningActivity,
    Log,
    Resource,
    ResourceCreate,
    ResourceUpdate,
    ResourcePublic,
    ResourcesPublic,
    Student,
    StudentTC,
    Submission,
    TC,
    Teacher,
    UD,
    Video,
)

__all__ = [
    "Base",
    "Chat",
    "ChatFeedback",
    "ChatArtifact",
    "AIUsageLog",
    "ChatThread",
    "Item",
    "ItemCreate",
    "ItemUpdate",
    "User",
    "UserMemoryProfile",
    "UserCreate",
    "UserUpdate",
    "MessageStatus",
    "MessageType",
    "Token",
    "TokenPayload",
    "Message",
    "NewPassword",
    "UserPublic",
    "Alert",
    "Assignment",
    "ChatLog",
    "Course",
    "CoursePlan",
    "HelpDocument",
    "LearningActivity",
    "Log",
    "Resource",
    "ResourceCreate",
    "ResourceUpdate",
    "ResourcePublic",
    "ResourcesPublic",
    "Student",
    "StudentTC",
    "Submission",
    "TC",
    "Teacher",
    "UD",
    "Video",
]
