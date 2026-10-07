import json
from app.storage.objects import preview_object
from app.storage.structured import preview_rows


def extract_evidence(scope, asset):
    base = {
        "asset_id": asset["id"],
        "domain_id": asset["domain_id"],
        "name": asset["name"],
        "product_ids": asset["product_ids"],
        "concept_iris": asset["concepts"],
        "classification": asset["classification"],
    }
    output = [
        {
            **base,
            "id": asset["id"] + ":metadata",
            "text": asset["name"] + ". " + asset["description"],
            "provenance": {"type": "metadata", "location": asset["storage_location"]},
        }
    ]
    if asset["type"] == "Document":
        text = preview_object(scope, asset["id"])["text"]
        for i, start in enumerate(range(0, len(text), 650)):
            output.append(
                {
                    **base,
                    "id": f"{asset['id']}:chunk-{i}",
                    "text": text[start : start + 800],
                    "provenance": {
                        "type": "document",
                        "object_key": asset["object_key"],
                        "start": start,
                        "end": min(start + 800, len(text)),
                        "location": asset["storage_location"],
                    },
                }
            )
    else:
        for i, row in enumerate(preview_rows(scope, asset["id"])):
            output.append(
                {
                    **base,
                    "id": f"{asset['id']}:rows-{i}",
                    "text": asset["name"] + " " + json.dumps(row),
                    "provenance": {
                        "type": "structured",
                        "table": "business_rows",
                        "row_id": row["record_id"],
                        "location": asset["storage_location"],
                    },
                }
            )
    return output
