"""No-provider source exploration for explicit extractive demo and smoke evals.

This conservative deterministic adapter is not a model quality evaluation and
never labels paraphrases as verified answers. It uses source handles, not gold
case IDs or expected answers.
"""

import json, re
from app.agent.actions import ActionDecision, PlannedCall, EvidenceAssessment
from app.knowledge.contracts import SearchIntentV2, AnswerFacet
from app.catalog.service import get_record


def make_offline_decider(ctx, adaptive=True):
    def planned(tool, **args):
        return PlannedCall(tool=tool, arguments_json=json.dumps(args))

    def decide(state, deadline):
        query = state.query
        if state.model_calls == 0:
            if (
                state.observations
                and state.observations[0].get("outcome") == "ambiguous"
            ):
                return ActionDecision(
                    stop_action="clarify",
                    summary="Which business entity or policy do you mean?",
                )
            intent = SearchIntentV2(
                query=query,
                facets=[
                    AnswerFacet(
                        id="requested_content",
                        description=query,
                        kinds=["document", "structured", "definition"],
                    )
                ],
                entity_ids=[e["id"] for e in state.entities[:3]],
            )
            if intent.entity_ids:
                reads = [
                    planned(
                        "traverse_graph",
                        roots=intent.entity_ids,
                        predicates=[
                            "governedBy",
                            "supportedBy",
                            "recordedIn",
                            "partOf",
                            "representsEntity",
                            "measures",
                            "partyTo",
                            "requiresContract",
                        ],
                        target_kinds=[],
                        depth=3,
                    )
                ]
            else:
                reads = [
                    planned(
                        "search_evidence",
                        query=query,
                        strategy="keyword",
                        kinds=["document", "structured"],
                    )
                ]
            return ActionDecision(
                intent=intent,
                read_calls=reads,
                summary="Following scoped source relationships",
            )
        if state.model_calls == 1:
            refs = []
            for path in state.paths:
                for edge in path.get("edges", []):
                    ref = edge["source_ref"]
                    if ref not in refs:
                        refs.append(ref)
            reads = []
            seen = set()
            for ref in refs:
                key = (ref["asset_id"], ref["locator"])
                if key in seen:
                    continue
                seen.add(key)
                asset = get_record(ctx.scope, ref["asset_id"], "asset")
                if asset["type"] == "Document":
                    reads.append(
                        planned(
                            "read_document",
                            asset_id=asset["id"],
                            section_id=ref["locator"],
                        )
                    )
                elif asset["type"] in ["Table", "Data product"]:
                    reads.append(
                        planned(
                            "query_dataset",
                            query={
                                "asset_id": asset["id"],
                                "filters": [
                                    {
                                        "field": "record_id",
                                        "op": "eq",
                                        "value": ref["locator"],
                                    }
                                ],
                                "limit": 1,
                            },
                        )
                    )
                if len(reads) == 4:
                    break
            if not reads:
                reads = [
                    planned(
                        "search_evidence",
                        query=query,
                        strategy="keyword",
                        kinds=["document", "structured"],
                    )
                ]
            return ActionDecision(
                read_calls=reads, summary="Reading actual source passages and rows"
            )
        if adaptive and state.model_calls == 2:
            assets = list(
                dict.fromkeys(
                    edge["source_ref"]["asset_id"]
                    for path in state.paths
                    for edge in path.get("edges", [])
                )
            )[:50]
            return ActionDecision(
                read_calls=[
                    planned(
                        "search_evidence",
                        query=query,
                        strategy="keyword",
                        asset_ids=assets,
                        kinds=["document", "structured"],
                    )
                ],
                summary="Looking for additional source coverage",
            )
        return ActionDecision(
            stop_action="finish", summary="Showing source excerpts for inspection"
        )

    return decide
