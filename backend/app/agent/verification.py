"""Source/span/typed-value gates plus an explicit, fallible semantic judge.

A valid asset ID is insufficient. Every accepted citation must point to a current
permitted source and an exact passage or independently checked structured field.
"""

import json, re
from decimal import Decimal, InvalidOperation
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from fastapi import HTTPException
from app.knowledge.contracts import SourceRef, EvidenceFragment, QueryDatasetAction
from app.knowledge.runtime import guard, version
from app.knowledge.sources import source_ref_is_current, iter_document_sections
from app.catalog.service import get_record
from app.db import query


class ClaimCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    source_ref: SourceRef | None = None
    quote: str | None = Field(default=None, max_length=1600)
    field: str | None = None
    value: str | None = None
    unit: str | None = None
    period: str | None = None


class SupportedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=3000)
    citations: list[ClaimCitation] = Field(min_length=1, max_length=8)
    facet_ids: list[str] = Field(default_factory=list, max_length=8)
    governance_paths: list[list[str]] = Field(default_factory=list, max_length=3)


class DraftAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claims: list[SupportedClaim] = Field(default_factory=list, max_length=12)
    gaps: list[str] = Field(default_factory=list, max_length=8)
    uncertainty: str = Field(default="", max_length=1000)


class TextJudgment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_index: int = Field(ge=0, le=11)
    status: Literal["supported", "unsupported", "conflicting"]
    facet_ids: list[str] = Field(default_factory=list, max_length=8)
    reason: str = Field(default="", max_length=300)


class JudgmentBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    judgments: list[TextJudgment] = Field(max_length=12)
    missing_requirements: list[str] = Field(default_factory=list, max_length=8)


class ClaimReview(BaseModel):
    claim: SupportedClaim
    status: Literal["supported", "unsupported", "conflicting", "stale"]
    reason: str
    facet_ids: list[str] = Field(default_factory=list)


class VerificationReport(BaseModel):
    supported: list[ClaimReview] = Field(default_factory=list)
    rejected: list[ClaimReview] = Field(default_factory=list)
    conflicts: list[ClaimReview] = Field(default_factory=list)
    covered_facet_ids: list[str] = Field(default_factory=list)
    semantic_verification: str = "source_only"


def fresh(ctx, evidence):
    scope = guard(ctx)
    ref = evidence.source_ref
    asset = get_record(scope, ref.asset_id, "asset")
    if asset["domain_id"] != ref.domain_id:
        return False
    if evidence.content_kind == "metadata":
        return ref.locator == "metadata" and ref.version == version(
            asset["name"] + ". " + asset["description"]
        )
    if ref.locator.startswith("aggregate:"):
        from app.knowledge.tools import query_dataset

        operation = evidence.provenance.get("operation")
        if not operation:
            return False
        result = query_dataset(ctx, QueryDatasetAction(query=operation))
        return (
            bool(result.source_refs)
            and result.source_refs[0] == ref
            and result.items[0]["values"] == evidence.values
        )
    if evidence.content_kind == "structured":
        rows = query(
            "SELECT payload FROM business_rows WHERE id=:id AND asset_id=:asset",
            {"id": ref.locator, "asset": ref.asset_id},
        )
        return (
            bool(rows)
            and version(rows[0]["payload"]) == ref.version
            and all(
                key in rows[0]["payload"] and rows[0]["payload"][key] == value
                for key, value in (evidence.values or {}).items()
            )
        )
    return source_ref_is_current(scope, ref)


def live_content(ctx, evidence):
    scope = guard(ctx)
    ref = evidence.source_ref
    if evidence.content_kind == "document":
        iterator = iter_document_sections(scope, ref.asset_id)
        try:
            for section in iterator:
                guard(ctx)
                if section["locator"] == ref.locator:
                    # Require the actual read's version as well as preceding stat.
                    if section["source_ref"]["version"] != ref.version:
                        return ""
                    return section["title"] + "\n" + section["text"]
        finally:
            iterator.close()
        return ""
    if evidence.content_kind == "metadata":
        asset = get_record(scope, ref.asset_id, "asset")
        return asset["name"] + ". " + asset["description"]
    if ref.locator.startswith("aggregate:"):
        return json.dumps(evidence.values)
    rows = query(
        "SELECT payload FROM business_rows WHERE id=:id AND asset_id=:asset",
        {"id": ref.locator, "asset": ref.asset_id},
    )
    return json.dumps(rows[0]["payload"]) if rows else ""


