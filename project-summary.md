# PharmaGuide Health Companion
## Project Summary
## Executive Overview

PharmaGuide is an AI-powered personal health companion platform built on a comprehensive medical knowledge graph architecture. Designed to bridge the gap between complex pharmaceutical data and everyday patient understanding, PharmaGuide transforms authoritative medical datasets into personalized, evidence-based health insights delivered through natural language interaction.

At its core, PharmaGuide is not merely a drug information lookup tool — it is an intelligent reasoning system capable of traversing millions of interconnected medical relationships to answer nuanced, patient-specific questions in real time. The platform integrates six major medical data sources, supports natural language queries, monitors drug interactions proactively, and maintains strict HIPAA-compliant security — all within a scalable cloud architecture built for healthcare.

## The Problem

Patients today face significant challenges in understanding their medications:

- **Information overload**: Drug labels and package inserts are dense, technical, and difficult to interpret.
- **Fragmented knowledge**: No single source captures the full picture of drug effects, interactions, contraindications, and real-world patient experiences.
- **Lack of personalization**: Generic drug information fails to account for individual patient factors such as age, comorbidities, genetics, or polypharmacy.
- **Delayed risk detection**: Drug-drug interactions and contraindications are often discovered reactively rather than proactively.

Healthcare providers face parallel challenges — synthesizing complex patient histories against evolving pharmaceutical evidence at the point of care is time-consuming and error-prone.

## The Solution

PharmaGuide addresses these gaps through a **knowledge graph-centric architecture** that unifies multiple authoritative datasets into a single, semantically rich representation of medical knowledge, and then makes that knowledge accessible through natural language.

### Core Capabilities

**1. Natural Language Query Processing**
Patients ask questions in plain language — "What are the risks of taking Lisinopril at my age with diabetes?" — and PharmaGuide parses the intent, extracts medical entities using BioBERT-based NER, translates the query into knowledge graph traversals, and returns a personalized, evidence-backed response within 45 seconds.

**2. Multi-Dataset Knowledge Graph**
The platform integrates six major medical databases into a unified graph:

| Dataset | Contribution |
|---|---|
| **OnSIDES** | 3.6M+ drug-adverse event pairs with confidence scoring |
| **SIDER** | Side effect frequency data for 1,430 drugs and 5,880 ADRs |
| **FAERS** | 18M+ real-world adverse event reports from the FDA |
| **DrugBank** | Comprehensive drug mechanisms, pharmacokinetics, and interactions |
| **DDInter** | Drug-drug interaction severity and management strategies |
| **Drugs@FDA** | Official FDA drug approval and labeling data |

**3. Personalized Risk Assessment**
Patient profiles — including demographics, conditions, current medications, and genetic factors — are mapped as context layers onto graph queries. This allows the system to surface risks, rank adverse effects, and generate recommendations specifically calibrated to each patient's situation.

**4. Proactive Interaction & Contraindication Monitoring**
The system continuously monitors patient data against the knowledge graph. When new medications are added or profiles change, PharmaGuide automatically executes comprehensive interaction queries and generates immediate alerts for critical findings.

**5. Temporal Symptom Tracking**
Patients can log symptoms over time, allowing the system to construct temporal knowledge graph nodes linking symptom patterns to medication schedules. This enables detection of effectiveness trends and supports clinical decision-making with longitudinal evidence.

**6. Clinical Decision Support**
A dedicated provider portal surfaces complex knowledge graph summaries in clinical formats, enabling healthcare providers to review patient medication histories, identify concerning patterns, and explore evidence-based alternatives — all with full provenance tracking.


## Architecture

PharmaGuide follows a layered, cloud-native architecture designed for scalability, reliability, and HIPAA compliance.

```
Data Ingestion Layer
    ↓
Knowledge Graph Construction (ETL → Entity Resolution → Quality Assurance)
    ↓
Knowledge Graph Storage (Amazon Neptune + OpenSearch)
    ↓
AI Processing Layer (NLP → Query Translation → Graph Reasoning → Personalization → Evidence Validation)
    ↓
Application Layer (REST API → Web / Mobile / Provider Portal)
    ↓
End Users (Patients, Healthcare Providers, Administrators)
```

