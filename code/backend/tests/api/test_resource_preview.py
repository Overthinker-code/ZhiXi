from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from docx import Document
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session

from app import models
from app.api.routes import resources
from fastapi.responses import FileResponse
from app.db.base_class import Base


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    Base.metadata.create_all(engine)
    return Session(engine)


def _resource(owner_id, *, name: str, source: str | None = None) -> models.Resource:
    return models.Resource(
        title="安全预览资料",
        type="docx",
        subject="数据库",
        file_name=name,
        file_path=name,
        content_type="application/octet-stream",
        source=source,
        uploader_id=owner_id,
    )


def _owner(user_id):
    return SimpleNamespace(id=user_id, is_superuser=False)


def test_pdf_preview_is_inline_private_and_records_evidence_once(tmp_path: Path, monkeypatch) -> None:
    db = _session()
    owner_id = uuid4()
    resource = _resource(owner_id, name="handout.pdf")
    db.add(resource)
    db.commit()
    db.refresh(resource)
    (tmp_path / "handout.pdf").write_bytes(b"%PDF-1.4\npreview")
    monkeypatch.setattr(resources, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(
        Path,
        "read_bytes",
        lambda _path: (_ for _ in ()).throw(AssertionError("binary preview must stream")),
    )
    evidence: list[str] = []
    monkeypatch.setattr(resources, "_record_resource_event", lambda *_args, **kwargs: evidence.append(kwargs["event_type"]))

    response = resources.preview_resource(db=db, current_user=_owner(owner_id), resource_id=resource.id)

    assert response.status_code == 200
    assert isinstance(response, FileResponse)
    assert response.media_type == "application/pdf"
    assert response.headers["content-disposition"].startswith("inline")
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert response.path.endswith("handout.pdf")
    assert evidence == ["resource_previewed"]
    assert "file_path" not in resources._resource_payload(resource)


def test_docx_preview_escapes_content_and_keeps_structural_html(tmp_path: Path, monkeypatch) -> None:
    db = _session()
    owner_id = uuid4()
    resource = _resource(owner_id, name="notes.docx")
    db.add(resource)
    db.commit()
    db.refresh(resource)
    document = Document()
    document.add_heading("<script>alert(1)</script>", level=1)
    document.add_paragraph("第一段")
    document.add_paragraph("列表项", style="List Bullet")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "字段"
    table.cell(0, 1).text = "值"
    document.save(tmp_path / "notes.docx")
    monkeypatch.setattr(resources, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(resources, "_record_resource_event", lambda *_args, **_kwargs: None)

    response = resources.preview_resource(db=db, current_user=_owner(owner_id), resource_id=resource.id)
    body = response.body.decode("utf-8")

    assert response.status_code == 200
    assert response.media_type.startswith("text/html")
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body
    assert "<script>alert" not in body
    assert "<h1>" in body and "<ul>" in body and "<table>" in body
    assert "Content-Security-Policy" in body
    assert "*,*::before,*::after{box-sizing:border-box}" in body
    assert "width:min(210mm,100%)" in body
    assert "min-height:297mm" in body
    assert ".preview-presentation" in body


def test_preview_hides_private_generated_resources_and_handles_missing_or_unsupported_files(
    tmp_path: Path, monkeypatch
) -> None:
    db = _session()
    owner_id, other_id = uuid4(), uuid4()
    private = _resource(owner_id, name="private.pdf", source="agent")
    missing = _resource(owner_id, name="missing.pdf")
    legacy = _resource(owner_id, name="legacy.doc")
    db.add(private)
    db.add(missing)
    db.add(legacy)
    db.commit()
    for resource in (private, missing, legacy):
        db.refresh(resource)
    (tmp_path / "private.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "legacy.doc").write_bytes(b"legacy")
    monkeypatch.setattr(resources, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(resources, "_record_resource_event", lambda *_args, **_kwargs: None)

    with pytest.raises(Exception) as hidden:
        resources.preview_resource(db=db, current_user=_owner(other_id), resource_id=private.id)
    assert getattr(hidden.value, "status_code", None) == 404
    with pytest.raises(Exception) as absent:
        resources.preview_resource(db=db, current_user=_owner(owner_id), resource_id=missing.id)
    assert getattr(absent.value, "status_code", None) == 404
    with pytest.raises(Exception) as unsupported:
        resources.preview_resource(db=db, current_user=_owner(owner_id), resource_id=legacy.id)
    assert getattr(unsupported.value, "status_code", None) == 415