def unit_for(field):
    return (
        "USD"
        if field.endswith("_usd")
        else "percent"
        if field.endswith("_percent")
        else "count"
        if field in ["count", "row_count", "headcount", "open_roles"]
        else "units"
    )


def equal_value(left, right):
    try:
        a, b = Decimal(str(left)), Decimal(str(right))
        return a.is_finite() and b.is_finite() and a == b
    except (InvalidOperation, ValueError, TypeError):
        return str(left) == str(right)


def money_values(text):
    pattern = r"(?i)(USD|EUR|GBP|\$|£)\s*([\d,]+(?:\.\d+)?)\s*(billion|million|thousand|bn|[mbk])?\b"
    output = []
    for currency, number, suffix in re.findall(pattern, text):
        multiplier = {
            "billion": 10**9,
            "bn": 10**9,
            "b": 10**9,
            "million": 10**6,
            "m": 10**6,
            "thousand": 1000,
            "k": 1000,
        }.get(suffix.lower(), 1)
        output.append(
            (
                {"$": "USD", "£": "GBP"}.get(currency, currency.upper()),
                Decimal(number.replace(",", "")) * multiplier,
            )
        )
    return output


def citation_error(claim, citation, evidence, actual):
    if citation.source_ref and citation.source_ref != evidence.source_ref:
        return "Citation source handle does not match the retrieved fragment"
    if citation.quote and (
        citation.quote not in evidence.text or citation.quote not in actual
    ):
        return "Quoted passage is not present at this source locator"
    if citation.field:
        try:
            values = json.loads(actual)
        except (ValueError, TypeError):
            return "Structured source could not be checked"
        if not isinstance(values, dict):
            return "Structured source is not a row or aggregate"
        if (
            citation.field not in values
            or citation.value is None
            or not equal_value(values[citation.field], citation.value)
        ):
            return "Claim field/value does not match the source"
        expected = values.get("unit") or unit_for(citation.field)
        if citation.unit and citation.unit != expected:
            return "Claim unit does not match the source"
        if citation.period and citation.period not in [
            str(v)
            for k, v in values.items()
            if k in ["as_of", "period", "reporting_period"] or k.endswith("_date")
        ]:
            return "Claim period does not match the source"
    elif not citation.quote:
        return "Citation requires an exact quote or structured field/value"
    return None


def numeric_error(claim, lookup):
    amounts = []
    dates = []
    percentages = []
    for citation in claim.citations:
        evidence = lookup[citation.evidence_id]
        amounts.extend(money_values(citation.quote or ""))
        dates.extend(re.findall(r"\b\d{4}-\d{2}-\d{2}\b", citation.quote or ""))
        values = evidence.values or {}
        dates.extend(str(v) for v in values.values())
        percentages.extend(
            Decimal(n) for n in re.findall(r"(\d+(?:\.\d+)?)\s*%", citation.quote or "")
        )
        if citation.field:
            unit = values.get("unit") or unit_for(citation.field)
            if unit in ["USD", "EUR", "GBP"]:
                amounts.append((unit, Decimal(str(values[citation.field]))))
            if unit == "percent":
                percentages.append(Decimal(str(values[citation.field])))
    if any(value not in amounts for value in money_values(claim.text)):
        return "Claim currency or amount is not supported by its source citations"
    if any(d not in dates for d in re.findall(r"\b\d{4}-\d{2}-\d{2}\b", claim.text)):
        return "Claim date is not supported by the cited passages or rows"
    if any(
        Decimal(n) not in percentages
        for n in re.findall(r"(\d+(?:\.\d+)?)\s*%", claim.text)
    ):
        return "Claim percentage is not supported by its source citations"
    return None


