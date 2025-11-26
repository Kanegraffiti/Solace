"""Synchronise and back up Solace journal data with optional remote backends."""

from __future__ import annotations

import base64
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from zipfile import ZIP_DEFLATED, ZipFile

from solace.configuration import get_cipher, get_storage_path, load_config


@dataclass
class SyncResult:
    """Outcome details from a sync or backup run."""

    archive: Path
    backend: str
    remote_target: Optional[str] = None
    dry_run: bool = False


SUPPORTED_BACKENDS = {"local", "s3", "webdav"}


class SyncConfigurationError(RuntimeError):
    """Raised when the sync backend is misconfigured."""


class SyncConflictError(FileExistsError):
    """Raised when a destination already exists and overwrite is disabled."""


def _sync_config(config: Dict[str, object]) -> Dict[str, object]:
    sync_cfg = config.setdefault("sync", {})
    if "backend" not in sync_cfg:
        sync_cfg["backend"] = "local"
    return sync_cfg


def _staging_dir(config: Dict[str, object]) -> Path:
    cache_dir = config.get("paths", {}).get("cache")
    if cache_dir:
        return Path(cache_dir).expanduser() / "sync"
    return get_storage_path(config, "root") / "cache" / "sync"


def _ensure_cipher(config: Dict[str, object], cipher, password: Optional[str]):
    if cipher:
        return cipher
    return get_cipher(config, password=password)


