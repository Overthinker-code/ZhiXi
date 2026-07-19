from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import Resource, User
from app.tests.utils.user import create_random_user


def test_legacy_generated_media_routes_require_resource_owner(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    db: Session,
) -> None:
    owner = db.exec(select(User).where(User.email == settings.EMAIL_TEST_USER)).one()
    other = create_random_user(db)
    directory = Path(settings.UPLOAD_DIR) / "resources"
    directory.mkdir(parents=True, exist_ok=True)
    image_name = "test-private-generated-image.png"
    video_name = "test-private-generated-video.mp4"
    (directory / image_name).write_bytes(b"image")
    (directory / video_name).write_bytes(b"video")
    own_image = Resource(title="private image", type="image", file_name=image_name, file_path=f"resources/{image_name}", file_size=5, content_type="image/png", uploader_id=owner.id)
    other_video = Resource(title="private video", type="video", file_name=video_name, file_path=f"resources/{video_name}", file_size=5, content_type="video/mp4", uploader_id=other.id)
    db.add(own_image)
    db.add(other_video)
    db.commit()
    try:
        allowed = client.get(f"{settings.API_V1_STR}/ai/generated-images/{image_name}", headers=normal_user_token_headers)
        denied = client.get(f"{settings.API_V1_STR}/ai/generated-artifacts/{video_name}", headers=normal_user_token_headers)
        legacy_without_resource = client.get(f"{settings.API_V1_STR}/ai/generated-images/no-owner.png", headers=normal_user_token_headers)
        assert allowed.status_code == 200
        assert denied.status_code == 404
        assert legacy_without_resource.status_code == 404
    finally:
        db.delete(own_image)
        db.delete(other_video)
        db.delete(other)
        db.commit()
        (directory / image_name).unlink(missing_ok=True)
        (directory / video_name).unlink(missing_ok=True)
