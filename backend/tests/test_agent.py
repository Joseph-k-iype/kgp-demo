import pytest
from app.agent.provider import validate_answer
from app.contracts import AnswerOutput,Statement
from app.agent.graph import build_graph

def test_citation_validation_rejects_unknown_ids():
    answer=AnswerOutput(statements=[Statement(text='Claim',evidence_ids=['invented'])],gaps=[],uncertainty='')
    with pytest.raises(ValueError): validate_answer(answer,[{'id':'real'}])

def test_uncited_claim_rejected():
    answer=AnswerOutput(statements=[Statement(text='Claim',evidence_ids=[])],gaps=[],uncertainty='')
    with pytest.raises(ValueError):validate_answer(answer,[{'id':'real'}])
