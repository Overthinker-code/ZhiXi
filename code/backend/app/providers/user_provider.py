from typing import Optional
from sqlalchemy.orm import Session

from app.providers.base_provider import BaseProvider
from app.models import User
from app.schemas.user import UserCreate, UserUpdate

class UserProvider(BaseProvider[User, UserCreate, UserUpdate]):
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def is_active(self, user: User) -> bool:
        return user.is_active

    def is_superuser(self, user: User) -> bool:
        return user.is_superuser

user_provider = UserProvider(User) 