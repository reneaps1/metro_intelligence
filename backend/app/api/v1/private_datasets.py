"""IQ-F30 (plan decision D29): admin-only upload of converted private datasets.

Only on a private host the customer authorized in writing
(`DEMO_PRIVATE_HOST_AUTHORIZATION`) and with `PRIVATE_DATASETS_UPLOAD_ENABLED`;
everywhere else every route answers 404, exactly as if it did not exist.

An operator converts the customer's export offline and sends one part at a
time over HTTPS: ``manifest.json`` + the pieces file it names. The files are
written to a temporary folder, fully validated (manifest, checksum, columns,
size caps) by loading them, and only then moved into `DEMO_REAL_DATASETS_DIR`
as ``<slug>/``. Contents, names and values are never logged; the audit log
records who uploaded or removed which slug, the checksum and the piece count.

No ``from __future__ import annotations``: FastAPI's ``UploadFile`` form
detection needs real runtime types (same as ``app.api.v1.imports``).
"""

import hashlib
import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi import Path as PathParam
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.connectors.pieces_file import MAX_MANIFEST_BYTES, read_manifest, read_pieces
from app.connectors.product_spec import MAX_PRODUCT_BYTES, apply_product_spec, read_product_spec
from app.core.config import get_settings
from app.core.database import get_db
from app.core.edition import require_industrial_edition
from app.core.private_data import authorized_private_host
from app.core.ratelimit import limiter
from app.core.security import require_permission
from app.models.security import User
from app.schemas.quality_analytics import CatalogEntryOut
from app.services import dataset_cache, dataset_registry
from app.services.audit_service import AuditContext, get_audit_context, record_event

_MB = 1024 * 1024
SLUG = r"^[a-z0-9][a-z0-9-]{0,39}$"


def require_upload_enabled() -> None:
    settings = get_settings()
    if not (settings.private_datasets_upload_enabled and authorized_private_host(settings)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not Found")


router = APIRouter(
    prefix="/private-datasets",
    tags=["private-datasets"],
    dependencies=[Depends(require_industrial_edition), Depends(require_upload_enabled)],
)

# Administrators only (user management is admin-only in the RBAC matrix).
_admin = require_permission("security.user", "update")


def _root() -> Path:
    root_value = get_settings().demo_real_datasets_dir
    if not root_value:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="DEMO_REAL_DATASETS_DIR is not configured.")
    root = Path(root_value)
    root.mkdir(parents=True, exist_ok=True)
    return root


async def _save(upload: UploadFile, target: Path, cap: int) -> str:
    """Stream to disk under a byte cap; returns the SHA-256."""
    digest = hashlib.sha256()
    written = 0
    with target.open("wb") as fh:
        while chunk := await upload.read(1 << 20):
            written += len(chunk)
            if written > cap:
                raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large.")
            digest.update(chunk)
            fh.write(chunk)
    return digest.hexdigest()


def _slug_id(slug: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"private-dataset:{slug}")


@router.put("/{slug}", response_model=CatalogEntryOut)
@limiter.limit("10/minute")
async def upload_private_dataset(
    request: Request,
    slug: str = PathParam(..., pattern=SLUG),
    manifest: UploadFile = File(...),
    pieces: UploadFile = File(...),
    product: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    _user: User = Depends(_admin),
    context: AuditContext = Depends(get_audit_context),
) -> CatalogEntryOut:
    if slug in dataset_registry.RESERVED_SLUGS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Reserved name.")
    settings = get_settings()
    root = _root()
    staging = Path(tempfile.mkdtemp(prefix=".upload-", dir=root))
    try:
        manifest_path = staging / "manifest.json"
        await _save(manifest, manifest_path, MAX_MANIFEST_BYTES)
        try:
            parsed = read_manifest(manifest_path)
        except (OSError, ValueError, ValidationError):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid manifest.") from None
        pieces_sha = await _save(
            pieces, staging / parsed.pieces_file, settings.demo_real_dataset_max_mb * _MB
        )
        try:
            loaded = read_pieces(
                manifest_path,
                dataset_id=f"{dataset_registry.REGISTRY_PREFIX}{slug}",
                name=slug,
                description="",
                max_bytes=settings.demo_real_dataset_max_mb * _MB,
                max_pieces=settings.demo_real_dataset_max_pieces,
            )
        except (OSError, ValueError, ValidationError):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Pieces file does not match the manifest."
            ) from None
        product_sha = None
        if product is not None:
            # IQ-F28: the part's drawing data; it must describe THIS part's variables.
            product_path = staging / "product.json"
            product_sha = await _save(product, product_path, MAX_PRODUCT_BYTES)
            try:
                apply_product_spec(loaded, read_product_spec(product_path))
            except (OSError, ValueError, ValidationError):
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Product file does not match the part."
                ) from None
        final = root / slug
        if final.exists():
            shutil.rmtree(final)
        staging.rename(final)
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    dataset_cache.forget(f"{dataset_registry.REGISTRY_PREFIX}{slug}")
    record_event(
        db,
        context,
        action="private_dataset_uploaded",
        entity_type="quality_analytics.private_dataset",
        entity_id=_slug_id(slug),
        after={
            "slug": slug,
            "pieces": parsed.pieces,
            "pieces_sha256": pieces_sha,
            "product_sha256": product_sha,
        },
    )
    db.commit()
    entry = dataset_registry.entry(f"{dataset_registry.REGISTRY_PREFIX}{slug}")
    if entry is None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Uploaded but not offered on this host.")
    return CatalogEntryOut(
        id=entry.id,
        label=entry.label,
        line=entry.line,
        description=entry.description,
        source_type="REAL",
        pieces=entry.pieces,
        period_start=entry.period_start,
        period_end=entry.period_end,
        loaded=False,
    )


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
def delete_private_dataset(
    request: Request,
    slug: str = PathParam(..., pattern=SLUG),
    db: Session = Depends(get_db),
    _user: User = Depends(_admin),
    context: AuditContext = Depends(get_audit_context),
) -> None:
    """Withdrawal procedure: remove one part from this host."""
    folder = _root() / slug
    if not folder.is_dir():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not Found")
    shutil.rmtree(folder)
    dataset_registry.reset_cache()
    record_event(
        db,
        context,
        action="private_dataset_removed",
        entity_type="quality_analytics.private_dataset",
        entity_id=_slug_id(slug),
        after={"slug": slug},
    )
    db.commit()
