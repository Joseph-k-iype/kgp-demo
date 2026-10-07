from app.worker import submit_index, run_index_job, get_job
from app.auth import resolve_scope
import pytest
from fastapi import HTTPException


def test_persisted_index_job_and_scoped_submission():
    admin = resolve_scope("admin")
    job = submit_index(admin, ["risk-asset-0"])
    assert job["state"] == "pending"
    run_index_job(job["id"])
    assert get_job(admin, job["id"])["state"] == "completed"
    with pytest.raises(HTTPException):
        submit_index(resolve_scope("analyst"), ["risk-asset-0"])
