from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import select

from app.api.deps import SessionDep, get_current_user
from app.models import Message, MessageStatus, MessageType, User
from app import crud

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("/", response_model=Message)
def create_message(
    *,
    session: SessionDep,
    message_data: dict,
    current_user: User = Depends(get_current_user),
):
    """
    创建消息
    普通用户只能向管理员发送消息
    管理员可以向任何用户发送消息
    可通过receiver_id(UUID)或receiver_email(邮箱)指定接收者
    """
    receiver_id = message_data.get("receiver_id")
    receiver_email = message_data.get("receiver_email")
    content = message_data.get("content")
    message_type = message_data.get("type", MessageType.feedback)

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="消息内容不能为空",
        )

    if not receiver_id and not receiver_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="接收者ID或邮箱必须提供一项",
        )

    # 通过ID或邮箱查找接收者
    receiver = None
    if receiver_id:
        receiver = session.get(User, receiver_id)
    elif receiver_email:
        receiver = crud.get_user_by_email(session=session, email=receiver_email)

    # 确保当前用户存在于数据库中
    sender = session.get(User, current_user.id)
    if not sender:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="发送者用户不存在或会话已过期",
        )

    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="接收者不存在",
        )

    # 检查权限
    if not sender.is_superuser and not receiver.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="普通用户只能向管理员发送消息",
        )

    # 创建消息
    message = Message(
        sender_id=sender.id,
        receiver_id=receiver.id,
        content=content,
        type=message_type,
        status=MessageStatus.unread,
    )

    session.add(message)
    session.commit()
    session.refresh(message)

    return message


@router.get("/", response_model=List[Message])
def get_messages(
    *,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
    unread_only: bool = False,
    sent: bool = False,
):
    """
    获取当前用户的消息
    可以选择只获取未读消息或发送的消息
    """
    # 确保当前用户存在于数据库中
    user = session.get(User, current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户不存在或会话已过期",
        )

    if sent:
        # 获取发送的消息
        query = select(Message).where(Message.sender_id == user.id)
    else:
        # 获取接收的消息
        query = select(Message).where(Message.receiver_id == user.id)

    if unread_only:
        query = query.where(Message.status == MessageStatus.unread)

    # 按时间倒序排列
    query = query.order_by(Message.created_at.desc())

    messages = session.exec(query).all()

    # 填充发件人和收件人的邮箱信息
    for message in messages:
        if message.sender_id:
            sender = session.get(User, message.sender_id)
            message.sender_email = sender.email if sender else None

        if message.receiver_id:
            receiver = session.get(User, message.receiver_id)
            message.receiver_email = receiver.email if receiver else None

    return messages


@router.get("/{message_id}", response_model=Message)
def get_message(
    *,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
    message_id: UUID,
):
    """获取单个消息详情"""
    # 确保当前用户存在于数据库中
    user = session.get(User, current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户不存在或会话已过期",
        )

    message = session.get(Message, message_id)

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在",
        )

    # 检查权限
    if message.receiver_id != user.id and message.sender_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看此消息",
        )

    # 如果当前用户是接收者且消息未读，则标记为已读
    if message.receiver_id == user.id and message.status == MessageStatus.unread:
        message.status = MessageStatus.read
        session.add(message)
        session.commit()
        session.refresh(message)

    # 填充发件人和收件人的邮箱信息
    if message.sender_id:
        sender = session.get(User, message.sender_id)
        message.sender_email = sender.email if sender else None

    if message.receiver_id:
        receiver = session.get(User, message.receiver_id)
        message.receiver_email = receiver.email if receiver else None

    return message


@router.put("/{message_id}/read", response_model=Message)
def mark_message_as_read(
    *,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
    message_id: UUID,
):
    """将消息标记为已读"""
    # 确保当前用户存在于数据库中
    user = session.get(User, current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户不存在或会话已过期",
        )

    message = session.get(Message, message_id)

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在",
        )

    # 检查权限
    if message.receiver_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权更新此消息状态",
        )

    # 标记为已读
    message.status = MessageStatus.read
    session.add(message)
    session.commit()
    session.refresh(message)

    return message


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    *,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
    message_id: UUID,
):
    """删除消息（仅管理员或消息的发送者可以删除）"""
    # 确保当前用户存在于数据库中
    user = session.get(User, current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户不存在或会话已过期",
        )

    message = session.get(Message, message_id)

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在",
        )

    # 检查权限
    if not user.is_superuser and message.sender_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除此消息",
        )

    session.delete(message)
    session.commit()
