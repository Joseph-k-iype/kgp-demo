import importlib.util
import shutil
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "demo_data", ROOT / "scripts/demo_data.py"
)
data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data)


def test_snapshot_contains_actual_stores_and_no_runtime_history():
    counts = data.validate(ROOT / "data/demo")
    assert counts["catalog_records"] == 359
    assert counts["business_rows"] == 880
    assert counts["objects"] == 40
    assert counts["rdf_triples"]["instances"] > 3000
    assert not any(
        "search_run" in p.name or "receipt" in p.name or p.name == ".env"
        for p in (ROOT / "data/demo").rglob("*")
    )


def test_snapshot_validation_rejects_modified_source_bytes(tmp_path):
    directory = tmp_path / "snapshot"
    shutil.copytree(ROOT / "data/demo", directory)
    first = next((directory / "objects").glob("*.txt"))
    first.write_text("Changed document")
    with pytest.raises(ValueError, match="digest"):
        data.validate(directory)
