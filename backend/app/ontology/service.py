from pathlib import Path
from rdflib import Graph, Namespace, Literal, RDF, RDFS, OWL, URIRef
from pyshacl import validate
import httpx
from fastapi import HTTPException
from app.config import settings
from app.db import query
from app.catalog.service import all_records
K=Namespace('https://atlas.example/ontology/')
I=Namespace('https://atlas.example/id/')
CONCEPTS=['Counterparty','Contract','Obligation','Service','Exposure','Policy','Person','Project','Product','DataElement']
CLASSES=['Domain','Subdomain','KnowledgeProduct','Asset','StructuredAsset','Document','Source','Gap','Role']+CONCEPTS
RELATIONS={'belongsToDomain':('Asset','Domain'),'belongsToSubdomain':('KnowledgeProduct','Subdomain'),'usesAsset':('KnowledgeProduct','Asset'),'sourcedFrom':('Asset','Source'),'representsConcept':('Asset','DataElement'),'stewardedBy':('Asset','Person'),'deliversProduct':('Project','KnowledgeProduct'),'hasGap':('KnowledgeProduct','Gap'),'relatedTo':('DataElement','DataElement')}

def sync_ontology():
    vocab=Graph();vocab.bind('atlas',K)
    for c in CLASSES:vocab.add((K[c],RDF.type,OWL.Class));vocab.add((K[c],RDFS.label,Literal(c)))
    for p,(d,r) in RELATIONS.items():
        vocab.add((K[p],RDF.type,OWL.ObjectProperty));vocab.add((K[p],RDFS.label,Literal(p)));vocab.add((K[p],RDFS.domain,K[d]));vocab.add((K[p],RDFS.range,K[r]))
    instances=Graph();instances.bind('atlas',K);instances.bind('id',I)
    for row in query('SELECT * FROM records ORDER BY id'):
        if row['kind']=='role':continue
        p=row['payload'];node=I[row['id']];kind={'product':'KnowledgeProduct','subdomain':'Subdomain'}.get(row['kind'],row['kind'].title())
        instances.add((node,RDF.type,K[kind]));instances.add((node,RDFS.label,Literal(p.get('name',row['id']))))
        if row['domain_id']:instances.add((node,K.belongsToDomain,I[row['domain_id']]))
        if p.get('subdomain_id'):instances.add((node,K.belongsToSubdomain,I[p['subdomain_id']]))
        if row['kind']=='asset':
            instances.add((node,RDF.type,K.Document if p['type']=='Document' else K.StructuredAsset))
            instances.add((node,K.sourcedFrom,I[p['source_id']]))
            if row['id']!='risk-asset-0':instances.add((node,K.stewardedBy,Literal(p['steward'])))
            for product in p['product_ids']:instances.add((I[product],K.usesAsset,node))
            for c in p['concepts']:instances.add((node,K.representsConcept,K[c]))
        if row['kind']=='project':instances.add((node,K.deliversProduct,I[p['product_id']]))
        if row['kind']=='gap':instances.add((I[p['product_id']],K.hasGap,node))
    for a,b in [('Counterparty','Exposure'),('Counterparty','Contract'),('Contract','Obligation'),('Exposure','Policy'),('Service','Policy')]:instances.add((K[a],K.relatedTo,K[b]))
    for name,graph in [('vocabulary',vocab),('instances',instances)]:
        httpx.put(settings().fuseki_url+'/data',params={'graph':f'https://atlas.example/graphs/{name}'},content=graph.serialize(format='turtle'),headers={'Content-Type':'text/turtle'},timeout=30).raise_for_status()
    Path(__file__).with_name('vocabulary.ttl').write_text(vocab.serialize(format='turtle'))
    return {'triples':len(vocab)+len(instances)}

def rdf_graph(scope):
    r=httpx.get(settings().fuseki_url+'/query',params={'query':'CONSTRUCT { ?s ?p ?o } WHERE { GRAPH ?g { ?s ?p ?o } }'},headers={'Accept':'text/turtle'},timeout=10);r.raise_for_status()
    full=Graph().parse(data=r.text,format='turtle');allowed={r['id'] for r in all_records(scope) if r['kind']!='role'};g=Graph();g.bind('atlas',K);g.bind('id',I)
    def permitted(term):return not isinstance(term,URIRef) or not str(term).startswith(str(I)) or str(term)[len(str(I)):] in allowed
    for s,p,o in full:
        if permitted(s) and permitted(o):g.add((s,p,o))
    return g

def resolve_concepts(scope,labels):
    return [c for c in CONCEPTS if any(c.lower() in label.lower() for label in labels)]

def explore_ontology(scope,concept_id='Counterparty',depth=1,limit=50):
    if not 1<=depth<=3 or not 1<=limit<=100:raise HTTPException(422,'Invalid graph bounds')
    g=rdf_graph(scope);root=K[concept_id] if concept_id in CLASSES else I[concept_id]
    if not any(g.triples((root,None,None))) and not any(g.triples((None,None,root))):raise HTTPException(404,'Concept or asset not found')
    def node_info(uri):
        id=str(uri).replace(str(I),'').replace(str(K),'')
        label=str(g.value(uri,RDFS.label) or id)
        types=list(g.objects(uri,RDF.type));kind=str(types[0]).split('/')[-1] if types else 'Concept'
        if str(uri).startswith(str(K)):kind='Concept'
        return {'id':id,'iri':str(uri),'name':label,'kind':kind}
    selected={root};front={root};edges=[];truncated=False
    for _ in range(depth):
        next_front=set()
        triples=sorted(set(t for n in front for t in list(g.triples((n,None,None)))+list(g.triples((None,None,n)))),key=lambda t:tuple(map(str,t)))
        for s,p,o in triples:
            if p not in [K[x] for x in RELATIONS] or not isinstance(o,URIRef) or s==o:continue
            required={s,o}-selected
            if len(selected)+len(required)>limit:truncated=True;continue
            selected.update(required);next_front.update(required)
            edge={'source':node_info(s)['id'],'target':node_info(o)['id'],'label':str(p).split('/')[-1],'asserted':True}
            if edge not in edges:edges.append(edge)
        front=next_front
    return {'nodes':sorted([node_info(n) for n in selected],key=lambda n:(n['id']!=concept_id,n['name'])),'edges':edges,'truncated':truncated,'root':concept_id}

def validate_ontology(scope=None):
    if scope is None:
        from app.auth import resolve_scope
        scope=resolve_scope('admin')
    g=rdf_graph(scope)
    shape=Graph().parse(Path(__file__).with_name('shapes.ttl'),format='turtle')
    conforms,report,_=validate(g,shacl_graph=shape)
    SH=Namespace('http://www.w3.org/ns/shacl#');findings=[]
    for result in report.subjects(RDF.type,SH.ValidationResult):
        node=report.value(result,SH.focusNode);message=report.value(result,SH.resultMessage)
        findings.append({'asset_id':str(node).replace(str(I),''),'rule':'Required stewardship','message':str(message),'severity':'Warning'})
    return findings
