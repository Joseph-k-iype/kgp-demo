DOMAINS = [
    (
        "risk",
        "Risk and Compliance",
        "Control risk, regulatory obligations and enterprise exposures.",
        "Priya Shah",
        ["Credit Risk", "Financial Crime", "Regulatory Compliance"],
        [
            "Counterparty Risk Intelligence",
            "Financial Crime Signals",
            "Regulatory Obligations",
            "Enterprise Risk Register",
        ],
        "Counterparty",
    ),
    (
        "legal",
        "Legal",
        "Connect contracts, legal obligations and advisory knowledge.",
        "Marcus Chen",
        ["Contracts", "Legal Advisory", "Litigation"],
        [
            "Contract Obligations",
            "Legal Matter Intelligence",
            "Clause Library",
            "Litigation Insights",
        ],
        "Contract",
    ),
    (
        "technology",
        "Technology",
        "Understand applications, infrastructure and technology resilience.",
        "Sofia Andersson",
        ["Applications", "Infrastructure", "Cybersecurity"],
        [
            "Technology Service Health",
            "Application Estate",
            "Cyber Threat Intelligence",
            "Infrastructure Capacity",
        ],
        "Service",
    ),
    (
        "product",
        "Product",
        "Govern the lifecycle, performance and controls of enterprise products.",
        "Daniel Brooks",
        ["Product Management", "Product Analytics", "Product Controls"],
        [
            "Product Performance",
            "Product Taxonomy",
            "Pricing Intelligence",
            "Product Control Evidence",
        ],
        "Product",
    ),
    (
        "operations",
        "Services and Operations",
        "Improve service delivery and operational resilience.",
        "Amara Okafor",
        ["Service Delivery", "Operational Resilience", "Process Management"],
        [
            "Operational Resilience",
            "Service Delivery Intelligence",
            "Process Performance",
            "Incident Knowledge",
        ],
        "Service",
    ),
    (
        "data",
        "Data and Information",
        "Define enterprise information, quality and data stewardship.",
        "Wei Lin",
        ["Data Governance", "Information Management", "Data Quality"],
        [
            "Enterprise Data Dictionary",
            "Data Quality Intelligence",
            "Information Classification",
            "Data Lineage Registry",
        ],
        "DataElement",
    ),
    (
        "finance",
        "Finance Treasury and Enterprise Tax",
        "Connect liquidity, financial reporting and enterprise tax obligations.",
        "Oliver Reed",
        ["Treasury", "Financial Control", "Enterprise Tax"],
        [
            "Treasury Liquidity",
            "Financial Reporting",
            "Enterprise Tax Obligations",
            "Capital Planning",
        ],
        "Exposure",
    ),
    (
        "people",
        "People",
        "Bring together workforce planning, policies and people operations.",
        "Isabella Rossi",
        ["Workforce Planning", "People Operations", "Learning"],
        [
            "Workforce Planning",
            "People Policy Library",
            "Skills Intelligence",
            "Employee Service Knowledge",
        ],
        "Person",
    ),
    (
        "third-party",
        "Third Party and Support",
        "Understand suppliers, support services and third party dependencies.",
        "Aisha Rahman",
        ["Third Party Risk", "Procurement", "Enterprise Support"],
        [
            "Third Party Due Diligence",
            "Supplier Performance",
            "Procurement Intelligence",
            "Support Service Knowledge",
        ],
        "Counterparty",
    ),
    (
        "strategy",
        "Strategy and Change",
        "Connect strategic objectives, investments and change delivery.",
        "Gabriel Santos",
        ["Strategy", "Change Delivery", "Portfolio Management"],
        [
            "Change Portfolio",
            "Strategic Objectives",
            "Investment Intelligence",
            "Benefits Realization",
        ],
        "Project",
    ),
    (
        "customer",
        "Customer and Counterparty",
        "Create trusted customer and counterparty context and relationships.",
        "Emma Wilson",
        ["Customer Intelligence", "Counterparty Management", "Relationship Management"],
        [
            "Customer Relationship Intelligence",
            "Counterparty Master",
            "Customer Journey",
            "Relationship Network",
        ],
        "Counterparty",
    ),
]


