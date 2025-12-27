"""
29 Canonical Fields Schema.
This is the contract between Document Processing Unit and Underwriting Pipeline.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime


class FieldStatus(str, Enum):
    PRESENT = "PRESENT"
    MISSING = "MISSING"
    STUBBED = "STUBBED"


@dataclass
class ExtractedField:
    """Single extracted field with provenance."""

    value: Any
    confidence: float
    source_document: str
    status: FieldStatus = FieldStatus.PRESENT


# The 29 Canonical Fields
CANONICAL_FIELDS = [
    # 1. Identity & Contact (8)
    "full_name",
    "date_of_birth",
    "age",
    "gender",
    "aadhaar_number",
    "pan_number",
    "mobile_number",
    "address",
    # 2. Lifestyle (4)
    "smoking_status",
    "alcohol_status",
    "alcohol_frequency",
    "hazardous_occupation",
    # 3. Vitals (5)
    "height_cm",
    "weight_kg",
    "bmi",
    "bp_systolic",
    "bp_diastolic",
    # 4. Diabetes (4)
    "diabetes_declared",
    "fbs",
    "hba1c",
    "diabetes_control",
    # 5. Liver (3)
    "sgot",
    "sgpt",
    "liver_status",
    # 6. Kidney (3)
    "creatinine",
    "urea",
    "kidney_status",
    # 7. Financial (2)
    "annual_income",
    "existing_insurance",
]


@dataclass
class PatientProfile:
    """
    The 29-field patient profile.
    This is the ONLY thing underwriting sees.
    Documents are never re-read after this is created.
    """

    # Metadata
    patient_id: str
    profile_generated_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    # 1. Identity & Contact (8)
    full_name: Optional[ExtractedField] = None
    date_of_birth: Optional[ExtractedField] = None
    age: Optional[ExtractedField] = None
    gender: Optional[ExtractedField] = None
    aadhaar_number: Optional[ExtractedField] = None
    pan_number: Optional[ExtractedField] = None
    mobile_number: Optional[ExtractedField] = None
    address: Optional[ExtractedField] = None

    # 2. Lifestyle (4)
    smoking_status: Optional[ExtractedField] = None
    alcohol_status: Optional[ExtractedField] = None
    alcohol_frequency: Optional[ExtractedField] = None
    hazardous_occupation: Optional[ExtractedField] = None

    # 3. Vitals (5)
    height_cm: Optional[ExtractedField] = None
    weight_kg: Optional[ExtractedField] = None
    bmi: Optional[ExtractedField] = None
    bp_systolic: Optional[ExtractedField] = None
    bp_diastolic: Optional[ExtractedField] = None

    # 4. Diabetes (4)
    diabetes_declared: Optional[ExtractedField] = None
    fbs: Optional[ExtractedField] = None
    hba1c: Optional[ExtractedField] = None
    diabetes_control: Optional[ExtractedField] = None

    # 5. Liver (3)
    sgot: Optional[ExtractedField] = None
    sgpt: Optional[ExtractedField] = None
    liver_status: Optional[ExtractedField] = None

    # 6. Kidney (3)
    creatinine: Optional[ExtractedField] = None
    urea: Optional[ExtractedField] = None
    kidney_status: Optional[ExtractedField] = None

    # 7. Financial (2)
    annual_income: Optional[ExtractedField] = None
    existing_insurance: Optional[ExtractedField] = None

    def get_completeness_report(self) -> Dict[str, Any]:
        """Check which of the 29 fields are present/missing."""
        present = []
        missing = []

        for field_name in CANONICAL_FIELDS:
            field_value = getattr(self, field_name, None)
            if field_value and field_value.value is not None:
                present.append(field_name)
            else:
                missing.append(field_name)

        return {
            "total": len(CANONICAL_FIELDS),
            "present": len(present),
            "missing": len(missing),
            "present_fields": present,
            "missing_fields": missing,
            "completeness_pct": len(present) / len(CANONICAL_FIELDS) * 100,
        }

    def to_profile_txt(self) -> str:
        """Generate the patient_profile.txt content."""
        lines = []

        def format_field(name: str, field: Optional[ExtractedField]) -> str:
            if field is None or field.value is None:
                return f"{name.upper()}: [MISSING]"
            return f"{name.upper()}: {field.value}"

        # Identity
        lines.append("# IDENTITY & CONTACT")
        lines.append(format_field("full_name", self.full_name))
        lines.append(format_field("dob", self.date_of_birth))
        lines.append(format_field("age", self.age))
        lines.append(format_field("gender", self.gender))
        lines.append(format_field("aadhaar", self.aadhaar_number))
        lines.append(format_field("pan", self.pan_number))
        lines.append(format_field("mobile", self.mobile_number))
        lines.append(format_field("address", self.address))
        lines.append("")

        # Lifestyle
        lines.append("# LIFESTYLE")
        lines.append(format_field("smoking", self.smoking_status))
        lines.append(format_field("alcohol", self.alcohol_status))
        lines.append(format_field("alcohol_frequency", self.alcohol_frequency))
        lines.append(format_field("hazardous_occupation", self.hazardous_occupation))
        lines.append("")

        # Vitals
        lines.append("# VITALS")
        lines.append(format_field("height_cm", self.height_cm))
        lines.append(format_field("weight_kg", self.weight_kg))
        lines.append(format_field("bmi", self.bmi))
        lines.append(format_field("bp_systolic", self.bp_systolic))
        lines.append(format_field("bp_diastolic", self.bp_diastolic))
        lines.append("")

        # Diabetes
        lines.append("# DIABETES")
        lines.append(format_field("diabetes_declared", self.diabetes_declared))
        lines.append(format_field("fbs", self.fbs))
        lines.append(format_field("hba1c", self.hba1c))
        lines.append(format_field("diabetes_control", self.diabetes_control))
        lines.append("")

        # Liver
        lines.append("# LIVER")
        lines.append(format_field("sgot", self.sgot))
        lines.append(format_field("sgpt", self.sgpt))
        lines.append(format_field("liver_status", self.liver_status))
        lines.append("")

        # Kidney
        lines.append("# KIDNEY")
        lines.append(format_field("creatinine", self.creatinine))
        lines.append(format_field("urea", self.urea))
        lines.append(format_field("kidney_status", self.kidney_status))
        lines.append("")

        # Financial
        lines.append("# FINANCIAL")
        lines.append(format_field("annual_income", self.annual_income))
        lines.append(format_field("existing_insurance", self.existing_insurance))

        return "\n".join(lines)
