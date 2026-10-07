import json,time,uuid,threading
from concurrent.futures import ThreadPoolExecutor
from langgraph.checkpoint.postgres import PostgresSaver
from fastapi import HTTPException
from app.db import query
from app.config import settings
from app.agent.graph import build_graph,RunCancelled,ScopeChanged
from app.agent.provider import ConfigurationRequired,ModelRefusal
from app.auth import resolve_scope
from app.contracts import SearchRequest
executor=ThreadPoolExecutor(max_workers=2)
_setup_lock=threading.Lock()


def raw_run(id):
    rows=query('SELECT payload FROM search_runs WHERE id=:id',{'id':id})
    if not rows:raise HTTPException(404,'Search run not found')
    return rows[0]['payload']

def patch_run(id,patch):
    query('UPDATE search_runs SET payload=payload || CAST(:patch AS jsonb) WHERE id=:id RETURNING id',{'id':id,'patch':json.dumps(patch)})

def event(id,stage,status,summary):
    e={'stage':stage,'status':status,'summary':summary,'at':time.time()}
    # One runner per run; PostgreSQL append avoids losing cancellation updates.
    query("UPDATE search_runs SET payload=jsonb_set(payload,'{events}', (payload->'events') || CAST(:e AS jsonb)) WHERE id=:id RETURNING id",{'id':id,'e':json.dumps([e])})

def get_search(scope,run_id):
    run=raw_run(run_id)
    if run['person_id']!=scope.person_id:raise HTTPException(404,'Search run not found')
    current=resolve_scope(scope.person_id)
    if current.scope_version!=run['scope_version']:raise HTTPException(409,'Access scope changed; run evidence is no longer available')
    run=dict(run)
    for i,e in enumerate(run['events']):e['sequence']=i+1
    run.pop('scope_version',None);run.pop('person_id',None)
    return run

def start_search(scope,request):
    request=SearchRequest.model_validate(request)
    id=str(uuid.uuid4());run={'run_id':id,'person_id':scope.person_id,'scope_version':scope.scope_version,'query':request.query,'mode':request.mode,'status':'pending','statements':[],'evidence':[],'gaps':[],'events':[],'graph':{'nodes':[],'edges':[]},'created_at':time.time()}
    query('INSERT INTO search_runs(id,person_id,payload) VALUES(:id,:person,CAST(:payload AS jsonb)) RETURNING id',{'id':id,'person':scope.person_id,'payload':json.dumps(run)})
    executor.submit(execute_run,id)
    return get_search(scope,id)

def execute_run(id):
    run=raw_run(id)
    if run['status']=='cancelled':return
    patch_run(id,{'status':'running'})
    conn=settings().database_url.replace('postgresql+psycopg://','postgresql://')
    try:
        with PostgresSaver.from_conn_string(conn) as saver:
            with _setup_lock:saver.setup()
            graph=build_graph(saver,event,raw_run)
            state={'run_id':id,'person_id':run['person_id'],'scope_version':run['scope_version'],'query':run['query'],'mode':run['mode'],'started':time.time(),'evidence':[]}
            output=graph.invoke(state,config={'configurable':{'thread_id':id},'recursion_limit':24})
        if raw_run(id)['status']=='cancelled':return
        patch_run(id,{'status':'completed','statements':output.get('statements',[]),'evidence':output.get('evidence',[]),'gaps':output.get('gaps',[]),'uncertainty':output.get('uncertainty',''),'graph':output.get('graph',{}),'retrieval_passes':output['retrieval_passes'],'tool_calls':output['tool_calls']})
        event(id,'finish','completed','Search completed with validated citations')
    except RunCancelled:patch_run(id,{'status':'cancelled'})
    except Exception as e:
        status='configuration_required' if isinstance(e,ConfigurationRequired) else 'refused' if isinstance(e,ModelRefusal) else 'scope_changed' if isinstance(e,ScopeChanged) else 'failed'
        message=str(e) if isinstance(e,(ConfigurationRequired,ModelRefusal,ScopeChanged,TimeoutError,ValueError)) else 'A search dependency failed. Check service readiness and server logs.'
        import logging
        logging.getLogger(__name__).exception('Search run %s failed',id)
        if raw_run(id)['status']!='cancelled':patch_run(id,{'status':status,'error':message,'statements':[],'evidence':[]})
        event(id,'finish',status,message)

def cancel_search(scope,run_id):
    run=get_search(scope,run_id)
    if run['status'] in ['pending','running']:patch_run(run_id,{'status':'cancelled'});event(run_id,'finish','cancelled','Search cancelled')
    return get_search(scope,run_id)
