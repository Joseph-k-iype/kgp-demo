"""Versioned, bounded-buffer source streaming independent of UI previews."""

import codecs, re
from fastapi import HTTPException
from app.catalog.service import get_record
from app.storage.objects import client
from app.config import settings
from app.knowledge.contracts import SourceRef


def source_info(scope, asset_id) -> SourceRef:
    asset = get_record(scope, asset_id, "asset")
    if asset["type"] != "Document":
        raise HTTPException(422, "Source is not a document")
    key = asset.get("object_key", "")
    if ".." in key or not key.startswith(asset["domain_id"] + "/"):
        raise HTTPException(422, "Invalid object reference")
    obj = client().stat_object(settings().bucket, key)
    return SourceRef(
        asset_id=asset_id,
        domain_id=asset["domain_id"],
        version=obj.metadata.get("x-amz-meta-sha256") or "etag:" + obj.etag,
        locator="document",
    )


def iter_document_sections(scope, asset_id):
    asset = get_record(scope, asset_id, "asset")
    ref = source_info(scope, asset_id)
    response = client().get_object(settings().bucket, asset["object_key"])
    decoder = codecs.getincrementaldecoder("utf-8")()
    pending = ""
    body = ""
    section = "overview"
    title = ""
    offset = 0
    start = 0
    part = 0

    def fragment(text, loc, at, part):
        return {
            "text": text,
            "title": title,
            "section_id": loc,
            "locator": loc if part == 0 else loc + ":" + str(part),
            "start": at,
            "end": at + len(text),
            "source_ref": ref.model_copy(
                update={"locator": loc if part == 0 else loc + ":" + str(part)}
            ).model_dump(mode="json"),
        }

    try:
        for chunk in response.stream(amt=32768):
            pending += decoder.decode(chunk)
            while "\n" in pending or len(pending) > 2048:
                if "\n" in pending:
                    line, pending = pending.split("\n", 1)
                    line += "\n"
                else:
                    line, pending = pending[:1024], pending[1024:]
                if line.startswith("# ") and not title:
                    title = line.strip().lstrip("# ")
                if line.startswith("## "):
                    if body:
                        yield fragment(body, section, start, part)
                    section = re.sub(
                        r"[^a-z0-9]+", "-", line[3:].strip().lower()
                    ).strip("-")
                    body = ""
                    part = 0
                    start = offset
                body += line
                offset += len(line)
                while len(body) > 1200:
                    yield fragment(body[:1200], section, start, part)
                    body = body[1200:]
                    start += 1200
                    part += 1
        pending += decoder.decode(b"", final=True)
        body += pending
        if body:
            yield fragment(body, section, start, part)
    finally:
        response.close()
        response.release_conn()


def source_ref_is_current(scope, ref):
    from app.db import query
    from app.knowledge.runtime import version

    asset = get_record(scope, ref.asset_id, "asset")
    if asset["type"] == "Document":
        return source_info(scope, ref.asset_id).version == ref.version
    rows = query(
        "SELECT payload FROM business_rows WHERE id=:id AND asset_id=:asset",
        {"id": ref.locator, "asset": ref.asset_id},
    )
    return bool(rows) and version(rows[0]["payload"]) == ref.version
