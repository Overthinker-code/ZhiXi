from __future__ import annotations

from sqlmodel import Session, select

from app.core.db import engine
from app.models.user import User
from app.services.user_memory_profile_service import user_memory_profile_service


def main() -> int:
    refreshed = 0
    with Session(engine) as session:
        users = session.exec(select(User)).all()
        for user in users:
            result = user_memory_profile_service.refresh_profile(user.id)
            if result.get("status") == "success":
                refreshed += 1
    print(f"memory profiles refreshed: {refreshed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
