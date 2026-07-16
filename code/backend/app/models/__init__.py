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
from app.models.conversation_message import ConversationMessage
from app.models.learning_context import LearningContext
from app.models.agent_task import AgentTask
from app.models.learning_task import LearningTask
from app.models.knowledge_graph import KnowledgeGraph
from app.models.resource_library import ResourceFavorite, UserResourceConfig
from app.models.external_resource import ExternalResource
from app.models.resource_recommendation import PersonalizedResourceRecommendation
from app.models.quiz import Question, QuizAttempt, WrongQuestion
from app.models.learning_path import LearningPath
from app.models.generated_resource_package import GeneratedResourcePackage
from app.models.resource_run import (
    CourseKnowledgeEdge,
    CourseKnowledgeNode,
    CourseKnowledgeNodeAction,
    ResourceGenerationRun,
    ResourceGenerationStep,
    ResourceKnowledgeLink,
)
from app.models.learning_evidence import (
    LearningEvidence,
    ProfileUpdateEvent,
    LearningPathUpdateEvent,
)
from app.models.student_hub import (
    PracticeRecord,
    StudentAchievement,
    StudentNotification,
    StudentPoints,
    StudyGroup,
    StudyGroupMember,
)
from app.models.message import Message
from app.core.enums import MessageStatus, MessageType

# Re-export from schemas
from app.schemas.user import (
    UserCreate,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
    UpdatePassword,
)
from app.schemas.token import Token, TokenPayload
from app.schemas.ud import UDCreate, UDPublic, UDUpdate
from app.schemas.teachers import (
    TeacherCreate,
    TeacherPublic,
    TeachersPublic,
    TeacherUpdate,
)
from app.schemas.course import CourseCreate, CourseUpdate, CoursePublic, CoursesPublic
from app.schemas.tc import TCCreate, TCUpdate, TCPublic, TCsPublic
from app.schemas.videos import VideoPublic, VideosPublic, VideoUpdate
from app.schemas.course_plans import (
    CoursePlanCreate,
    CoursePlanPublic,
    CoursePlansPublic,
    CoursePlanUpdate,
)
from app.schemas.students import (
    StudentCreate,
    StudentPublic,
    StudentsPublic,
    StudentUpdate,
)

# 根目录 app/models.py 中的业务表（教育/视频等），经 business_tables 只加载一次
from app.models.business_tables import (
    Alert,
    Assignment,
    BehaviorSummaryRecord,
    ChatLog,
    Course,
    CourseEngagementRecord,
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
    StudentBehaviorAlert,
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
    "User",
    "UserMemoryProfile",
    "ConversationMessage",
    "LearningContext",
    "AgentTask",
    "LearningTask",
    "KnowledgeGraph",
    "LearningPath",
    "GeneratedResourcePackage",
    "ResourceFavorite",
    "UserResourceConfig",
    "ExternalResource",
    "PersonalizedResourceRecommendation",
    "Question",
    "QuizAttempt",
    "WrongQuestion",
    "CourseKnowledgeEdge",
    "CourseKnowledgeNode",
    "CourseKnowledgeNodeAction",
    "ResourceGenerationRun",
    "ResourceGenerationStep",
    "ResourceKnowledgeLink",
    "LearningEvidence",
    "ProfileUpdateEvent",
    "LearningPathUpdateEvent",
    "PracticeRecord",
    "StudentAchievement",
    "StudentNotification",
    "StudentPoints",
    "StudyGroup",
    "StudyGroupMember",
    "UserCreate",
    "UserPublic",
    "UserRegister",
    "UserUpdate",
    "UserUpdateMe",
    "UsersPublic",
    "UpdatePassword",
    "MessageStatus",
    "MessageType",
    "Token",
    "TokenPayload",
    "Message",
    "UDCreate",
    "UDPublic",
    "UDUpdate",
    "TeacherCreate",
    "TeacherPublic",
    "TeachersPublic",
    "TeacherUpdate",
    "CourseCreate",
    "CoursePublic",
    "CoursesPublic",
    "CourseUpdate",
    "TCCreate",
    "TCPublic",
    "TCsPublic",
    "TCUpdate",
    "VideoPublic",
    "VideosPublic",
    "VideoUpdate",
    "CoursePlanCreate",
    "CoursePlanPublic",
    "CoursePlansPublic",
    "CoursePlanUpdate",
    "StudentCreate",
    "StudentPublic",
    "StudentsPublic",
    "StudentUpdate",
    "Alert",
    "Assignment",
    "BehaviorSummaryRecord",
    "ChatLog",
    "Course",
    "CourseEngagementRecord",
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
    "StudentBehaviorAlert",
    "StudentTC",
    "Submission",
    "TC",
    "Teacher",
    "UD",
    "Video",
]
