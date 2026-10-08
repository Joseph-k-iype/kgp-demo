# Implementation decisions and review

These decisions record the scope adaptations made while implementing the approved plan. They are retained for review rather than implying that live model quality passed its rollout gates.

- Ruling: reuse existing Finance document assets for richer policies rather than add unnecessary assets — stable150asset catalog, new entity/section records carry graph semantics — cost if wrong: generic asset display titles remain contextual until content-first viewer uses document titles. Ingestion/relevance versioning followsTask3.

- Task5: offline40developmentcases completederrors0, modelattempts0, retrievalrecall0.9375, p501.332s/p952.2s; alloutcomespartial/source-only versusgoldanswered/noevidence, so no modelqualityclaim. Artifact docs/evaluations/2026-10-08-development-offline.json includesper-casefailures/metrics. Ruling: offline adapterexploresrealgraph/sourcehandles conservatively andreturnsverbatimexcerpts, nevergold-derivedverifiedanswers — cannotpretendthiscertifiesLMAsemantics; liveheld-outTask8 remainsrequired. Strengthenedtreasuryheldoutgoldpathrequirements tobothTL001/TF002matchingitsoriginaltwofacts beforefirstlivebatch; oldbaselinecriterionwasonepath.

- Task8: Ruling: user explicitly authorized publishing all code and mock data to kgp-demo after verification; preserve existing origin and use a separate destination, no additional push approval. Add store snapshot/export/empty-target restore and detailed architecture/API/MCP/agentic/data documentation; exclude secrets and runtime model history.

- Task8: Ruling: V3.2 routes failed latency/native/schema checks; evaluate explicitly announced DeepSeek V4.1 Flash/Fireworks within approved DeepSeek family. Explicit JSON-object provider mode preserves complete prompt schema and strict server validation; no automatic paid replay. Typed native plan objects remove nested JSON escaping; old known receipts remain readable.

- Task8: Ruling: graph paths expressed as alternating subject/predicate/object are accepted only against an exact retrieved/current proof, never by discarding predicates. Initial source page starts at the actual document header so current policy identification is evidence, rather than trusting metadata alone.

- Task8: Ruling: replace exact full-filter vector scoring with schema-v3 Lucene HNSW content alias, keep old content index for rollback. New alias is built completely before server reconfiguration; legacy metadata discovery index remains separate.

- Final review: fresh gpt-6-astra reviewed whole branch748928f..d1261cc; user explicitly requested immediate push before final review soinitialHEADpublished andfollow-upfixesauthorized. OneCriticalforeignRDFnamespaceidentityleak andthreeImportantaggregateopening/relationshipendpoints/clarificationpresentation findings accepted. Singlefixpass: unknownsubject/object/predicateURI andinvalidreifiedparticipants denybyexplicittrustedterms+authorizedrecordIRIs; countedonlyvisibledefinitionfacts; aggregatecitationrequiresownedrun/validatedoperation,reexecutesresultandboundedselection; same-surfacekeyboardrelatednodes+governingpaths restored; explicitclarificationquestion/refineaction. Eachfinding RED→GREEN. Backend159passed157.88s includingrealHTTP/stdio; typecheck/buildpassed; final34browsergateactive. NoMinorfindings. Reviewerdeclinedpaidqualitybeyondreportedfailures, productionloadclaims andconcurrentfinalgates; rulings: retainqualityflagoff/measureonlylocalbounds/verifyactualgatesourselves. No secondreview.

## Final review

A fresh gpt-6-astra review of the whole branch identified one Critical RDF namespace access issue and three Important content/UX issues. All entered one regression-driven fix pass: explicit RDF term and authorized-record mapping; aggregate result/selection reopening; source/target relationship navigation; visible clarification and query refinement. No Minor findings were raised. The reviewer did not certify paid-model quality or production throughput and did not run competing shared-state tests. Those are measured/documented separately.

The user explicitly authorized immediate publication before final test/review completion. The first published commit was d1261cc; the follow-up contains the review fixes and final code/browser test record. Release defaults keep graph_search_v2 disabled because live quality gates remain unmet.

Final visual QA also reproduced a real SSR/client opacity mismatch on direct source URLs under reduced motion. The modal now uses a deterministic initial opacity and a zero-duration reduced-motion transition; its console-error regression passed. Final gates:159 backend,35 browser, typecheck/build/static checks;27 responsive UI states with no overflow, page/console errors or read-only generation.
