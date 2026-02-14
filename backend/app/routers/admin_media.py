"""
Admin media: upload file to GridFS, serve by file_id.
Stored in MongoDB; reference in questions via media.gridfs_file_id.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import Response
from bson import ObjectId

from app.core.db import get_db
from app.core.deps import get_current_admin_user
from app.core.errors import AppError

router = APIRouter(prefix="/admin/media", tags=["admin-media"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload")
def upload_media(
    current_user: Annotated[dict, Depends(get_current_admin_user)],
    file: UploadFile = File(...),
):
    """Upload a file (image). Stored in GridFS. Returns file_id and url for preview/saving in question."""
    if not file.filename:
        raise AppError("NO_FILE", "No file provided", status_code=400)
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise AppError(
            "INVALID_TYPE",
            f"Allowed types: {', '.join(ALLOWED_CONTENT_TYPES)}",
            status_code=400,
        )
    data = file.file.read()
    if len(data) > MAX_SIZE:
        raise AppError("FILE_TOO_LARGE", "Max size 10 MB", status_code=400)
    db = get_db()
    from gridfs import GridFS
    fs = GridFS(db, collection="media")
    file_id = fs.put(data, filename=file.filename, content_type=content_type)
    file_id_str = str(file_id)
    url = f"/admin/media/files/{file_id_str}"
    return {"file_id": file_id_str, "url": url, "content_type": content_type}


@router.get("/files/{file_id}")
def get_media_file(
    file_id: str,
    current_user: Annotated[dict, Depends(get_current_admin_user)],
):
    """Stream a file from GridFS by file_id."""
    if not ObjectId.is_valid(file_id):
        return Response(status_code=404)
    db = get_db()
    from gridfs import GridFS
    fs = GridFS(db, collection="media")
    try:
        grid_out = fs.get(ObjectId(file_id))
    except Exception:
        return Response(status_code=404)
    content_type = grid_out.content_type or "application/octet-stream"
    return Response(content=grid_out.read(), media_type=content_type)
