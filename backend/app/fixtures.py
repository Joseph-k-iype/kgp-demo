DOMAINS = [
('risk','Risk and Compliance','Control risk, regulatory obligations and enterprise exposures.','Priya Shah',['Credit Risk','Financial Crime','Regulatory Compliance'],['Counterparty Risk Intelligence','Financial Crime Signals','Regulatory Obligations','Enterprise Risk Register'],'Counterparty'),
('legal','Legal','Connect contracts, legal obligations and advisory knowledge.','Marcus Chen',['Contracts','Legal Advisory','Litigation'],['Contract Obligations','Legal Matter Intelligence','Clause Library','Litigation Insights'],'Contract'),
('technology','Technology','Understand applications, infrastructure and technology resilience.','Sofia Andersson',['Applications','Infrastructure','Cybersecurity'],['Technology Service Health','Application Estate','Cyber Threat Intelligence','Infrastructure Capacity'],'Service'),
('product','Product','Govern the lifecycle, performance and controls of enterprise products.','Daniel Brooks',['Product Management','Product Analytics','Product Controls'],['Product Performance','Product Taxonomy','Pricing Intelligence','Product Control Evidence'],'Product'),
('operations','Services and Operations','Improve service delivery and operational resilience.','Amara Okafor',['Service Delivery','Operational Resilience','Process Management'],['Operational Resilience','Service Delivery Intelligence','Process Performance','Incident Knowledge'],'Service'),
('data','Data and Information','Define enterprise information, quality and data stewardship.','Wei Lin',['Data Governance','Information Management','Data Quality'],['Enterprise Data Dictionary','Data Quality Intelligence','Information Classification','Data Lineage Registry'],'DataElement'),
('finance','Finance Treasury and Enterprise Tax','Connect liquidity, financial reporting and enterprise tax obligations.','Oliver Reed',['Treasury','Financial Control','Enterprise Tax'],['Treasury Liquidity','Financial Reporting','Enterprise Tax Obligations','Capital Planning'],'Exposure'),
('people','People','Bring together workforce planning, policies and people operations.','Isabella Rossi',['Workforce Planning','People Operations','Learning'],['Workforce Planning','People Policy Library','Skills Intelligence','Employee Service Knowledge'],'Person'),
('third-party','Third Party and Support','Understand suppliers, support services and third party dependencies.','Aisha Rahman',['Third Party Risk','Procurement','Enterprise Support'],['Third Party Due Diligence','Supplier Performance','Procurement Intelligence','Support Service Knowledge'],'Counterparty'),
('strategy','Strategy and Change','Connect strategic objectives, investments and change delivery.','Gabriel Santos',['Strategy','Change Delivery','Portfolio Management'],['Change Portfolio','Strategic Objectives','Investment Intelligence','Benefits Realization'],'Project'),
('customer','Customer and Counterparty','Create trusted customer and counterparty context and relationships.','Emma Wilson',['Customer Intelligence','Counterparty Management','Relationship Management'],['Customer Relationship Intelligence','Counterparty Master','Customer Journey','Relationship Network'],'Counterparty')]

