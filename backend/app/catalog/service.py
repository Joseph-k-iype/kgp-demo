import json
from fastapi import HTTPException
from pydantic import ValidationError
from app.db import query
from app.contracts import CatalogQuery
from app.auth import can_view, require_edit

def unpack(row):
    return {**row['payload'], 'id': row['id'], 'kind': row['kind'], 'domain_id': row['domain_id'], 'updated_at': str(row['updated_at'])}

def all_records(scope, kind=None):
    rows = query('SELECT * FROM records WHERE (CAST(:kind AS text) IS NULL OR kind=CAST(:kind AS text)) AND (domain_id IS NULL OR domain_id=ANY(:domains))', {'kind':kind,'domains':scope.domain_ids})
    return [unpack(row) for row in rows]

def get_record(scope, record_id, kind=None):
    rows = query('SELECT * FROM records WHERE id=:id', {'id':record_id})
    if not rows or not can_view(scope, rows[0]) or (kind and rows[0]['kind'] != kind): raise HTTPException(404, 'Record not found in your scope')
    return unpack(rows[0])

def list_catalog(scope, filters):
    f = CatalogQuery.model_validate(filters)
    items = all_records(scope, f.kind)
    for field in ['domain_id','subdomain_id','source_id','owner_id','status','classification']:
        value = getattr(f, field)
        if value: items = [r for r in items if r.get(field) == value]
    if f.quality:
        items = [r for r in items if ('attention' if r.get('quality',100)<90 else 'healthy') == f.quality]
    if f.text:
        terms = f.text.lower().split()
        items = [r for r in items if all(t in (r.get('name','')+' '+r.get('description','')+' '+' '.join(r.get('tags',[]))).lower() for t in terms)]
    items.sort(key=lambda r: r.get({'updated':'updated_at','quality':'quality'}.get(f.sort,'name'),''), reverse=f.sort=='updated')
    total = len(items); start=(f.page-1)*f.page_size
    return {'items':items[start:start+f.page_size], 'total':total, 'page':f.page,'page_size':f.page_size}

def get_product(scope, product_id):
    p = get_record(scope,product_id,'product')
    p['assets'] = [a for a in all_records(scope,'asset') if product_id in a.get('product_ids',[])]
    p['projects'] = [a for a in all_records(scope,'project') if a.get('product_id')==product_id]
    p['gaps'] = [a for a in all_records(scope,'gap') if a.get('product_id')==product_id]
    return p

def get_asset(scope, asset_id):
    a = get_record(scope,asset_id,'asset')
    a['source'] = get_record(scope,a['source_id'],'source')
    a['issues'] = [r for r in all_records(scope,'issue') if r.get('asset_id')==asset_id]
    a['products'] = [get_record(scope,p,'product') for p in a['product_ids'] if any(r['id']==p for r in all_records(scope,'product'))]
    return a

def list_domains(scope):
    domains = all_records(scope,'domain'); products=all_records(scope,'product'); assets=all_records(scope,'asset')
    for d in domains:
        d['product_count']=sum(p['domain_id']==d['id'] for p in products)
        d['asset_count']=sum(a['domain_id']==d['id'] for a in assets)
        d['subdomains']=[s for s in all_records(scope,'subdomain') if s['domain_id']==d['id']]
    return domains

def update_metadata(scope, kind, record_id, patch):
    record=get_record(scope,record_id,kind);require_edit(scope,record,kind)
    allowed={'project': {'name','description','status','budget','currency','sponsor','subdomain_id'}, 'gap':{'description','status','owner','tags'}, 'role':{'role','domain_ids'}, 'product':{'description','status','tags','steward'}}
    if kind not in allowed or not patch or set(patch)-allowed[kind]: raise HTTPException(422,'Unsupported edit')
    if 'budget' in patch and (not isinstance(patch['budget'],(int,float)) or isinstance(patch['budget'],bool) or not 0<=patch['budget']<=1e12): raise HTTPException(422,'Invalid budget')
    if 'subdomain_id' in patch and get_record(scope,patch['subdomain_id'],'subdomain')['domain_id']!=record['domain_id']:raise HTTPException(422,'Subdomain must belong to product domain')
    if 'status' in patch and patch['status'] not in ['Active','Draft','In development','Planned','In progress','Completed','Open','Resolved']:raise HTTPException(422,'Invalid status')
    if 'role' in patch and patch['role'] not in ['Administrator','Analyst','Domain steward','Delegate','Product owner','Reviewer']:raise HTTPException(422,'Invalid role')
    if 'domain_ids' in patch:
        from app.auth import DOMAINS
        if not isinstance(patch['domain_ids'],list) or any(d not in DOMAINS for d in patch['domain_ids']):raise HTTPException(422,'Invalid domain scope')
    if kind=='role':patch['scope_version']=record.get('scope_version',1)+1
    query('UPDATE records SET payload=payload || CAST(:patch AS jsonb), updated_at=now() WHERE id=:id RETURNING id',{'id':record_id,'patch':json.dumps(patch)})
    if kind=='product':
        query("UPDATE records SET payload=jsonb_set(payload,'{indexing_state}','\"stale\"') WHERE kind='asset' AND payload->'product_ids' @> CAST(:p AS jsonb) RETURNING id",{'p':json.dumps([record_id])})
    return get_record(scope,record_id)

def overview(scope):
    records=all_records(scope)
    counts={kind:sum(r['kind']==kind for r in records) for kind in ['domain','product','asset','source','gap','project','issue']}
    return {'counts':counts, 'domains':list_domains(scope), 'attention':[r for r in records if r['kind']=='gap' and r['status']=='Open'][:6], 'recent':sorted([r for r in records if r['kind']=='product'], key=lambda r:r['updated_at'],reverse=True)[:5], 'indexed':sum(r['kind']=='asset' and r.get('indexing_state')=='ready' for r in records)}
