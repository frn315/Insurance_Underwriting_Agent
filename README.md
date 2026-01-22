# AI Underwriting System

An automated, production-grade underwriting system for life insurance applications aligned with IRDAI regulations. The system uses deterministic actuarial tables for rating decisions and an LLM (Azure OpenAI) for non-binding advisory recommendations.

## Overview

This system processes insurance applications through a multi-stage pipeline:

1. **Document Processing** → Extract data from application documents
2. **Requirement Determination** → Identify what evidence is needed
3. **Deterministic Rating** → Calculate loadings using actuarial tables
4. **LLM Advisory** → Get AI recommendations (non-binding)
5. **Offer Construction** → Generate final decision and premium

### Key Design Principles

- **Deterministic Decisions**: All accept/decline/loading decisions are made by rule-based engines, NOT by LLM
- **LLM as Advisor Only**: The LLM provides recommendations and summaries but never makes final decisions
- **Full Audit Trail**: Every state change is logged for regulatory compliance
- **Evidence-Backed**: Every data point has provenance (source document, confidence, extraction date)

---

## Project Structure

```
underwriting_system/
├── src/
│   ├── agents/
│   │   └── llm_advisor.py          # LLM advisory layer (non-binding)
│   ├── domain/
│   │   ├── evidence.py             # Evidence-backed attribute models
│   │   ├── risk_case.py            # Core stateful RiskCase object
│   │   └── patient_profile.py      # 29 canonical fields schema
│   ├── dpu/
│   │   ├── document_processor.py   # Document Processing Unit
│   │   └── text_extractor.py       # Plain text extraction
│   ├── infrastructure/
│   │   ├── llm_client.py           # Azure OpenAI transport
│   │   └── docling_client.py       # IBM Docling document extraction
│   ├── stubs/
│   │   └── external_services.py    # ⚠️ STUB external API integrations
│   └── underwriting/
│       ├── production_pipeline.py  # Main underwriting pipeline
│       ├── pipeline.py             # Legacy pipeline (alternate implementation)
│       ├── requirement_engine.py   # Determines required evidence
│       └── rating_engine.py        # Deterministic actuarial rating
├── tests/
│   └── test_production.py          # Production pipeline test
├── patient_documents/              # Sample input documents
├── patient_profiles/               # Generated patient profiles
└── output/                         # Processing output
```

---

## How It Works

### Pipeline Flow

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   RiskCase       │ → │  Requirement     │ → │  Deterministic   │
│   Creation       │    │  Engine          │    │  Rating Engine   │
└──────────────────┘    └──────────────────┘    └──────────────────┘
                                                         │
                                                         ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   Final Offer    │ ← │  Offer           │ ← │  LLM Advisory    │
│   Decision+Price │    │  Constructor     │    │  (Non-binding)   │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

### Core Components

| Component              | File                                  | Purpose                                                          |
| ---------------------- | ------------------------------------- | ---------------------------------------------------------------- |
| **RiskCase**           | `domain/risk_case.py`                 | Stateful object containing all applicant evidence                |
| **RequirementEngine**  | `underwriting/requirement_engine.py`  | Determines what evidence is needed based on age, SA, disclosures |
| **RatingEngine**       | `underwriting/rating_engine.py`       | Calculates loadings using actuarial tables                       |
| **LLMAdvisor**         | `agents/llm_advisor.py`               | Provides non-binding recommendations                             |
| **ProductionPipeline** | `underwriting/production_pipeline.py` | Orchestrates the complete flow                                   |

---

## Stubs & Placeholders

> **Important**: The following components are **stubs/dummy implementations** that must be replaced with actual integrations for production use.

### External Service Stubs

Located in `src/stubs/external_services.py`:

| Stub             | Current Behavior                           | Production Replacement                                      |
| ---------------- | ------------------------------------------ | ----------------------------------------------------------- |
| **KYCService**   | Always returns `VERIFIED` status           | Integrate with DigiLocker API and NSDL PAN verification     |
| **CIBILService** | Returns fixed score of 750 (EXCELLENT)     | Integrate with TransUnion CIBIL API                         |
| **IIBService**   | Returns clean result (no fraud, no claims) | Integrate with Insurance Information Bureau (IIB/Sibyl) API |

### LLM Client

Located in `src/infrastructure/llm_client.py`:

| Component        | Current State                                | Production Requirements                                                       |
| ---------------- | -------------------------------------------- | ----------------------------------------------------------------------------- |
| **LLMClient**    | Uses Azure OpenAI with environment variables | Requires production API keys, proper SSL handling, rate limiting, retry logic |
| SSL Verification | Disabled (`verify_mode = ssl.CERT_NONE`)     | Must enable proper SSL certificate verification                               |

### Synthetic Data Loader

Located in `src/underwriting/production_pipeline.py`:

The function `create_risk_case_from_synthetic()` accepts a dictionary of values instead of extracting from real documents. For production:

- Integrate with the Document Processing Unit (`src/dpu/document_processor.py`)
- Use IBM Docling for PDF/image extraction
- Implement proper OCR and field validation

---

## Configuration

### Environment Variables

Create a `.env` file (see `env.example`):

```env
LLM_PROVIDER=azure
LLM_API_KEY=your-azure-openai-key
LLM_AZURE_ENDPOINT=https://your-resource.openai.azure.com/
LLM_AZURE_API_VERSION=2024-02-15-preview
LLM_AZURE_DEPLOYMENT=your-deployment-name
```

---

## Running the Project

### Prerequisites

```bash
pip install -r requirements.txt
```

### Running the Test

```bash
python tests/test_production.py
```

This runs the production pipeline with synthetic data and outputs:

- Requirement determination
- Rating calculation with loadings
- LLM advisory (if Azure OpenAI is configured)
- Final offer with premium

### Expected Output

````
======================================================================
PRODUCTION UNDERWRITING PIPELINE
======================================================================
Case ID: CASE-XXXXXXXX
Applicant: Priya Sharma
Sum Assured: ₹15,000,000

----------------------------------------------------------------------
STEP 1: REQUIREMENT DETERMINATION
----------------------------------------------------------------------
  [Medical Grid - SA Based]
    SA Slab: ₹10,000,001 - ₹25,000,000
      + Full_Medical
      + ECG
      + Lipid_Profile
      ...

----------------------------------------------------------------------
STEP 2: DETERMINISTIC RATING
----------------------------------------------------------------------
  [Auto-Decline Checks]
    ✓ No auto-decline conditions
  [Medical Loadings]
    (none or calculated loadings)

----------------------------------------------------------------------
STEP 3: LLM ADVISORY (Non-Binding)
----------------------------------------------------------------------
  Calling Azure OpenAI for advisory...
  ✓ Response received

----------------------------------------------------------------------
DECISION: APPROVE
======================================================================
  Sum Assured: ₹15,000,000
  Base Premium: ₹XX,XXX/year
  Loading: X%
  Final Premium: ₹XX,XXX/year
### Running the TUI

For an interactive experience, run the Textual-based TUI:

```bash
python main.py
````

This provides a professional interface to:

- Select patient profiles
- Run the underwriting pipeline
- View formatted results with Rich text rendering

---

## Audit Trail

Every action is logged in the RiskCase's audit trail:

```python
risk_case.log_audit(
    action="RATING_COMPLETED",
    actor="SYSTEM",
    component="DeterministicRatingEngine",
    new_value="APPROVE_WITH_LOADING|STANDARD|25%",
    reason="Approved with 25% loading. Loadings for: BMI_Overweight"
)
```

View the audit trail:

```python
print(risk_case.get_audit_summary())
```
