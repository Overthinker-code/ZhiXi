from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import Resource, ResourceFavorite, User, UserResourceConfig


def test_resource_library_favorite_top_and_soft_remove(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    db: Session,
) -> None:
    user = db.exec(select(User).where(User.email == settings.EMAIL_TEST_USER)).one()
    resource = Resource(
        title="Phase 3 resource library test",
        type="lecture_markdown",
        knowledge_point="transaction",
        source="agent",
        uploader_id=user.id,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)

    base_url = f"{settings.API_V1_STR}/education/resources/{resource.id}"
    try:
        response = client.put(
            f"{base_url}/favorite",
            headers=normal_user_token_headers,
            json={"favorite": True},
        )
        assert response.status_code == 200
        assert response.json()["favorite"] is True

        response = client.put(
            f"{base_url}/config",
            headers=normal_user_token_headers,
            json={"is_top": True},
        )
        assert response.status_code == 200
        assert response.json()["top"] is True

        listing = client.get(
            f"{settings.API_V1_STR}/education/resources/",
            headers=normal_user_token_headers,
            params={"owned_only": True},
        )
        item = next(entry for entry in listing.json()["data"] if entry["id"] == str(resource.id))
        assert item["favorite"] is True
        assert item["top"] is True

        removed = client.delete(
            f"{base_url}/library",
            headers=normal_user_token_headers,
        )
        assert removed.status_code == 200
        assert removed.json() == {
            "resource_id": str(resource.id),
            "removed": True,
            "physical_deleted": False,
        }
        listing = client.get(
            f"{settings.API_V1_STR}/education/resources/",
            headers=normal_user_token_headers,
            params={"owned_only": True},
        )
        assert str(resource.id) not in {entry["id"] for entry in listing.json()["data"]}
        db.expire_all()
        assert db.get(Resource, resource.id) is not None
    finally:
        for favorite in db.exec(
            select(ResourceFavorite).where(ResourceFavorite.resource_id == resource.id)
        ).all():
            db.delete(favorite)
        for config in db.exec(
            select(UserResourceConfig).where(UserResourceConfig.resource_id == resource.id)
        ).all():
            db.delete(config)
        stored = db.get(Resource, resource.id)
        if stored:
            db.delete(stored)
        db.commit()
