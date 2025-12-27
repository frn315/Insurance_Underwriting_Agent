"""
Evidence-backed attribute models for production underwriting.
Every value has provenance: source, date, confidence.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class EvidenceSource(str, Enum):
    """Source of evidence."""

    LAB_REPORT = "LAB_REPORT"
    MEDICAL_EXAM = "MEDICAL_EXAM"
    PROPOSAL_FORM = "PROPOSAL_FORM"
    KYC_DOCUMENT = "KYC_DOCUMENT"
    FINANCIAL_DOC = "FINANCIAL_DOC"
    BUREAU_CHECK = "BUREAU_CHECK"
    SELF_DECLARATION = "SELF_DECLARATION"
    THIRD_PARTY = "THIRD_PARTY"


@dataclass
class EvidenceMetadata:
    """Provenance for every piece of evidence."""

    source_type: EvidenceSource
    source_document_id: str
    extraction_date: datetime
    lab_name: Optional[str] = None
    test_date: Optional[datetime] = None
    reference_range: Optional[str] = None
    confidence: float = 0.95
    verified: bool = False


@dataclass
class EvidenceValue:
    """A single evidence-backed value."""

    value: Any
    unit: Optional[str] = None
    metadata: Optional[EvidenceMetadata] = None

    @property
    def is_verified(self) -> bool:
        return self.metadata.verified if self.metadata else False


# ============================================================================
# MEDICAL EVIDENCE (Evidence-backed, not flat fields)
# ============================================================================


@dataclass
class BPReading:
    """Blood pressure reading with context."""

    systolic: int
    diastolic: int
    pulse: Optional[int] = None
    reading_date: Optional[datetime] = None
    position: str = "sitting"  # sitting, standing, supine
    metadata: Optional[EvidenceMetadata] = None


@dataclass
class DiabetesEvidence:
    """Diabetes evidence - not just HbA1c value."""

    is_diabetic: EvidenceValue  # Yes/No/Prediabetic
    diagnosis_date: Optional[datetime] = None
    duration_years: Optional[float] = None

    # Current control
    hba1c: Optional[EvidenceValue] = None  # With lab, date, reference
    fbs: Optional[EvidenceValue] = None
    ppbs: Optional[EvidenceValue] = None

    # Treatment
    treatment_type: Optional[str] = None  # Diet, OHA, Insulin
    medications: List[str] = field(default_factory=list)
    medication_adherence: Optional[str] = None  # Good, Fair, Poor

    # Complications
    has_complications: bool = False
    complications: List[str] = field(
        default_factory=list
    )  # Retinopathy, Nephropathy, etc.

    # Trend (not single value)
    hba1c_history: List[EvidenceValue] = field(default_factory=list)


@dataclass
class LiverPanel:
    """Liver function with evidence."""

    sgot: Optional[EvidenceValue] = None
    sgpt: Optional[EvidenceValue] = None
    alkaline_phosphatase: Optional[EvidenceValue] = None
    bilirubin_total: Optional[EvidenceValue] = None
    ggt: Optional[EvidenceValue] = None
    albumin: Optional[EvidenceValue] = None

    # Derived assessment
    status: str = "Normal"  # Normal, Elevated, Severely Elevated
    fatty_liver: bool = False


@dataclass
class RenalPanel:
    """Kidney function with evidence."""

    creatinine: Optional[EvidenceValue] = None
    urea: Optional[EvidenceValue] = None
    uric_acid: Optional[EvidenceValue] = None
    egfr: Optional[EvidenceValue] = None  # Calculated

    # Urine
    urine_albumin: Optional[EvidenceValue] = None
    urine_protein: Optional[EvidenceValue] = None

    # Derived
    status: str = "Normal"  # Normal, Mild Impairment, Moderate, Severe
    ckd_stage: Optional[int] = None  # 1-5


@dataclass
class LipidPanel:
    """Lipid profile with evidence."""

    total_cholesterol: Optional[EvidenceValue] = None
    ldl: Optional[EvidenceValue] = None
    hdl: Optional[EvidenceValue] = None
    triglycerides: Optional[EvidenceValue] = None
    vldl: Optional[EvidenceValue] = None

    # Ratios
    tc_hdl_ratio: Optional[float] = None
    ldl_hdl_ratio: Optional[float] = None

    # Risk
    cardiovascular_risk: str = "Low"  # Low, Moderate, High


@dataclass
class CardiacEvidence:
    """Cardiac evidence."""

    ecg_findings: Optional[str] = None
    ecg_abnormal: bool = False
    tmt_done: bool = False
    tmt_result: Optional[str] = None
    echo_done: bool = False
    echo_ef: Optional[float] = None
    known_heart_disease: bool = False


@dataclass
class VitalsEvidence:
    """Physical vitals with evidence."""

    height_cm: Optional[EvidenceValue] = None
    weight_kg: Optional[EvidenceValue] = None
    bmi: Optional[EvidenceValue] = None
    waist_circumference: Optional[EvidenceValue] = None

    # BP readings (list for trend)
    bp_readings: List[BPReading] = field(default_factory=list)

    # Derived
    bmi_category: str = (
        "Normal"  # Underweight, Normal, Overweight, Obese, Morbidly Obese
    )
    bp_category: str = "Normal"  # Normal, Elevated, Stage 1 HTN, Stage 2 HTN


@dataclass
class MedicalHistory:
    """Past medical history."""

    conditions: List[str] = field(default_factory=list)
    surgeries: List[str] = field(default_factory=list)
    hospitalizations: List[Dict[str, Any]] = field(default_factory=list)
    current_medications: List[str] = field(default_factory=list)

    # Family history
    family_diabetes: bool = False
    family_heart_disease: bool = False
    family_cancer: bool = False
    family_details: Optional[str] = None


@dataclass
class MedicalEvidence:
    """Complete medical evidence collection."""

    vitals: VitalsEvidence = field(default_factory=VitalsEvidence)
    diabetes: DiabetesEvidence = field(
        default_factory=lambda: DiabetesEvidence(
            is_diabetic=EvidenceValue(value="Unknown")
        )
    )
    liver: LiverPanel = field(default_factory=LiverPanel)
    renal: RenalPanel = field(default_factory=RenalPanel)
    lipid: LipidPanel = field(default_factory=LipidPanel)
    cardiac: CardiacEvidence = field(default_factory=CardiacEvidence)
    history: MedicalHistory = field(default_factory=MedicalHistory)


# ============================================================================
# LIFESTYLE EVIDENCE
# ============================================================================


@dataclass
class SmokingEvidence:
    """Smoking history - not just Yes/No."""

    status: str = "Never"  # Never, Former, Current
    pack_years: Optional[float] = None  # (packs/day * years)
    quit_date: Optional[datetime] = None
    years_since_quit: Optional[float] = None
    current_frequency: Optional[str] = None  # Occasional, Regular, Heavy


@dataclass
class AlcoholEvidence:
    """Alcohol history - not just Yes/No."""

    status: str = "Never"  # Never, Social, Regular, Heavy
    units_per_week: Optional[float] = None
    type_of_alcohol: Optional[str] = None  # Beer, Wine, Spirits
    cage_score: Optional[int] = None  # 0-4, screening for dependence


@dataclass
class OccupationEvidence:
    """Occupation details with risk grading."""

    occupation: str
    employer: Optional[str] = None
    industry: Optional[str] = None

    # Risk grading
    occupation_class: int = 1  # 1-4 (1=office, 4=hazardous)
    hazards: List[str] = field(default_factory=list)  # Chemicals, Heights, etc.
    travel_risk: str = "Low"  # Low, Medium, High


@dataclass
class LifestyleEvidence:
    """Complete lifestyle evidence."""

    smoking: SmokingEvidence = field(default_factory=SmokingEvidence)
    alcohol: AlcoholEvidence = field(default_factory=AlcoholEvidence)
    occupation: OccupationEvidence = field(
        default_factory=lambda: OccupationEvidence(occupation="")
    )

    # Other risk factors
    hazardous_hobbies: List[str] = field(default_factory=list)
    foreign_travel: bool = False
    high_risk_countries: List[str] = field(default_factory=list)


# ============================================================================
# FINANCIAL EVIDENCE
# ============================================================================


@dataclass
class IncomeEvidence:
    """Income with verification."""

    declared_annual: Optional[EvidenceValue] = None
    verified_annual: Optional[EvidenceValue] = None

    income_source: str = "Salary"  # Salary, Business, Professional, Other
    verification_method: Optional[str] = None  # ITR, Salary Slip, Bank Statement
    employer_name: Optional[str] = None


@dataclass
class FinancialEvidence:
    """Complete financial evidence."""

    income: IncomeEvidence = field(default_factory=IncomeEvidence)

    # Sum assured context
    sum_assured_requested: float = 0
    existing_cover: float = 0
    total_cover: float = 0  # existing + requested

    # Justification ratios
    sa_to_income_ratio: Optional[float] = None  # Should be reasonable
    human_life_value: Optional[float] = None

    # CIBIL
    cibil_score: Optional[int] = None
    cibil_category: str = "Unknown"  # Excellent, Good, Fair, Poor


# ============================================================================
# IDENTITY EVIDENCE
# ============================================================================


@dataclass
class IdentityEvidence:
    """Verified identity."""

    full_name: EvidenceValue
    date_of_birth: Optional[EvidenceValue] = None
    age: Optional[int] = None
    gender: Optional[str] = None

    # KYC
    pan: Optional[EvidenceValue] = None
    aadhaar: Optional[EvidenceValue] = None

    # Verification
    kyc_verified: bool = False
    kyc_method: Optional[str] = None

    # Contact
    address: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