def make_fixtures():
    records=[]
    def add(id,kind,domain_id,**payload):
        records.append({'id':id,'kind':kind,'domain_id':domain_id,'payload':payload})
    for i,(d,name,desc,steward,subs,products,concept) in enumerate(DOMAINS):
        delegates=[DOMAINS[(i+1)%11][3],DOMAINS[(i+3)%11][3]]
        add(d,'domain',d,name=name,description=desc,steward=steward,delegates=delegates,color=['blue','violet','teal','amber'][i%4])
        for j,sub in enumerate(subs):add(f'{d}-sub-{j}','subdomain',d,name=sub,description=f'{sub} knowledge, governance and source evidence.',parent_id=d)
        for j,p in enumerate(products):
            add(f'{d}-product-{j}','product',d,name=p,description=f'{p} brings together governed {subs[j%3].lower()} records, reference definitions and supporting documents for evidence-based decisions.',subdomain_id=f'{d}-sub-{j%3}',steward=steward,owner_id=steward,status=['Active','Active','In development','Draft'][j],tags=[subs[j%3],concept,'governed'],classification='Internal',quality=97-(i*3+j)%16,concepts=[concept,'Policy' if j%2 else 'Exposure'],formats=['SQL','Document','RDF','Vector'],asset_count=0)
        add(f'{d}-sql','source',d,name=f'{subs[0]} PostgreSQL',description=f'Synthetic operational records for {name}.',type='PostgreSQL',system_of_record=True,storage_location='postgresql://atlas/business_rows',connection_state='Connected',steward=steward)
        add(f'{d}-minio','source',d,name=f'{subs[0]} Document Store',description=f'Synthetic policies, reports and supporting evidence for {name}.',type='MinIO',system_of_record=False,storage_location=f's3://atlas-knowledge/{d}/',connection_state='Connected',steward=steward)
        n=14 if i<7 else 13
        for j in range(n):
            p=j%4; kind=['Table','Document','Metadata','Data product'][j%4]
            asset_name = [products[p]+' · records',products[p]+' · evidence brief',products[p]+' · definitions',products[p]+' · curated dataset'][j%4]
            if d=='risk' and j==0:asset_name='counterparty_exposure'
            if d=='risk' and j==1:asset_name='Counterparty due diligence policy'
            if d=='third-party' and j==1:asset_name='Third party due diligence report'
            if j>=4:asset_name+=f' {j//4+1}'
            add(f'{d}-asset-{j}','asset',d,name=asset_name,description=f'{asset_name} supports {subs[p%3].lower()} decisions with {concept.lower()} context and accountable provenance.',type=kind,source_id=f'{d}-minio' if kind=='Document' else f'{d}-sql',subdomain_id=f'{d}-sub-{p%3}',product_ids=[f'{d}-product-{k}' for k in range(4)] if j<4 else [f'{d}-product-{p}'],steward=steward,owner_id=steward,status='Active',classification='Confidential' if j%5==0 else 'Internal',quality=98-(j*3+i)%19,tags=[concept,subs[p%3]],concepts=[concept,'Policy' if kind=='Document' else 'Exposure'],storage_location=f's3://atlas-knowledge/{d}/{d}-asset-{j}.txt' if kind=='Document' else f'postgresql://atlas/business_rows?asset_id={d}-asset-{j}',table='business_rows' if kind!='Document' else None,object_key=f'{d}/{d}-asset-{j}.txt' if kind=='Document' else None,indexing_state='pending',record_count=8 if kind!='Document' else None)
        add(f'{d}-project','project',d,name=products[0]+' delivery',description=f'Expand trusted coverage for {products[0]}.',product_id=f'{d}-product-0',knowledge_product_name=products[0],status='In progress' if i%3 else 'Planned',sponsor=delegates[0],budget=850000+i*125000,currency='USD',subdomain_id=f'{d}-sub-0',steward=steward)
        add(f'{d}-gap','gap',d,name=subs[0]+' evidence coverage',description=f'{2+i%3} required {subs[0].lower()} evidence sources remain uncovered. Remediation requires steward review and source onboarding.',coverage=round((8-i%3)/10*100),covered=8-i%3,required=10,coverage_basis='Required evidence sources',tags=['coverage','documentation',subs[0]],quality_issues=2+i%3,product_id=f'{d}-product-0',asset_ids=[f'{d}-asset-0'],owner=steward,status='Open')
        for j in range(2+i%3):add(f'{d}-issue-{j}','issue',d,name=['Missing steward evidence','Incomplete identifiers','Stale policy reference','Unmapped concept'][j],description=f'Synthetic governance finding {j+1} requiring review.',asset_id=f'{d}-asset-0',severity='High' if j==0 else 'Medium',status='Open')
    from app.auth import PERSONAS
    for id,(name,role,domains) in PERSONAS.items():add(f'role-{id}','role',None,name=name,role=role,domain_ids=domains,scope_version=1)
    for record in records:
        if record['kind']=='product':record['payload']['asset_count']=sum(record['id'] in a['payload'].get('product_ids',[]) for a in records if a['kind']=='asset')
    return records

def business_data(asset):
    return [{'record_id':f"{asset['id']}-row-{i}",'counterparty_id':f'CP-{1000+i}','counterparty_name':['Aster Capital','Meridian Holdings','Northbridge Trading','Cedar Partners'][i%4], 'exposure_usd':(i+1)*1250000,'risk_rating':['Low','Moderate','High'][i%3], 'review_status':'Reviewed' if i%3 else 'Evidence pending','as_of':'2026-09-30','domain':asset['domain_id']} for i in range(8)]

def document_text(asset):
    p=asset['payload']
    return f"""# {p['name']}
Synthetic enterprise evidence — Atlas demonstration data
Domain: {asset['domain_id']}
Steward: {p['steward']}
Concepts: {', '.join(p['concepts'])}

Purpose
{p['description']}

Control requirements
Every counterparty exposure must link to an approved due diligence record. Aster Capital (CP-1000) has a reported exposure of USD 1,250,000 and a High review priority. Meridian Holdings (CP-1001) has a reported exposure of USD 2,500,000. These are fictional entities and amounts. Due diligence includes legal ownership, sanctions screening, financial condition, and service dependencies.

Evidence and governance
The steward reviews records monthly. PostgreSQL stores the structured records; the source document is retained in MinIO. RDF concepts connect Counterparty, Exposure and Policy. Two required supporting evidence sources are missing, and unresolved data quality issues must be considered before use.

Domain-specific context
{p['name']} applies this evidence framework to {p['tags'][-1]}. Supporting assets are discoverable through the catalog and ontology explorer. Policy applicability must be confirmed by the assigned steward.
"""
