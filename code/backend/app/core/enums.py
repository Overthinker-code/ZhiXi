from enum import Enum

class MessageStatus(str, Enum):
    """消息状态枚举"""
    unread = "unread"  # 未读
    read = "read"      # 已读

class MessageType(str, Enum):
    """消息类型枚举"""
    system = "system"      # 系统消息
    personal = "personal"  # 个人消息
    feedback = "feedback"  # 反馈消息 