def package_journal(
    config: Dict[str, object] | None = None,
    *,
    cipher=None,
    password: Optional[str] = None,
    include_restore_point: bool = True,
    dry_run: bool = False,
) -> Path:
    """Package the journal into an encrypted zip archive.

    The archive always contains an encrypted ``journal.enc`` payload and a
    ``metadata.json`` descriptor.  When ``include_restore_point`` is true a
    plain-text copy of the original ``entries.json`` is stored alongside so
    that users can recover even if keys change.
    """

    config = config or load_config()
    sync_cfg = _sync_config(config)
    entries_path = get_storage_path(config, "journal") / "entries.json"
    entries_path.parent.mkdir(parents=True, exist_ok=True)
    if not entries_path.exists():
        entries_path.write_text("[]", encoding="utf-8")

    staging_root = _staging_dir(config)
    staging_root.mkdir(parents=True, exist_ok=True)
    archive_path = staging_root / f"journal-sync-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"

    if dry_run:
        return archive_path

    cipher = _ensure_cipher(config, cipher, password)
    payload = entries_path.read_bytes()
    encrypted_payload = cipher.encrypt(payload)

    metadata = {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "source": str(entries_path),
        "config_version": config.get("version", "2.0"),
        "backend": sync_cfg.get("backend", "local"),
    }

    with ZipFile(archive_path, mode="w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("journal.enc", encrypted_payload)
        archive.writestr("metadata.json", json.dumps(metadata, indent=2))
        if include_restore_point:
            archive.writestr("entries.json", entries_path.read_text(encoding="utf-8"))
            archive.writestr("config.json", json.dumps(config, indent=2))
    return archive_path


def _local_destination(config: Dict[str, object], archive: Path) -> Path:
    sync_cfg = _sync_config(config)
    local_cfg = sync_cfg.get("local", {}) if isinstance(sync_cfg, dict) else {}
    target_dir = Path(local_cfg.get("path") or (get_storage_path(config, "root") / "backups"))
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / archive.name


def _sync_local(config: Dict[str, object], archive: Path, *, allow_overwrite: bool, dry_run: bool) -> SyncResult:
    destination = _local_destination(config, archive)
    if destination.exists() and not allow_overwrite:
        raise SyncConflictError(destination)
    if dry_run:
        return SyncResult(archive=destination, backend="local", dry_run=True)
    shutil.copy2(archive, destination)
    return SyncResult(archive=destination, backend="local")


def _sync_s3(config: Dict[str, object], archive: Path, *, allow_overwrite: bool, dry_run: bool) -> SyncResult:
    sync_cfg = _sync_config(config)
    s3_cfg = sync_cfg.get("s3", {}) if isinstance(sync_cfg, dict) else {}
    if not s3_cfg.get("enabled"):
        raise SyncConfigurationError("S3 backend disabled in config")
    bucket = s3_cfg.get("bucket")
    prefix = s3_cfg.get("prefix", "solace/")
    if not bucket:
        raise SyncConfigurationError("S3 bucket is not configured")
    key = f"{prefix.rstrip('/')}/{archive.name}".lstrip("/")
    remote = f"s3://{bucket}/{key}"
    if dry_run:
        return SyncResult(archive=archive, backend="s3", remote_target=remote, dry_run=True)

    try:
        import boto3
    except Exception as exc:  # noqa: BLE001
        raise SyncConfigurationError("boto3 is required for S3 sync") from exc

    session_kwargs = {}
    if s3_cfg.get("profile"):
        session_kwargs["profile_name"] = s3_cfg["profile"]
    session = boto3.Session(**session_kwargs)
    client = session.client(
        "s3",
        endpoint_url=s3_cfg.get("endpoint") or None,
        region_name=s3_cfg.get("region") or None,
    )
    if not allow_overwrite:
        try:
            client.head_object(Bucket=bucket, Key=key)
            raise SyncConflictError(remote)
        except client.exceptions.NoSuchKey:
            pass
        except client.exceptions.ClientError:
            # Treat unknown errors as missing to avoid false positives offline
            pass
    client.upload_file(str(archive), bucket, key)
    return SyncResult(archive=archive, backend="s3", remote_target=remote)


def _sync_webdav(config: Dict[str, object], archive: Path, *, allow_overwrite: bool, dry_run: bool) -> SyncResult:
    sync_cfg = _sync_config(config)
    webdav_cfg = sync_cfg.get("webdav", {}) if isinstance(sync_cfg, dict) else {}
    if not webdav_cfg.get("enabled"):
        raise SyncConfigurationError("WebDAV backend disabled in config")
    base_url = webdav_cfg.get("url")
    if not base_url:
        raise SyncConfigurationError("WebDAV URL is not configured")
    target_path = webdav_cfg.get("path", "/solace")
    remote = f"{base_url.rstrip('/')}/{target_path.strip('/')}/{archive.name}"
    if dry_run:
        return SyncResult(archive=archive, backend="webdav", remote_target=remote, dry_run=True)

    from urllib import error, request

    req = request.Request(remote, data=archive.read_bytes(), method="PUT")
    if webdav_cfg.get("username"):
        credentials = f"{webdav_cfg.get('username')}:{webdav_cfg.get('password', '')}"
        token = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
        req.add_header("Authorization", f"Basic {token}")

    opener = request.build_opener()
    if not allow_overwrite:
        head_req = request.Request(remote, method="HEAD")
        try:
            opener.open(head_req)
            raise SyncConflictError(remote)
        except error.HTTPError as exc:  # noqa: PERF203
            if exc.code not in {401, 404}:
                raise
    opener.open(req)
    return SyncResult(archive=archive, backend="webdav", remote_target=remote)


def perform_sync(
    config: Dict[str, object] | None = None,
    *,
    backend: Optional[str] = None,
    cipher=None,
    password: Optional[str] = None,
    include_restore_point: bool = True,
    allow_overwrite: bool = False,
    dry_run: bool = False,
) -> SyncResult:
    """Package the journal and send it to the selected backend."""

    config = config or load_config()
    sync_cfg = _sync_config(config)
    backend = backend or sync_cfg.get("backend", "local")
    if backend not in SUPPORTED_BACKENDS:
        raise SyncConfigurationError(f"Unsupported backend: {backend}")

    include_restore_point = bool(include_restore_point and sync_cfg.get("restore_point", True))
    dry_run = bool(dry_run or sync_cfg.get("dry_run", False))

    archive = package_journal(
        config,
        cipher=cipher,
        password=password,
        include_restore_point=include_restore_point,
        dry_run=dry_run,
    )

    if dry_run:
        return SyncResult(archive=archive, backend=backend, dry_run=True)

    if backend == "local":
        return _sync_local(config, archive, allow_overwrite=allow_overwrite, dry_run=dry_run)
    if backend == "s3":
        return _sync_s3(config, archive, allow_overwrite=allow_overwrite, dry_run=dry_run)
    if backend == "webdav":
        return _sync_webdav(config, archive, allow_overwrite=allow_overwrite, dry_run=dry_run)

    raise SyncConfigurationError(f"Unhandled backend: {backend}")


__all__ = [
    "SUPPORTED_BACKENDS",
    "SyncConflictError",
    "SyncConfigurationError",
    "SyncResult",
    "package_journal",
    "perform_sync",
]