### Technology Stack

| Layer | Technology |
|---|---|
| **Backend API** | Python + FastAPI |
| **Knowledge Graph** | Amazon Neptune (property graph) |
| **Search** | OpenSearch for entity lookup and full-text search |
| **NLP / ML** | spaCy, BioBERT, scikit-learn, Hugging Face Transformers |
| **LLM Integration** | Anthropic Claude for response generation and decision support |
| **Data Processing** | Pandas, NumPy |
| **Frontend** | React Native (web + mobile) |
| **Infrastructure** | Docker, Kubernetes, AWS (HIPAA-compliant) |

## Key Technical Innovations

### Graph Reasoning Engine
The system supports multi-hop traversals across drug, condition, symptom, and patient nodes — enabling discovery of complex interaction patterns that would be invisible in tabular databases. Probabilistic inference weights evidence by source authority and statistical significance, producing confidence-scored recommendations.

### Entity Resolution at Scale
Identical medical entities appear under different identifiers across datasets (e.g., "Lisinopril" in DrugBank, RxNorm, and FAERS). PharmaGuide's entity resolution service links these into canonical graph nodes, ensuring queries against one dataset surface evidence from all others.

### Provenance-Tracked Responses
Every response traces its evidence path through the knowledge graph, citing the specific datasets, relationship weights, and reasoning steps that contributed to the answer. This supports clinical trust and regulatory accountability.

### Dynamic Patient Context Layers
Patient profiles are not static filters — they are live context layers re-evaluated whenever profile data changes. A new diagnosis, a medication update, or a reported symptom triggers an automatic re-traversal of relevant graph paths and updated risk assessments.

## Security and Compliance

PharmaGuide is built to the standards required for healthcare data:

- **AES-256 encryption** for all PII and PHI, at rest and in transit
- **Tokenization and pseudonymization** to separate patient identity from medical data within the knowledge graph
- **Role-based access control (RBAC)** enforcing least-privilege data access
- **Comprehensive audit trails** that log all data access and modifications without exposing raw PHI
- **HIPAA-compliant infrastructure** on AWS, with full separation of production and development environments

## Testing and Quality Assurance

PharmaGuide employs a dual-layer testing strategy to ensure correctness across all system behaviors.

**Unit Testing (388 tests)**
Covers ETL pipeline logic, entity resolution, Cypher query generation, NLP component accuracy, dataset ingestion, and personalization context application using pytest and Neptune test containers.

**Property-Based Testing (Hypothesis)**
Verifies universal system invariants across randomized inputs — including knowledge graph round-trip consistency, provenance completeness on all responses, personalization determinism, and PII/PHI non-exposure guarantees. Each property test runs a minimum of 100 iterations.

**27 Core Correctness Properties** are formally specified and validated, spanning semantic query processing, multi-dataset integration, drug interaction detection, patient personalization, evidence provenance, and security controls.


## Development Experience

PharmaGuide is designed to be accessible from day one:

- **Local development requires no AWS account** — a full mock service layer simulates Neptune and OpenSearch, enabling immediate development and testing
- **Automated setup scripts** (`setup_local_dev.sh`, `run_local.sh`) provide a working environment in minutes
- **Comprehensive documentation** covers local setup, environment configuration, mock data systems, graph reasoning architecture, and query translation internals

## Impact and Value Proposition

| Stakeholder | Value Delivered |
|---|---|
| **Patients** | Personalized, understandable medication guidance grounded in real-world evidence |
| **Healthcare Providers** | Clinical-grade decision support with full evidence provenance |
| **Health Systems** | Reduced adverse events through proactive interaction monitoring |
| **Researchers** | A unified, queryable representation of multi-source pharmaceutical evidence |

PharmaGuide transforms fragmented, technical medical data into a living knowledge graph that reasons on behalf of patients — making safer, smarter medication management accessible to everyone.


## Project Status

PharmaGuide is currently in prototype development, with a comprehensive technical foundation including full API specification, knowledge graph schema, security architecture, testing strategy, and local development environment. The platform is architected for production deployment on AWS with HIPAA-compliant services.


*PharmaGuide Health Companion — Intelligent medication guidance powered by medical knowledge graphs.*
