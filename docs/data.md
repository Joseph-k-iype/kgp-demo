# Mock data and restoration

Everything in the supplied snapshot is synthetic. [data/demo/manifest.json](../data/demo/manifest.json) records counts and SHA-256 digests. It includes catalog metadata, PostgreSQL business rows, both Fuseki RDF named graphs and actual MinIO text documents. The ontology vocabulary and SHACL shapes, fixture generators and development/held-out gold cases are also checked into the repository.

Excluded: `.env`, real provider keys, database volume binaries, search runs/checkpoints, raw model receipts/private reasoning, jobs, embedding/model caches and OpenSearch data directories. OpenSearch projections are derived and rebuilt from the source snapshot. The supplied live evaluation reports contain public accepted claims, synthetic source handles and aggregate usage; they are not a user-history backup.

## Fresh installation from the snapshot

```sh
cp .env.example .env
make install
make up
make migrate
PYTHONPATH=backend uv run --project backend python scripts/demo_data.py validate
PYTHONPATH=backend uv run --project backend python scripts/demo_data.py restore --execute
make index
make dev
```

Restore requires an empty catalog database and never deletes existing records. Choose a separate PostgreSQL database, MinIO bucket and Fuseki dataset through server configuration for an isolated restore. Do not run `make seed` after restoring if you want the exact snapshot: fixture seeding refreshes synthetic source documents and business rows. `make seed` remains an alternative reproducible generator for a fresh demo.

Restore validates file digests, scoped object keys, record references and RDF parsing before writing. It restores managed MinIO SHA metadata so source versions and graph assertions retain their bindings. Cross-store restoration is not a distributed transaction; keep the app stopped until it succeeds and rebuild derived indexes afterwards. Snapshot export captures catalog/rows in one PostgreSQL repeatable-read transaction, and verifies each managed object digest; stop source mutation while exporting for a coherent RDF/object snapshot.

## Export another synthetic snapshot

```sh
PYTHONPATH=backend uv run --project backend python scripts/demo_data.py export --directory data/new-snapshot
PYTHONPATH=backend uv run --project backend python scripts/demo_data.py validate --directory data/new-snapshot
```

Export refuses an existing destination. It selects only catalog/business source tables and the two configured graph names, rather than dumping runtime state. Inspect content before committing any non-demo data. The supplied fixture material includes named active/superseded policies, treasury positions, counterparties, contracts, exceptions, ownership and deliberate governance/quality gaps.