def governance_current(ctx, claim, paths, lookup):
    if not claim.governance_paths:
        return False
    from app.knowledge.graph import traverse_graph

    known = {
        tuple([p["edges"][0]["source"]] + [e["target"] for e in p["edges"]]): p
        for p in paths
        if p.get("edges")
    }
    for nodes in claim.governance_paths:
        path = known.get(tuple(nodes))
        if not path or not 2 <= len(nodes) <= 4:
            return False
        edges = path["edges"]
        governing = [e for e in edges if e["predicate"] == "governedBy"]
        if not governing:
            return False
        for edge in governing:
            try:
                target = get_record(guard(ctx), edge["target"], "entity")
            except HTTPException as error:
                if error.status_code in [403, 404]:
                    return False
                raise
            if target.get("entity_type") != "Policy":
                return False
        local = ctx.model_copy(update={"graph_nodes": set(), "graph_edges": set()})
        result = traverse_graph(
            local,
            [nodes[0]],
            list({e["predicate"] for e in edges}),
            [],
            depth=len(edges),
        )

        def triples(p):
            return [
                (e["source"], e["predicate"], e["target"], e["source_ref"])
                for e in p["edges"]
            ]

        if not any(triples(p) == triples(path) for p in result.paths):
            return False
        cited = [lookup[c.evidence_id].source_ref for c in claim.citations]
        if not any(
            r.asset_id == edge["source_ref"]["asset_id"]
            and r.version == edge["source_ref"]["version"]
            for r in cited
            for edge in governing
        ):
            return False
    return True


def verify_claims(
    ctx,
    claims,
    evidence,
    judge=None,
    paths=None,
    required_facets=None,
    require_governance=False,
):
    guard(ctx)
    report = VerificationReport()
    lookup = {e.id: e for e in evidence}
    valid = []
    cache = {}
    for claim in claims:
        reason = ""
        status = "unsupported"
        for citation in claim.citations:
            e = lookup.get(citation.evidence_id)
            if not e:
                reason = "Citation refers to unavailable evidence"
                break
            key = (e.asset_id, e.source_ref.version, e.source_ref.locator)
            if key not in cache:
                if not fresh(ctx, e):
                    cache[key] = (False, "")
                else:
                    cache[key] = (True, live_content(ctx, e))
            current, actual = cache[key]
            if not current:
                reason = "Source changed since it was retrieved"
                status = "stale"
                break
            reason = citation_error(claim, citation, e, actual) or ""
            if reason:
                break
        if not reason:
            reason = numeric_error(claim, lookup) or ""
        if not reason and (
            require_governance
            or claim.governance_paths
            or re.search(
                r"\b(governs?|governing|applicable policy)\b", claim.text, re.I
            )
        ):
            if not governance_current(ctx, claim, paths or [], lookup):
                reason = "No current source-backed governing policy path supports applicability"
        if reason:
            report.rejected.append(
                ClaimReview(claim=claim, status=status, reason=reason)
            )
        else:
            valid.append(claim)
    if valid and judge:
        judgments = judge(
            valid,
            [
                lookup[id]
                for id in dict.fromkeys(
                    c.evidence_id for claim in valid for c in claim.citations
                )
            ],
        )
        by_index = {}
        for j in judgments:
            j = TextJudgment.model_validate(j)
            if j.claim_index in by_index or j.claim_index >= len(valid):
                raise ValueError(
                    "Semantic verifier returned invalid or duplicate claim indices"
                )
            by_index[j.claim_index] = j
        report.semantic_verification = "model_assessed"
        for n, claim in enumerate(valid):
            j = by_index.get(n)
            status = j.status if j else "unsupported"
            facets = [
                f
                for f in (j.facet_ids if j else [])
                if required_facets is None or f in required_facets
            ]
            review = ClaimReview(
                claim=claim,
                status=status,
                reason=j.reason if j else "Verifier did not assess this claim",
                facet_ids=facets,
            )
            if status == "supported":
                report.supported.append(review)
            elif status == "conflicting":
                report.conflicts.append(review)
            else:
                report.rejected.append(review)
    else:
        for claim in valid:
            exact = all(c.quote == claim.text for c in claim.citations)
            review = ClaimReview(
                claim=claim,
                status="supported" if exact else "unsupported",
                reason="Exact source excerpt"
                if exact
                else "Textual support has not been verified",
            )
            (report.supported if exact else report.rejected).append(review)
    report.covered_facet_ids = sorted(
        {f for r in report.supported for f in r.facet_ids}
    )
    guard(ctx)
    return report