def make_fixtures():
    records = []

    def add(id, kind, domain_id, **payload):
        records.append(
            {"id": id, "kind": kind, "domain_id": domain_id, "payload": payload}
        )

    for i, (d, name, desc, steward, subs, products, concept) in enumerate(DOMAINS):
        delegates = [DOMAINS[(i + 1) % 11][3], DOMAINS[(i + 3) % 11][3]]
        add(
            d,
            "domain",
            d,
            name=name,
            description=desc,
            steward=steward,
            delegates=delegates,
            color=["blue", "violet", "teal", "amber"][i % 4],
        )
        for j, sub in enumerate(subs):
            add(
                f"{d}-sub-{j}",
                "subdomain",
                d,
                name=sub,
                description=f"{sub} knowledge, governance and source evidence.",
                parent_id=d,
            )
        for j, p in enumerate(products):
            add(
                f"{d}-product-{j}",
                "product",
                d,
                name=p,
                description=f"{p} brings together governed {subs[j % 3].lower()} records, reference definitions and supporting documents for evidence-based decisions.",
                subdomain_id=f"{d}-sub-{j % 3}",
                steward=steward,
                owner_id=steward,
                status=["Active", "Active", "In development", "Draft"][j],
                tags=[subs[j % 3], concept, "governed"],
                classification="Internal",
                quality=97 - (i * 3 + j) % 16,
                concepts=[concept, "Policy" if j % 2 else "Exposure"],
                formats=["SQL", "Document", "RDF", "Vector"],
                asset_count=0,
            )
        add(
            f"{d}-sql",
            "source",
            d,
            name=f"{subs[0]} PostgreSQL",
            description=f"Synthetic operational records for {name}.",
            type="PostgreSQL",
            system_of_record=True,
            storage_location="postgresql://atlas/business_rows",
            connection_state="Connected",
            steward=steward,
        )
        add(
            f"{d}-minio",
            "source",
            d,
            name=f"{subs[0]} Document Store",
            description=f"Synthetic policies, reports and supporting evidence for {name}.",
            type="MinIO",
            system_of_record=False,
            storage_location=f"s3://atlas-knowledge/{d}/",
            connection_state="Connected",
            steward=steward,
        )
        n = 14 if i < 7 else 13
        for j in range(n):
            p = j % 4
            kind = ["Table", "Document", "Metadata", "Data product"][j % 4]
            asset_name = [
                products[p] + " · records",
                products[p] + " · evidence brief",
                products[p] + " · definitions",
                products[p] + " · curated dataset",
            ][j % 4]
            if d == "risk" and j == 0:
                asset_name = "counterparty_exposure"
            if d == "risk" and j == 1:
                asset_name = "Counterparty due diligence policy"
            if d == "third-party" and j == 1:
                asset_name = "Third party due diligence report"
            if j >= 4:
                asset_name += f" {j // 4 + 1}"
            add(
                f"{d}-asset-{j}",
                "asset",
                d,
                name=asset_name,
                description=f"{asset_name} supports {subs[p % 3].lower()} decisions with {concept.lower()} context and accountable provenance.",
                type=kind,
                source_id=f"{d}-minio" if kind == "Document" else f"{d}-sql",
                subdomain_id=f"{d}-sub-{p % 3}",
                product_ids=[f"{d}-product-{k}" for k in range(4)]
                if j < 4
                else [f"{d}-product-{p}"],
                steward=steward,
                owner_id=steward,
                status="Active",
                classification="Confidential" if j % 5 == 0 else "Internal",
                quality=98 - (j * 3 + i) % 19,
                tags=[concept, subs[p % 3]],
                concepts=[concept, "Policy" if kind == "Document" else "Exposure"],
                storage_location=f"s3://atlas-knowledge/{d}/{d}-asset-{j}.txt"
                if kind == "Document"
                else f"postgresql://atlas/business_rows?asset_id={d}-asset-{j}",
                table="business_rows" if kind != "Document" else None,
                object_key=f"{d}/{d}-asset-{j}.txt" if kind == "Document" else None,
                indexing_state="pending",
                record_count=8 if kind != "Document" else None,
            )
        add(
            f"{d}-project",
            "project",
            d,
            name=products[0] + " delivery",
            description=f"Expand trusted coverage for {products[0]}.",
            product_id=f"{d}-product-0",
            knowledge_product_name=products[0],
            status="In progress" if i % 3 else "Planned",
            sponsor=delegates[0],
            budget=850000 + i * 125000,
            currency="USD",
            subdomain_id=f"{d}-sub-0",
            steward=steward,
        )
        add(
            f"{d}-gap",
            "gap",
            d,
            name=subs[0] + " evidence coverage",
            description=f"{2 + i % 3} required {subs[0].lower()} evidence sources remain uncovered. Remediation requires steward review and source onboarding.",
            coverage=round((8 - i % 3) / 10 * 100),
            covered=8 - i % 3,
            required=10,
            coverage_basis="Required evidence sources",
            tags=["coverage", "documentation", subs[0]],
            quality_issues=2 + i % 3,
            product_id=f"{d}-product-0",
            asset_ids=[f"{d}-asset-0"],
            owner=steward,
            status="Open",
        )
        for j in range(2 + i % 3):
            add(
                f"{d}-issue-{j}",
                "issue",
                d,
                name=[
                    "Missing steward evidence",
                    "Incomplete identifiers",
                    "Stale policy reference",
                    "Unmapped concept",
                ][j],
                description=f"Synthetic governance finding {j + 1} requiring review.",
                asset_id=f"{d}-asset-0",
                severity="High" if j == 0 else "Medium",
                status="Open",
            )
    for _, _, _, steward, _, _, _ in DOMAINS:
        add(
            "person-" + steward.lower().replace(" ", "-"),
            "person",
            None,
            name=steward,
            email=steward.lower().replace(" ", ".") + "@atlas.example",
            team="Enterprise stewardship",
        )
    from app.auth import PERSONAS

    for id, (name, role, domains) in PERSONAS.items():
        add(
            f"role-{id}",
            "role",
            None,
            name=name,
            role=role,
            domain_ids=domains,
            scope_version=1,
        )
    for record in records:
        if record["kind"] == "product":
            record["payload"]["asset_count"] = sum(
                record["id"] in a["payload"].get("product_ids", [])
                for a in records
                if a["kind"] == "asset"
            )
    from app.knowledge.corpus import semantic_records

    records.extend(semantic_records())
    for r in records:
        if r["kind"] == "asset" and r["id"] in [
            "finance-asset-1",
            "finance-asset-5",
            "finance-asset-9",
            "finance-asset-13",
        ]:
            r["payload"]["product_ids"] = sorted(
                set(r["payload"]["product_ids"] + ["finance-product-0"])
            )
        if r["kind"] == "product":
            r["payload"]["primary_content_asset_id"] = r["domain_id"] + "-asset-0"
    return records


