from typing import Any

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import User, UserCreate, UserUpdate


def create_user(*, session: Session, user_create: UserCreate) -> User:
    username = (user_create.username or user_create.email.split("@", 1)[0]).strip()
    db_obj = User.model_validate(
        user_create,
        update={
            "hashed_password": get_password_hash(user_create.password),
            "username": username,
        },
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    # 终局修复：邮箱去空格且大小写不敏感，避免“ student@example.com ”等输入导致登录失败
    normalized = (email or "").strip().casefold()
    # 先尝试精确匹配，再回退到大小写不敏感匹配，兼容历史数据
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    if session_user:
        return session_user
    # 回退：遍历匹配（用户量小，性能可接受；如量大可改为 ilike）
    all_users = session.exec(select(User)).all()
    for u in all_users:
        if (u.email or "").strip().casefold() == normalized:
            return u
    return None


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    # 前端已 trim，这里再做一次防御
    email = (email or "").strip()
    password = (password or "").strip()
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user
