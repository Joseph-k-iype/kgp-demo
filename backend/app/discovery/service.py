from collections import defaultdict
from app.auth import narrow_scope
from app.catalog.service import all_records
from app.ontology.service import resolve_concepts
from app.retrieval.service import retrieve
from app.discovery.contracts import DiscoveryQuery, DiscoveryItem, DiscoveryPage


def search_discovery(scope, query):
    query = DiscoveryQuery.model_validate(query)
    scope = narrow_scope(scope, query.domain_id)
    assets = {item['id']: item for item in all_records(scope, 'asset')}
    products = {item['id']: item for item in all_records(scope, 'product')}
    sources = {item['id']: item for item in all_records(scope, 'source')}
    records = {**assets, **products}
    concepts = resolve_concepts(scope, [query.q])
    hits = retrieve(scope, query.q, concepts, limit=30)
    metadata_rank = []
    terms = query.q.casefold().split()
    for item in records.values():
        text = ' '.join([item['name'].replace('_', ' '), item.get('description', ''), ' '.join(item.get('tags', []))]).casefold()
        if all(term in text for term in terms):
            metadata_rank.append(item['id'])
    metadata_rank.sort(key=lambda id: (records[id]['name'].casefold(), id))
    evidence_rank = []
    excerpts = {}
    for hit in hits:
        asset = assets.get(hit['asset_id'])
        if not asset:
            continue
        if asset['id'] not in excerpts:
            excerpts[asset['id']] = hit
            evidence_rank.append(asset['id'])
        for id in asset.get('product_ids', []):
            if id in products and id not in evidence_rank:
                evidence_rank.append(id)
    scores = defaultdict(float)
    for ranking in [metadata_rank, evidence_rank]:
        ranking = [id for id in ranking if query.type == "all" or ("product" if id in products else ("document" if records[id].get("type") == "Document" else "data")) == query.type]
        for rank, id in enumerate(ranking):
            scores[id] += 1 / (60 + rank)
    ordered = sorted(scores, key=lambda id: (-scores[id], id))[:100]
    results = []
    for id in ordered:
        item = records[id]
        is_product = id in products
        kind = 'product' if is_product else ('document' if item.get('type') == 'Document' else 'data')
        if query.type != 'all' and kind != query.type:
            continue
        evidence = excerpts.get(id)
        source = sources.get(item.get('source_id'), {})
        results.append(DiscoveryItem(
            id=id, kind=kind, title=item['name'],
            excerpt=evidence['text'][:420] if evidence else item.get('description', ''),
            domain_id=item['domain_id'], source_type='Knowledge product' if is_product else source.get('type', item.get('type', 'Metadata')),
            asset_id=None if is_product else id, product_id=id if is_product else None,
            evidence_id=evidence['id'] if evidence else None,
            steward=item.get('steward') or item.get('owner'), quality=item.get('quality'), score=round(scores[id], 6),
        ))
    if query.sort == 'name':
        results.sort(key=lambda item: (item.title.casefold(), item.id))
    start = (query.page - 1) * query.page_size
    page = results[start:start + query.page_size]
    return DiscoveryPage(items=page, returned_count=len(page), has_more=start+len(page)<len(results), page=query.page, page_size=query.page_size, query=query.q, domain_id=query.domain_id)