def business_data(asset):
    d = asset["domain_id"]
    output = []
    for i in range(8):
        row = {
            "record_id": f"{asset['id']}-row-{i}",
            "as_of": "2026-09-30",
            "domain": d,
        }
        if d in ["risk", "customer", "third-party"]:
            row.update(
                counterparty_id=f"CP-{1000 + i}",
                counterparty_name=[
                    "Aster Capital",
                    "Meridian Holdings",
                    "Northbridge Trading",
                    "Cedar Partners",
                ][i % 4],
                exposure_usd=(i + 1) * 1250000,
                risk_rating=["High", "Moderate", "Low"][i % 3],
                review_status="Reviewed" if i % 3 else "Evidence pending",
            )
            if d == "third-party":
                row.update(
                    service_dependency=[
                        "Settlement",
                        "Cloud hosting",
                        "Customer support",
                        "Legal advice",
                    ][i % 4],
                    due_diligence_status="Approved" if i % 3 else "Awaiting evidence",
                )
        elif d == "legal":
            row.update(
                contract_id=f"CT-{2000 + i}",
                counterparty=["Aster Capital", "Meridian Holdings"][i % 2],
                contract_type=["Master agreement", "Service agreement"][i % 2],
                obligation="Annual disclosure",
                renewal_date="2027-03-31",
                review_status="Approved",
            )
        elif d == "technology":
            row.update(
                service_id=f"SVC-{300 + i}",
                service_name=[
                    "Payment Gateway",
                    "Risk Analytics",
                    "Identity Service",
                    "Document Platform",
                ][i % 4],
                availability_percent=round(99.5 + i * 0.05, 2),
                criticality=["Tier 1", "Tier 2"][i % 2],
                open_incidents=i % 3,
            )
        elif d == "product":
            row.update(
                product_code=f"PRD-{100 + i}",
                product_name=[
                    "Corporate Lending",
                    "Treasury Services",
                    "Trade Finance",
                    "Custody",
                ][i % 4],
                active_accounts=1200 + i * 125,
                revenue_usd=250000 + i * 45000,
                control_status="Verified" if i % 3 else "Review required",
            )
        elif d == "operations":
            row.update(
                process_id=f"OPS-{100 + i}",
                service_name=[
                    "Settlement",
                    "Reconciliation",
                    "Onboarding",
                    "Case management",
                ][i % 4],
                sla_percent=96 + i * 0.3,
                open_exceptions=i % 4,
                resilience_test="Passed" if i % 3 else "Remediation open",
            )
        elif d == "data":
            row.update(
                element_id=f"DE-{100 + i}",
                business_name=[
                    "Counterparty identifier",
                    "Contract identifier",
                    "Service identifier",
                    "Exposure amount",
                ][i % 4],
                data_type=["varchar", "varchar", "varchar", "numeric"][i % 4],
                completeness_percent=92 + i,
                classification="Internal",
                definition_status="Approved",
            )
        elif d == "finance":
            row.update(
                position_id=f"FIN-{100 + i}",
                currency=["USD", "EUR", "GBP", "INR"][i % 4],
                liquidity_usd=12500000 + i * 1750000,
                tax_jurisdiction=["US", "UK", "EU", "India"][i % 4],
                capital_ratio_percent=14 + i * 0.25,
                reporting_status="Reconciled",
            )
        elif d == "people":
            row.update(
                workforce_id=f"WF-{100 + i}",
                team=["Engineering", "Operations", "Finance", "Legal"][i % 4],
                headcount=35 + i * 4,
                open_roles=i % 5,
                required_skill=[
                    "Data stewardship",
                    "Service management",
                    "Financial control",
                    "Contract review",
                ][i % 4],
                training_completion_percent=85 + i,
            )
        elif d == "strategy":
            row.update(
                initiative_id=f"CHG-{100 + i}",
                initiative=[
                    "Cloud modernization",
                    "Customer experience",
                    "Data governance",
                    "Operational resilience",
                ][i % 4],
                budget_usd=750000 + i * 125000,
                benefits_usd=1500000 + i * 200000,
                delivery_status=["On track", "At risk"][i % 2],
                sponsor="Enterprise Change Office",
            )
        output.append(row)
    return output


