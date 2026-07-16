#!/usr/bin/env python3
"""Conservatively repair historical resource course scope.

The script is dry-run by default.  It only accepts an exact, globally unique
match to a trusted curriculum concept node.  Generated/private graph nodes and
substring similarity are deliberately excluded.  Completed generated packages
whose declared generation domain conflicts with the matched curriculum are
reported for quarantine/regeneration instead of being relabelled.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import UUID

from sqlmodel import Session, select

from app.core.db import engine
from app.models import (
    Course,
    CourseKnowledgeNode,
    GeneratedResourcePackage,
    Resource,
    ResourceGenerationRun,
    ResourceKnowledgeLink,
    UserResourceConfig,
)
from app.services.learning_report_service import learning_report_service
from app.services.resource_subject_service import GENERIC_SUBJECTS, resolve_resource_subject


POLICY_VERSION = "resource-course-scope-v1"


@dataclass(frozen=True)
class CurriculumMatch:
    course_id: UUID
    course_name: str
    node_id: UUID
    node_label: str
    normalized_label: str


@dataclass(frozen=True)
class Resolution:
    status: str
    match: CurriculumMatch | None
    terms: tuple[str, ...]
    candidate_node_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScopeDeclarations:
    package_subject: str = ""
    requested_subject: str = ""
    model_domain: str = ""


def quarantine_transition(
    *,
    enabled: bool,
    config_exists: bool,
    current_hidden: bool | None,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Plan a reversible library quarantine without deleting the resource."""
    if not enabled or current_hidden is True:
        return None
    return (
        {"exists": config_exists, "is_hidden": current_hidden},
        {"exists": True, "is_hidden": True},
    )


