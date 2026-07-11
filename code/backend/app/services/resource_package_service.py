from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from app.models import Course, GeneratedResourcePackage, Resource
from app.schemas.resource_generation import (
    ResourceGenerationRequest,
    ResourceGenerationResponse,
)
from app.services.resource_generation_service import resource_generation_service


class ResourcePackagePersistenceError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ResourcePackageService:
    """Persist generated files and course resource rows as one operation."""

    def generate(
        self,
        session: Session,
        request: ResourceGenerationRequest,
        *,
        owner_id: UUID,
    ) -> ResourceGenerationResponse:
        if request.course_id and not session.get(Course, request.course_id):
            raise ResourcePackagePersistenceError(
                "COURSE_NOT_FOUND",
                "未找到指定课程，资源包未生成",
            )

        response = resource_generation_service.generate(
            request,
            owner_id=owner_id,
        )
        try:
            package = GeneratedResourcePackage(
                id=response.package_id,
                user_id=owner_id,
                course_id=request.course_id,
                subject=response.subject,
                topic=response.topic,
                source=response.source,
                resource_id=response.resource_id,
                node_id=response.node_id,
                node_label=response.node_label,
                map_type=response.map_type,
                status="completed",
                persistence_status=(
                    "resources_persisted"
                    if request.course_id
                    else "package_persisted"
                ),
                model_profile=response.local_model_profile,
                agent_trace=response.agent_trace,
                quality_notes=response.quality_notes,
                generated_at=response.generated_at,
            )
            session.add(package)
            # There is intentionally no ORM relationship on the legacy Resource
            # model, so establish the FK target before flushing artifact rows.
            session.flush([package])

            resources: list[Resource] = []
            if request.course_id:
                for artifact in response.artifacts:
                    artifact_path = resource_generation_service.resolve_artifact_path(
                        response.package_id,
                        artifact.file_name,
                    )
                    resource = Resource(
                        title=artifact.title,
                        type=artifact.kind,
                        file_name=artifact.file_name,
                        file_path=(
                            f"generated_resources/{response.package_id}/"
                            f"{artifact.file_name}"
                        ),
                        file_size=artifact_path.stat().st_size,
                        content_type=artifact.content_type,
                        course_id=request.course_id,
                        package_id=response.package_id,
                        uploader_id=owner_id,
                    )
                    resources.append(resource)
                    session.add(resource)

            session.flush()
            resource_ids = [resource.id for resource in resources]
            persistence_status = package.persistence_status
            resource_generation_service.update_package_manifest(
                response.package_id,
                {
                    "owner_id": str(owner_id),
                    "persistence_status": persistence_status,
                    "persisted_resource_ids": [str(item) for item in resource_ids],
                },
            )
            session.commit()
            return response.model_copy(
                update={
                    "persistence_status": persistence_status,
                    "persisted_resource_ids": resource_ids,
                }
            )
        except Exception as exc:
            session.rollback()
            resource_generation_service.delete_package(response.package_id)
            if isinstance(exc, ResourcePackagePersistenceError):
                raise
            raise ResourcePackagePersistenceError(
                "RESOURCE_PERSISTENCE_FAILED",
                "资源文件已生成，但入库失败；本次临时文件已清理",
            ) from exc

    def list_recent(
        self,
        session: Session,
        *,
        owner_id: UUID,
        course_id: UUID | None = None,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        query = select(GeneratedResourcePackage).where(
            GeneratedResourcePackage.user_id == owner_id
        )
        if course_id:
            query = query.where(GeneratedResourcePackage.course_id == course_id)
        packages = session.exec(
            query.order_by(GeneratedResourcePackage.generated_at.desc()).limit(limit)
        ).all()

        output: list[dict[str, Any]] = []
        for package in packages:
            try:
                file_payload = resource_generation_service.get_package_payload(
                    package.id
                )
                artifacts = file_payload.get("artifacts", [])
            except (FileNotFoundError, ValueError, OSError):
                artifacts = []
            resource_ids = session.exec(
                select(Resource.id).where(Resource.package_id == package.id)
            ).all()
            output.append(
                {
                    "package_id": package.id,
                    "course_id": str(package.course_id) if package.course_id else "",
                    "resource_id": package.resource_id or "",
                    "node_id": package.node_id or "",
                    "node_label": package.node_label or "",
                    "map_type": package.map_type or "",
                    "source": package.source or "",
                    "subject": package.subject,
                    "topic": package.topic,
                    "generated_at": package.generated_at.isoformat(),
                    "status": package.status,
                    "persistence_status": package.persistence_status,
                    "persisted_resource_ids": [str(item) for item in resource_ids],
                    "local_model_profile": package.model_profile,
                    "agent_trace": package.agent_trace,
                    "quality_notes": package.quality_notes,
                    "artifacts": artifacts,
                }
            )
        return output

    @staticmethod
    def can_access(
        session: Session,
        *,
        package_id: str,
        user_id: UUID,
        is_superuser: bool,
    ) -> bool:
        package = session.get(GeneratedResourcePackage, package_id)
        return bool(
            package
            and (is_superuser or package.user_id == user_id)
        )


resource_package_service = ResourcePackageService()