DOMAIN_CONTROLS = {
    "risk": "Every counterparty exposure must link to an approved due diligence record. Aster Capital (CP-1000) has a reported exposure of USD 1,250,000 and a High review priority. Meridian Holdings (CP-1001) has a reported exposure of USD 2,500,000. Due diligence includes legal ownership, sanctions screening and financial condition.",
    "customer": "Counterparty master identifiers connect customer relationships, exposure and onboarding evidence. Aster Capital has identifier CP-1000. Relationship managers must confirm consent, ownership and current due diligence before using the record.",
    "third-party": "Third party due diligence connects counterparties to service dependencies and supplier review evidence. Aster Capital (CP-1000) supports settlement with a synthetic exposure of USD 1,250,000. Service owners must verify sanctions screening, financial condition and resilience evidence.",
    "legal": "Every contract must identify the counterparty, renewal date and applicable obligations. Contract CT-2000 with Aster Capital requires annual disclosure. Clauses must be reviewed by Legal before an obligation is treated as current.",
    "technology": "Critical services require approved owners, availability targets, incident records and dependency mappings. Payment Gateway (SVC-300) has a synthetic availability of 99.5 percent. Tier 1 service failures must link to operational resilience evidence.",
    "product": "Product performance combines active accounts, revenues, pricing and control evidence. Corporate Lending (PRD-100) reports 1,200 synthetic active accounts. Product owners must verify control status before a performance report is reused.",
    "operations": "Operational resilience requires service-level indicators, open exception tracking and resilience tests. Settlement (OPS-100) has a synthetic SLA attainment of 96 percent. Remediation evidence must be reviewed by the assigned service owner.",
    "data": "Data elements require stable identifiers, approved business definitions, classification and completeness measurements. Counterparty identifier (DE-100) is classified Internal and has synthetic completeness of 92 percent. Missing definitions require steward review.",
    "finance": "Treasury liquidity reconciles positions, currencies and funding evidence. Position FIN-100 has synthetic USD liquidity of 12,500,000. Enterprise tax reporting must link jurisdiction, source amounts and reconciled financial controls.",
    "people": "Workforce planning links teams, headcount, open roles and required skills. Engineering workforce WF-100 has a synthetic headcount of 35. People policies govern access to workforce data and learning completion evidence.",
    "strategy": "Change portfolios require initiative sponsors, budgets, benefit estimates and delivery evidence. Initiative CHG-100 Cloud modernization has a synthetic budget of USD 750,000 and benefit estimate of USD 1,500,000. Benefits require sponsor review.",
}


def document_text(asset):
    from app.knowledge.corpus import managed_document

    managed = managed_document(asset["id"])
    if managed is not None:
        return managed
    p = asset["payload"]
    return f"""# {p["name"]}
Synthetic enterprise evidence — Knowledge Product Manager demonstration data
Domain: {asset["domain_id"]}
Steward: {p["steward"]}
Concepts: {", ".join(p["concepts"])}

Purpose
{p["description"]}

Control requirements
{DOMAIN_CONTROLS[asset["domain_id"]]}
All entities, measurements and amounts in this source are fictional.

Evidence and governance
The steward reviews records monthly. PostgreSQL stores structured records; MinIO retains the original source document. RDF concepts connect the business meaning, source and knowledge product. Two required supporting evidence sources remain uncovered. Unresolved data quality issues must be considered before use.

Domain-specific context
{p["name"]} applies this evidence framework to {p["tags"][-1]}. Supporting assets are discoverable through the catalog and ontology explorer. Policy applicability must be confirmed by the assigned steward.
"""