def _normalize(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        return learning_report_service.normalize_knowledge_point(raw)
    except ValueError:
        return ""


def _normalized_domain(value: object) -> str:
    """Normalize an explicit domain label, allowing only a trailing `课程`."""
    raw = str(value or "").strip()
    if raw.endswith("课程"):
        raw = raw[:-2].strip()
    return _normalize(raw)


class CurriculumIndex:
    """Exact-match index over trusted, public curriculum concepts only."""

    def __init__(self, *, courses: Iterable[Course], nodes: Iterable[CourseKnowledgeNode]):
        self.course_names: dict[UUID, str] = {course.id: course.name for course in courses}
        self.course_ids_by_name: dict[str, set[UUID]] = defaultdict(set)
        for course_id, name in self.course_names.items():
            normalized = _normalize(name)
            if normalized:
                self.course_ids_by_name[normalized].add(course_id)

        self.by_term: dict[str, dict[UUID, CurriculumMatch]] = defaultdict(dict)
        self.node_ids: set[UUID] = set()
        trusted_sources = learning_report_service.TRUSTED_GRAPH_SOURCES
        for node in nodes:
            source = str((node.attributes or {}).get("source") or "")
            if (
                node.map_type != "knowledge"
                or node.node_type != "concept"
                or source not in trusted_sources
                or node.course_id not in self.course_names
            ):
                continue
            normalized = _normalize(node.label)
            if not normalized:
                continue
            match = CurriculumMatch(
                course_id=node.course_id,
                course_name=self.course_names[node.course_id],
                node_id=node.id,
                node_label=node.label,
                normalized_label=normalized,
            )
            self.by_term[normalized][node.id] = match
            self.by_term[str(node.id).lower()][node.id] = match
            self.node_ids.add(node.id)

    def resolve(self, terms: Iterable[object]) -> Resolution:
        normalized_terms: list[str] = []
        candidates: dict[UUID, CurriculumMatch] = {}
        for term in terms:
            raw = str(term or "").strip()
            if not raw:
                continue
            normalized_terms.append(raw)
            key = str(term).strip().lower() if _looks_like_uuid(term) else _normalize(term)
            for node_id, match in self.by_term.get(key, {}).items():
                candidates[node_id] = match
        if not candidates:
            return Resolution("unresolved", None, tuple(dict.fromkeys(normalized_terms)))
        if len(candidates) != 1:
            return Resolution(
                "ambiguous",
                None,
                tuple(dict.fromkeys(normalized_terms)),
                tuple(sorted(str(node_id) for node_id in candidates)),
            )
        return Resolution(
            "unique",
            next(iter(candidates.values())),
            tuple(dict.fromkeys(normalized_terms)),
        )

    def exact_course_id(self, value: object, *, domain: bool = False) -> UUID | None:
        normalized = _normalized_domain(value) if domain else _normalize(value)
        matches = self.course_ids_by_name.get(normalized, set())
        return next(iter(matches)) if len(matches) == 1 else None


def _looks_like_uuid(value: object) -> bool:
    try:
        UUID(str(value or ""))
        return True
    except (TypeError, ValueError, AttributeError):
        return False


def declared_scope_conflict(
    *,
    index: CurriculumIndex,
    target_course_id: UUID,
    declarations: ScopeDeclarations,
) -> dict[str, str]:
    """Return exact declarations that prove content was generated for another course."""
    conflicts: dict[str, str] = {}
    checks = {
        "package_subject": (declarations.package_subject, False),
        "requested_subject": (declarations.requested_subject, False),
        "model_domain": (declarations.model_domain, True),
    }
    for field, (value, is_domain) in checks.items():
        raw = str(value or "").strip()
        if not raw or raw in GENERIC_SUBJECTS:
            continue
        declared_course_id = index.exact_course_id(raw, domain=is_domain)
        if declared_course_id is not None and declared_course_id != target_course_id:
            conflicts[field] = raw
    return conflicts


def should_repair_subject(
    *,
    index: CurriculumIndex,
    subject: str | None,
    target_course_id: UUID,
) -> bool:
    raw = str(subject or "").strip()
    if raw in GENERIC_SUBJECTS:
        return True
    declared_course_id = index.exact_course_id(raw)
    return declared_course_id is not None and declared_course_id != target_course_id


def _change(
    *,
    entity: str,
    entity_id: object,
    before: dict[str, Any],
    after: dict[str, Any],
    match: CurriculumMatch,
    reason: str,
) -> dict[str, Any]:
    return {
        "entity": entity,
        "id": str(entity_id),
        "before": before,
        "after": after,
        "reason": reason,
        "evidence": {
            "course_id": str(match.course_id),
            "course_name": match.course_name,
            "node_id": str(match.node_id),
            "node_label": match.node_label,
            "match_policy": "exact_normalized_unique_trusted_curriculum_node",
        },
    }


def _package_declarations(
    package: GeneratedResourcePackage | None,
    runs: list[ResourceGenerationRun],
) -> ScopeDeclarations:
    requested_subject = ""
    for run in runs:
        requested_subject = str((run.requested or {}).get("subject") or "").strip()
        if requested_subject:
            break
    model_domain = ""
    if package is not None:
        model_domain = str((package.model_profile or {}).get("domain") or "").strip()
    return ScopeDeclarations(
        package_subject=str(package.subject if package else ""),
        requested_subject=requested_subject,
        model_domain=model_domain,
    )


def backfill(
    session: Session,
    *,
    apply: bool,
    quarantine_conflicts: bool = False,
) -> dict[str, Any]:
    if quarantine_conflicts and not apply:
        raise ValueError("quarantine_conflicts_requires_apply")

    courses = session.exec(select(Course)).all()
    nodes = session.exec(select(CourseKnowledgeNode)).all()
    resources = session.exec(select(Resource).order_by(Resource.upload_time, Resource.id)).all()
    packages = session.exec(select(GeneratedResourcePackage)).all()
    links = session.exec(select(ResourceKnowledgeLink)).all()
    runs = session.exec(select(ResourceGenerationRun)).all()
    configs = session.exec(select(UserResourceConfig)).all()

    index = CurriculumIndex(courses=courses, nodes=nodes)
    packages_by_id = {package.id: package for package in packages}
    links_by_resource: dict[UUID, list[ResourceKnowledgeLink]] = defaultdict(list)
    for link in links:
        links_by_resource[link.resource_id].append(link)
    runs_by_package: dict[str, list[ResourceGenerationRun]] = defaultdict(list)
    for run in runs:
        if run.package_id:
            runs_by_package[run.package_id].append(run)
    configs_by_user_resource = {
        (config.user_id, config.resource_id): config for config in configs
    }

    changes: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    resource_matches: dict[UUID, CurriculumMatch] = {}

    for resource in resources:
        package = packages_by_id.get(resource.package_id or "")
        resource_links = links_by_resource.get(resource.id, [])
        package_runs = runs_by_package.get(resource.package_id or "", [])
        terms: list[object] = [resource.knowledge_point]
        terms.extend(link.knowledge_point for link in resource_links)
        if package is not None:
            terms.extend([package.node_id, package.node_label, package.topic])
        resolution = index.resolve(terms)

        if resolution.status == "ambiguous":
            skipped.append({
                "entity": "resource",
                "id": str(resource.id),
                "reason": "ambiguous_curriculum_match",
                "terms": list(resolution.terms),
                "candidate_node_ids": list(resolution.candidate_node_ids),
            })
            continue
        if resolution.match is None:
            if resource.course_id is None:
                skipped.append({
                    "entity": "resource",
                    "id": str(resource.id),
                    "reason": "no_exact_curriculum_match",
                    "terms": list(resolution.terms),
                })
            continue

        match = resolution.match
        declarations = _package_declarations(package, package_runs)
        conflicts = declared_scope_conflict(
            index=index,
            target_course_id=match.course_id,
            declarations=declarations,
        )
        if conflicts:
            config_key = (resource.uploader_id, resource.id)
            config = configs_by_user_resource.get(config_key)
            already_quarantined = bool(config is not None and config.is_hidden)
            skipped_record = {
                "entity": "resource",
                "id": str(resource.id),
                "package_id": resource.package_id,
                "reason": "content_scope_conflict",
                "current_course_id": str(resource.course_id) if resource.course_id else None,
                "matched_course_id": str(match.course_id),
                "matched_node_id": str(match.node_id),
                "declarations": conflicts,
                "recommended_action": (
                    "quarantined; regenerate_under_matched_course"
                    if quarantine_conflicts or already_quarantined
                    else "quarantine_and_regenerate_under_matched_course"
                ),
            }
            skipped.append(skipped_record)

            transition = quarantine_transition(
                enabled=quarantine_conflicts,
                config_exists=config is not None,
                current_hidden=config.is_hidden if config is not None else None,
            )
            if transition is not None:
                before, after = transition
                if config is None:
                    config = UserResourceConfig(
                        user_id=resource.uploader_id,
                        resource_id=resource.id,
                        is_hidden=True,
                    )
                    configs_by_user_resource[config_key] = config
                else:
                    config.is_hidden = True
                    config.updated_time = datetime.now(timezone.utc)
                changes.append(_change(
                    entity="user_resource_config",
                    entity_id=config.id,
                    before=before,
                    after=after,
                    match=match,
                    reason="quarantine_content_scope_conflict",
                ))
                session.add(config)
            continue

        resource_matches[resource.id] = match
        before: dict[str, Any] = {}
        after: dict[str, Any] = {}
        if resource.course_id != match.course_id:
            before["course_id"] = str(resource.course_id) if resource.course_id else None
            after["course_id"] = str(match.course_id)
        if not resource.knowledge_point:
            before["knowledge_point"] = None
            after["knowledge_point"] = match.node_label
        if should_repair_subject(
            index=index,
            subject=resource.subject,
            target_course_id=match.course_id,
        ):
            before["subject"] = resource.subject
            after["subject"] = resolve_resource_subject(match.course_name, match.node_label)
        if before:
            changes.append(_change(
                entity="resource",
                entity_id=resource.id,
                before=before,
                after=after,
                match=match,
                reason="unique_curriculum_scope",
            ))
            if apply:
                if "course_id" in after:
                    resource.course_id = match.course_id
                if "knowledge_point" in after:
                    resource.knowledge_point = match.node_label
                if "subject" in after:
                    resource.subject = str(after["subject"])
                session.add(resource)

        for link in resource_links:
            link_before: dict[str, Any] = {}
            link_after: dict[str, Any] = {}
            if link.course_id != match.course_id:
                link_before["course_id"] = str(link.course_id)
                link_after["course_id"] = str(match.course_id)
            if link.knowledge_node_id != match.node_id:
                link_before["knowledge_node_id"] = (
                    str(link.knowledge_node_id) if link.knowledge_node_id else None
                )
                link_after["knowledge_node_id"] = str(match.node_id)
            if link_before:
                changes.append(_change(
                    entity="resource_knowledge_link",
                    entity_id=link.id,
                    before=link_before,
                    after=link_after,
                    match=match,
                    reason="align_link_with_unique_curriculum_node",
                ))
                if apply:
                    link.course_id = match.course_id
                    link.knowledge_node_id = match.node_id
                    session.add(link)

    # Package and run scope can be repaired only when every resource in the
    # package has the same safe unique match.  The original request JSON remains
    # immutable and a compact provenance marker is added to operational state.
    resources_by_package: dict[str, list[Resource]] = defaultdict(list)
    for resource in resources:
        if resource.package_id:
            resources_by_package[resource.package_id].append(resource)
    applied_at = datetime.now(timezone.utc).isoformat()
    for package in packages:
        members = resources_by_package.get(package.id, [])
        if not members or any(item.id not in resource_matches for item in members):
            continue
        matches = {resource_matches[item.id] for item in members}
        if len(matches) != 1:
            continue
        match = next(iter(matches))
        package_runs = runs_by_package.get(package.id, [])
        conflicts = declared_scope_conflict(
            index=index,
            target_course_id=match.course_id,
            declarations=_package_declarations(package, package_runs),
        )
        if package.course_id not in (None, match.course_id) and conflicts:
            continue

        package_before: dict[str, Any] = {}
        package_after: dict[str, Any] = {}
        if package.course_id != match.course_id:
            package_before["course_id"] = str(package.course_id) if package.course_id else None
            package_after["course_id"] = str(match.course_id)
        if should_repair_subject(
            index=index,
            subject=package.subject,
            target_course_id=match.course_id,
        ):
            package_before["subject"] = package.subject
            package_after["subject"] = resolve_resource_subject(match.course_name, match.node_label)
        if package_before:
            changes.append(_change(
                entity="generated_resource_package",
                entity_id=package.id,
                before=package_before,
                after=package_after,
                match=match,
                reason="all_package_resources_share_unique_scope",
            ))
            if apply:
                package.course_id = match.course_id
                if "subject" in package_after:
                    package.subject = str(package_after["subject"])
                profile = dict(package.model_profile or {})
                profile["scope_backfill"] = {
                    "policy": POLICY_VERSION,
                    "applied_at": applied_at,
                    "node_id": str(match.node_id),
                }
                package.model_profile = profile
                session.add(package)

        for run in package_runs:
            if run.course_id == match.course_id:
                continue
            before = {"course_id": str(run.course_id) if run.course_id else None}
            after = {"course_id": str(match.course_id)}
            changes.append(_change(
                entity="resource_generation_run",
                entity_id=run.id,
                before=before,
                after=after,
                match=match,
                reason="package_scope_repair_preserving_original_request",
            ))
            if apply:
                run.course_id = match.course_id
                shared_state = dict(run.shared_state or {})
                shared_state["scope_backfill"] = {
                    "policy": POLICY_VERSION,
                    "applied_at": applied_at,
                    "node_id": str(match.node_id),
                    "original_request_preserved": True,
                }
                run.shared_state = shared_state
                session.add(run)

    if apply:
        session.commit()
    else:
        session.rollback()

    return {
        "schema_version": 1,
        "policy_version": POLICY_VERSION,
        "mode": "apply" if apply else "dry-run",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "positive_match": "exact normalized label or exact node UUID",
            "trusted_node_sources": sorted(learning_report_service.TRUSTED_GRAPH_SOURCES),
            "substring_matching": False,
            "ambiguous_matches": "unchanged",
            "quarantine_conflicts_enabled": quarantine_conflicts,
            "declared_content_scope_conflicts": (
                "hidden through user_resource_config; regenerate before restoring"
                if quarantine_conflicts
                else "unchanged; quarantine and regenerate"
            ),
        },
        "summary": {
            "courses_scanned": len(courses),
            "curriculum_nodes_indexed": len(index.node_ids),
            "resources_scanned": len(resources),
            "change_records": len(changes),
            "skipped_records": len(skipped),
            "content_scope_conflicts": sum(
                item["reason"] == "content_scope_conflict" for item in skipped
            ),
            "quarantine_records": sum(
                item["entity"] == "user_resource_config" for item in changes
            ),
        },
        "changes": changes,
        "skipped": skipped,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit safe repairs. Without this flag the script rolls back.",
    )
    parser.add_argument(
        "--quarantine-conflicts",
        action="store_true",
        help=(
            "Hide audited content-scope conflicts through UserResourceConfig. "
            "Requires --apply; never deletes resource rows or files."
        ),
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional JSON audit-report path. Parent directories are created.",
    )
    args = parser.parse_args()
    if args.quarantine_conflicts and not args.apply:
        parser.error("--quarantine-conflicts requires --apply")
    return args


def main() -> int:
    args = _parse_args()
    with Session(engine) as session:
        report = backfill(
            session,
            apply=args.apply,
            quarantine_conflicts=args.quarantine_conflicts,
        )
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
