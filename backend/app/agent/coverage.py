from app.knowledge.contracts import SearchIntentV2, EvidenceFragment, CoverageReport


def assess_coverage(
    intent: SearchIntentV2, evidence: list[EvidenceFragment]
) -> CoverageReport:
    supported = []
    relevant = set()
    for facet in intent.facets:
        for item in evidence:
            if facet.id in item.matched_facet_ids and (
                not facet.kinds or item.content_kind in facet.kinds
            ):
                relevant.add(item.id)
                if facet.id not in supported:
                    supported.append(facet.id)
    missing = [f for f in intent.facets if f.id not in supported]
    return CoverageReport(
        supported_facet_ids=supported,
        uncovered_facet_ids=[f.id for f in missing],
        irrelevant_ids=[e.id for e in evidence if e.id not in relevant],
        suggested_source_needs=[f.description for f in missing],
    )
