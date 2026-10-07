from typing import TypedDict
class SearchState(TypedDict,total=False):
    run_id:str
    person_id:str
    scope_version:int
    query:str
    mode:str
    started:float
    tool_calls:int
    retrieval_passes:int
    concept_labels:list[str]
    concepts:list[str]
    variants:list[str]
    evidence:list[dict]
    statements:list[dict]
    gaps:list[str]
    uncertainty:str
    graph:dict
