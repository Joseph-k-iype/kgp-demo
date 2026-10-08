import json
from app.storage.structured import iter_rows
from app.knowledge.sources import iter_document_sections, source_info
from app.knowledge.runtime import version


def extract_evidence(scope, asset):
    base = {
        "asset_id": asset["id"],
        "domain_id": asset["domain_id"],
        "name": asset["name"],
        "product_ids": asset["product_ids"],
        "concept_iris": asset["concepts"],
        "classification": asset["classification"],
    }
    description = asset["name"] + ". " + asset["description"]
    yield {
        **base,
        "id": asset["id"] + ":metadata",
        "text": description,
        "source_ref": {
            "asset_id": asset["id"],
            "domain_id": asset["domain_id"],
            "version": version(description),
            "locator": "metadata",
        },
        "content_kind": "metadata",
        "provenance": {"type": "metadata", "location": asset["storage_location"]},
    }
    if asset["type"] == "Document":
        for i, section in enumerate(iter_document_sections(scope, asset["id"])):
            yield {
                **base,
                "id": asset["id"] + ":chunk-" + str(i),
                "text": section["title"] + "\n" + section["text"],
                "content_kind": "document",
                "source_ref": section["source_ref"],
                "provenance": {
                    "type": "document",
                    "object_key": asset["object_key"],
                    "start": section["start"],
                    "end": section["end"],
                    "section_id": section["locator"],
                    "location": asset["storage_location"],
                },
            }
    elif asset["type"] != "Metadata":
        for i, row in enumerate(iter_rows(scope, asset["id"])):
            yield {
                **base,
                "id": asset["id"] + ":rows-" + str(i),
                "text": asset["name"] + " " + json.dumps(row),
                "content_kind": "structured",
                "values": row,
                "source_ref": {
                    "asset_id": asset["id"],
                    "domain_id": asset["domain_id"],
                    "version": version(row),
                    "locator": row["record_id"],
                },
                "provenance": {
                    "type": "structured",
                    "table": "business_rows",
                    "row_id": row["record_id"],
                    "location": asset["storage_location"],
                },
            }
