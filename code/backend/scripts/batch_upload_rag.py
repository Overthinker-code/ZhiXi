#!/usr/bin/env python3
"""
Batch upload files to RAG without using the frontend flow.

Example:
  python scripts/batch_upload_rag.py \
    --base-url http://127.0.0.1:8000/api/v1 \
    --email admin@example.com \
    --password admin123 \
    --input "D:/docs/rag" \
    --scope system \
    --recursive
"""

from __future__ import annotations

import argparse
import mimetypes
import sys
from pathlib import Path
from typing import Iterable

import httpx

ALLOWED_SUFFIXES = {".doc", ".docx", ".pdf", ".ppt", ".pptx", ".md", ".markdown"}


def collect_files(input_path: Path, recursive: bool) -> list[Path]:
    if input_path.is_file():
        return [input_path] if input_path.suffix.lower() in ALLOWED_SUFFIXES else []

    if not input_path.is_dir():
        raise FileNotFoundError(f"Path not found: {input_path}")

    iterator: Iterable[Path]
    if recursive:
        iterator = input_path.rglob("*")
    else:
        iterator = input_path.glob("*")

    files = [
        p
        for p in iterator
        if p.is_file() and p.suffix.lower() in ALLOWED_SUFFIXES
    ]
    files.sort()
    return files


def login(client: httpx.Client, base_url: str, email: str, password: str) -> str:
    token_url = f"{base_url.rstrip('/')}/login/access-token"
    response = client.post(
        token_url,
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("Login succeeded but access_token is missing")
    return token


def fetch_existing_names(client: httpx.Client, base_url: str, token: str) -> set[str]:
    url = f"{base_url.rstrip('/')}/rag/files"
    response = client.get(url, headers={"Authorization": f"Bearer {token}"})
    response.raise_for_status()
    payload = response.json()
    files = payload.get("files") or []
    names = {str(item.get("name") or "") for item in files if item.get("name")}
    return names


def upload_file(
    client: httpx.Client,
    base_url: str,
    token: str,
    path: Path,
    scope: str,
) -> dict:
    url = f"{base_url.rstrip('/')}/rag/upload"
    mime_type, _ = mimetypes.guess_type(str(path))
    mime_type = mime_type or "application/octet-stream"
    with path.open("rb") as fh:
        files = {"file": (path.name, fh, mime_type)}
        data = {"scope": scope}
        response = client.post(
            url,
            data=data,
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
    response.raise_for_status()
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch upload files to RAG.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000/api/v1",
        help="Backend API base URL (default: %(default)s)",
    )
    parser.add_argument("--email", required=True, help="Login email")
    parser.add_argument("--password", required=True, help="Login password")
    parser.add_argument("--input", required=True, help="Input file or directory")
    parser.add_argument(
        "--scope",
        choices=["system", "personal"],
        default="personal",
        help="Upload scope (default: %(default)s)",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively scan input directory",
    )
    parser.add_argument(
        "--skip-existing-name",
        action="store_true",
        help="Skip file if same name already exists in RAG file list",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print files to upload, do not upload",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="HTTP timeout in seconds (default: %(default)s)",
    )
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    files = collect_files(input_path, recursive=args.recursive)
    if not files:
        print("No supported files found.")
        return 1

    print(f"Found {len(files)} file(s).")
    for item in files:
        print(f" - {item}")

    if args.dry_run:
        return 0

    success = 0
    failed = 0
    skipped = 0

    with httpx.Client(timeout=args.timeout) as client:
        token = login(client, args.base_url, args.email, args.password)
        existing_names: set[str] = set()
        if args.skip_existing_name:
            existing_names = fetch_existing_names(client, args.base_url, token)

        for file_path in files:
            if args.skip_existing_name and file_path.name in existing_names:
                skipped += 1
                print(f"[SKIP] {file_path.name} (same name exists)")
                continue

            try:
                result = upload_file(
                    client=client,
                    base_url=args.base_url,
                    token=token,
                    path=file_path,
                    scope=args.scope,
                )
                success += 1
                file_id = result.get("file_id", "-")
                chunks = result.get("chunks", "-")
                print(
                    f"[OK] {file_path.name} -> file_id={file_id}, chunks={chunks}, scope={args.scope}"
                )
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print(f"[FAIL] {file_path.name} -> {exc}")

    print(
        f"\nDone. success={success}, failed={failed}, skipped={skipped}, total={len(files)}"
    )
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())

