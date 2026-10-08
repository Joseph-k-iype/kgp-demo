import hashlib
import codecs
from io import BytesIO
from datetime import timedelta
from minio import Minio
from app.config import settings
from app.catalog.service import get_record
from fastapi import HTTPException


def client():
    c = settings()
    return Minio(
        c.minio_endpoint,
        access_key=c.minio_access_key,
        secret_key=c.minio_secret_key,
        secure=False,
    )


def put_object(key, text):
    c = client()
    bucket = settings().bucket
    if not c.bucket_exists(bucket):
        c.make_bucket(bucket)
    data = text.encode()
    c.put_object(
        bucket,
        key,
        BytesIO(data),
        len(data),
        content_type="text/plain; charset=utf-8",
        metadata={"sha256": hashlib.sha256(data).hexdigest()},
    )


def preview_object(scope, asset_id):
    a = get_record(scope, asset_id, "asset")
    if a["type"] != "Document":
        raise HTTPException(422, "This asset is not a document")
    key = a["object_key"]
    if ".." in key or not key.startswith(a["domain_id"] + "/"):
        raise HTTPException(422, "Invalid object reference")
    info = client().stat_object(settings().bucket, key)
    response = client().get_object(settings().bucket, key)
    try:
        raw = response.read(256000)
        text = codecs.getincrementaldecoder("utf-8")().decode(
            raw, final=info.size <= 256000
        )
    finally:
        response.close()
        response.release_conn()
    return {
        "text": text,
        "location": a["storage_location"],
        "asset_id": asset_id,
        "content_type": "text/plain",
        "truncated": info.size > 256000,
        "version": info.metadata.get("x-amz-meta-sha256") or "etag:" + info.etag,
    }
