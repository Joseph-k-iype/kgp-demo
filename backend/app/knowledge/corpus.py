import json
from pathlib import Path
from app.knowledge.contracts import GraphAssertion

ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "semantic"


def semantic_manifest():
    return json.loads((ROOT / "manifest.json").read_text())


def load_semantic_manifest() -> list[GraphAssertion]:
    return [GraphAssertion.model_validate(a) for a in semantic_manifest()["assertions"]]


def managed_document(asset_id: str) -> str | None:
    path = ROOT / "documents" / (asset_id + ".txt")
    return path.read_text() if path.is_file() else None


def semantic_records():
    return [
        {
            "id": n["id"],
            "kind": n["kind"],
            "domain_id": n["domain_id"],
            "payload": {
                k: v for k, v in n.items() if k not in ["id", "kind", "domain_id"]
            },
        }
        for n in semantic_manifest()["nodes"]
    ]
