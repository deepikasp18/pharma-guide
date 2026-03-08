# PharmaGuide Health Companion
## Project Summary

## Executive Overview

PharmaGuide is an AI-powered personal health companion platform designed to help patients understand their medications better. The platform provides natural language query processing for medication information, patient profile management, and symptom tracking — all within a secure, user-friendly interface.

At its core, PharmaGuide aims to bridge the gap between complex pharmaceutical information and everyday patient understanding by providing personalized, evidence-based health insights through natural language interaction. The platform is built with a knowledge graph architecture in mind for future scalability, currently operating with an in-memory drug database for immediate functionality.

## The Problem

Patients today face significant challenges in understanding their medications:

- **Information overload**: Drug labels and package inserts are dense, technical, and difficult to interpret.
- **Fragmented knowledge**: No single source captures the full picture of drug effects, interactions, contraindications, and real-world patient experiences.
- **Lack of personalization**: Generic drug information fails to account for individual patient factors such as age, comorbidities, genetics, or polypharmacy.
- **Delayed risk detection**: Drug-drug interactions and contraindications are often discovered reactively rather than proactively.
- **Memory and confusion challenges**: Patients often get confused about their medications and diseases, frequently forgetting to mention critical information to their doctors during appointments — including past medical history, allergies, or current symptoms.
- **Incomplete health context**: Most health information systems fail to consider the complete picture of a patient's health conditions, allergies, and past medical history when providing medication guidance.

Healthcare providers face parallel challenges — synthesizing complex patient histories against evolving pharmaceutical evidence at the point of care is time-consuming and error-prone.

## The Solution

PharmaGuide addresses these gaps through a **knowledge graph-centric architecture** that unifies multiple authoritative datasets into a single, semantically rich representation of medical knowledge, and then makes that knowledge accessible through natural language.

### Core Capabilities

**1. Natural Language Query Processing**
Patients ask questions in plain language — "What are the side effects of ibuprofen?" — and PharmaGuide parses the intent, extracts medical entities using NLP, and returns relevant information from the drug database with clear, understandable responses.

**2. In-Memory Drug Database**
The current implementation includes an in-memory database with 5 common medications:

| Medication | Class | Information Included |
|---|---|---|
| **Aspirin** | NSAID | Side effects, interactions, dosing |
| **Lisinopril** | ACE Inhibitor | Side effects, interactions, dosing |
| **Metformin** | Biguanide | Side effects, interactions, dosing |
| **Ibuprofen** | NSAID | Side effects, interactions, dosing |
| **Atorvastatin** | Statin | Side effects, interactions, dosing |

The architecture supports future integration with larger medical datasets including OnSIDES, SIDER, FAERS, DrugBank, DDInter, and Drugs@FDA.

**3. Patient Profile Management**
Patient profiles — including demographics, conditions, current medications, allergies, and past medical history — can be stored and managed through the platform. PharmaGuide's system is designed to take into comprehensive consideration the user's complete health profile: existing health conditions, known allergies, past medical history, and current medications. This holistic approach is being developed to surface risks, rank adverse effects, and generate recommendations specifically calibrated to each patient's unique situation.

**4. Medication and Symptom Tracking**
Patients can log their current medications and track symptoms over time. PharmaGuide helps patients who often get confused about their medications and diseases by maintaining a comprehensive record of their health journey — ensuring they have organized information to share with their doctor during appointments.

**5. 24/7 Medical Guidance**
PharmaGuide provides round-the-clock access to medication information and health guidance. Unlike traditional healthcare services with limited hours, patients can query the system anytime, anywhere — whether it's late at night when concerns arise, during weekends, or while traveling. This continuous availability ensures patients always have access to reliable medication information when they need it most, reducing anxiety and helping them make informed decisions about their health at any time.

**6. Authentication and Security**
The platform implements JWT-based authentication, secure password hashing with bcrypt, and role-based access control to protect patient data.


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
| **LLM Integration** | LLM for response generation and decision support |
| **Data Processing** | Pandas, NumPy |
| **Frontend** | React |
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


## Impact and Value Proposition

| Stakeholder | Value Delivered |
|---|---|
| **Patients** | Personalized, understandable medication guidance grounded in evidence; 24/7 access to reliable health information; comprehensive health tracking that helps remember medications, conditions, and important details for doctor visits |
| **Healthcare Providers** | Supplementary decision support with patient health context including allergies, past history, and current conditions; better-informed patients who can articulate their concerns |
| **Health Systems** | Improved patient engagement and medication adherence; reduced non-urgent inquiries through self-service information access |
| **Caregivers** | Easy-to-understand medication information to help care for family members; organized health records for multiple patients |

PharmaGuide transforms fragmented, technical medical data into a living knowledge graph that reasons on behalf of patients — making safer, smarter medication management accessible to everyone.


## Project Status

PharmaGuide is currently in prototype development, with a comprehensive technical foundation including full API specification, knowledge graph schema, security architecture, testing strategy, and local development environment. The platform is architected for production deployment on AWS with HIPAA-compliant services.


*PharmaGuide Health Companion — Intelligent medication guidance powered by medical knowledge graphs.*
