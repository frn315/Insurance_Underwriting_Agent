"""
Document Processing Unit (DPU).
Converts documents → PatientProfile.
No underwriting logic here.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime

from src.domain.patient_profile import (
    PatientProfile,
    ExtractedField,
    FieldStatus,
    CANONICAL_FIELDS,
)


class DocumentType(str, Enum):
    """Document classification types."""

    IDENTITY = "IDENTITY"  # Aadhaar, PAN
    MEDICAL_VITALS = "MEDICAL_VITALS"  # Vitals exam
    DIABETES_LAB = "DIABETES_LAB"  # FBS, HbA1c
    LIVER_KIDNEY_LAB = "LIVER_KIDNEY_LAB"  # SGOT, SGPT, Creatinine
    LIFESTYLE = "LIFESTYLE"  # Proposal form lifestyle section
    FINANCIAL = "FINANCIAL"  # Income proof
    PROPOSAL_FORM = "PROPOSAL_FORM"  # General proposal
    UNKNOWN = "UNKNOWN"


class DocumentClassifier:
    """STEP 2: Classify documents by type."""

    PATTERNS = {
        DocumentType.IDENTITY: ["aadhaar", "aadhar", "pan", "passport", "voter"],
        DocumentType.MEDICAL_VITALS: ["medical", "exam", "vitals", "physical"],
        DocumentType.DIABETES_LAB: ["diabetes", "sugar", "hba1c", "glucose"],
        DocumentType.LIVER_KIDNEY_LAB: ["liver", "kidney", "lft", "kft", "renal"],
        DocumentType.FINANCIAL: ["income", "salary", "itr", "bank", "financial"],
        DocumentType.PROPOSAL_FORM: ["proposal", "form", "application", "insurance"],
    }

    @classmethod
    def classify(cls, filename: str) -> DocumentType:
        """Classify document based on filename."""
        filename_lower = filename.lower()

        for doc_type, patterns in cls.PATTERNS.items():
            if any(p in filename_lower for p in patterns):
                return doc_type

        return DocumentType.UNKNOWN


class DocumentExtractor:
    """STEP 3: Extract fields from a single document."""

    def __init__(self):
        from docling.document_converter import DocumentConverter

        self.converter = DocumentConverter()

    def extract(self, file_path: str) -> Dict[str, ExtractedField]:
        """
        Extract fields from a single document.
        Returns dict of field_name → ExtractedField.
        No merging, no policy logic.
        """
        print(f"[DPU] Extracting: {os.path.basename(file_path)}")

        result = self.converter.convert(file_path)
        text = result.document.export_to_markdown()

        fields = {}
        source = os.path.basename(file_path)

        # Pattern-based extraction
        fields.update(self._extract_identity(text, source))
        fields.update(self._extract_vitals(text, source))
        fields.update(self._extract_diabetes(text, source))
        fields.update(self._extract_liver_kidney(text, source))
        fields.update(self._extract_lifestyle(text, source))
        fields.update(self._extract_financial(text, source))

        return fields

    def _make_field(
        self, value: Any, source: str, confidence: float = 0.90
    ) -> ExtractedField:
        return ExtractedField(
            value=value, confidence=confidence, source_document=source
        )

    def _extract_identity(self, text: str, source: str) -> Dict[str, ExtractedField]:
        fields = {}

        # Name - look for markdown headers with names
        name_match = re.search(r"##\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", text)
        if name_match:
            fields["full_name"] = self._make_field(name_match.group(1), source)

        # PAN
        pan_match = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", text)
        if pan_match:
            fields["pan_number"] = self._make_field(pan_match.group(1), source, 0.95)

        # Aadhaar
        aadhaar_match = re.search(r"\b(\d{4}\s?\d{4}\s?\d{4})\b", text)
        if aadhaar_match:
            aadhaar = aadhaar_match.group(1).replace(" ", "")
            fields["aadhaar_number"] = self._make_field(aadhaar, source, 0.95)

        # DOB
        dob_match = re.search(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b", text)
        if dob_match:
            fields["date_of_birth"] = self._make_field(dob_match.group(1), source)

        # Gender
        if re.search(r"\bMALE\b", text, re.IGNORECASE):
            fields["gender"] = self._make_field("Male", source)
        elif re.search(r"\bFEMALE\b", text, re.IGNORECASE):
            fields["gender"] = self._make_field("Female", source)

        # Age
        age_match = re.search(r"(?:age|aged?)[:\s]*(\d+)", text, re.IGNORECASE)
        if age_match:
            age = int(age_match.group(1))
            if 1 <= age <= 120:
                fields["age"] = self._make_field(age, source)

        # Mobile
        mobile_match = re.search(r"\b([6-9]\d{9})\b", text)
        if mobile_match:
            fields["mobile_number"] = self._make_field(mobile_match.group(1), source)

        # Address - look for multi-line address
        addr_match = re.search(
            r"(?:address|addr)[:\s]*([^\n]+(?:\n[^\n]+)?)", text, re.IGNORECASE
        )
        if addr_match:
            fields["address"] = self._make_field(
                addr_match.group(1).strip(), source, 0.80
            )

        return fields

    def _extract_vitals(self, text: str, source: str) -> Dict[str, ExtractedField]:
        fields = {}

        # Height
        height_match = re.search(
            r"(?:height|ht)[:\s]*(\d+\.?\d*)\s*(?:cm)?", text, re.IGNORECASE
        )
        if height_match:
            fields["height_cm"] = self._make_field(float(height_match.group(1)), source)

        # Weight
        weight_match = re.search(
            r"(?:weight|wt)[:\s]*(\d+\.?\d*)\s*(?:kg)?", text, re.IGNORECASE
        )
        if weight_match:
            fields["weight_kg"] = self._make_field(float(weight_match.group(1)), source)

        # BMI
        bmi_match = re.search(r"(?:bmi)[:\s]*(\d+\.?\d*)", text, re.IGNORECASE)
        if bmi_match:
            fields["bmi"] = self._make_field(float(bmi_match.group(1)), source)

        # Blood Pressure
        bp_match = re.search(
            r"(?:bp|blood\s*pressure)[:\s]*(\d{2,3})\s*[/\-]\s*(\d{2,3})",
            text,
            re.IGNORECASE,
        )
        if bp_match:
            fields["bp_systolic"] = self._make_field(int(bp_match.group(1)), source)
            fields["bp_diastolic"] = self._make_field(int(bp_match.group(2)), source)

        return fields

    def _extract_diabetes(self, text: str, source: str) -> Dict[str, ExtractedField]:
        fields = {}

        # FBS
        fbs_match = re.search(
            r"(?:fbs|fasting\s*(?:blood\s*)?sugar)[:\s]*(\d+\.?\d*)",
            text,
            re.IGNORECASE,
        )
        if fbs_match:
            fields["fbs"] = self._make_field(float(fbs_match.group(1)), source)

        # HbA1c
        hba1c_match = re.search(
            r"(?:hba1c|a1c|glycated)[:\s]*(\d+\.?\d*)", text, re.IGNORECASE
        )
        if hba1c_match:
            fields["hba1c"] = self._make_field(float(hba1c_match.group(1)), source)

        # Diabetes declared
        if re.search(r"diabetes\s*:\s*yes", text, re.IGNORECASE):
            fields["diabetes_declared"] = self._make_field("Yes", source)
        elif re.search(r"diabetes\s*:\s*no", text, re.IGNORECASE):
            fields["diabetes_declared"] = self._make_field("No", source)

        return fields

    def _extract_liver_kidney(
        self, text: str, source: str
    ) -> Dict[str, ExtractedField]:
        fields = {}

        # SGOT
        sgot_match = re.search(r"(?:sgot|ast)[:\s]*(\d+\.?\d*)", text, re.IGNORECASE)
        if sgot_match:
            fields["sgot"] = self._make_field(float(sgot_match.group(1)), source)

        # SGPT
        sgpt_match = re.search(r"(?:sgpt|alt)[:\s]*(\d+\.?\d*)", text, re.IGNORECASE)
        if sgpt_match:
            fields["sgpt"] = self._make_field(float(sgpt_match.group(1)), source)

        # Creatinine
        creat_match = re.search(r"(?:creatinine)[:\s]*(\d+\.?\d*)", text, re.IGNORECASE)
        if creat_match:
            fields["creatinine"] = self._make_field(float(creat_match.group(1)), source)

        # Urea
        urea_match = re.search(r"(?:urea|bun)[:\s]*(\d+\.?\d*)", text, re.IGNORECASE)
        if urea_match:
            fields["urea"] = self._make_field(float(urea_match.group(1)), source)

        return fields

    def _extract_lifestyle(self, text: str, source: str) -> Dict[str, ExtractedField]:
        fields = {}

        # Smoking
        if re.search(r"smoking\s*[:\-]?\s*(?:no|nil|never|non)", text, re.IGNORECASE):
            fields["smoking_status"] = self._make_field("No", source)
        elif re.search(r"smoking\s*[:\-]?\s*yes", text, re.IGNORECASE):
            fields["smoking_status"] = self._make_field("Yes", source)

        # Alcohol
        if re.search(r"alcohol\s*[:\-]?\s*(?:no|nil|never|non)", text, re.IGNORECASE):
            fields["alcohol_status"] = self._make_field("No", source)
        elif re.search(
            r"alcohol\s*[:\-]?\s*(?:yes|occasional|social)", text, re.IGNORECASE
        ):
            fields["alcohol_status"] = self._make_field("Yes", source)

        # Hazardous occupation
        if re.search(r"hazardous\s*[:\-]?\s*no", text, re.IGNORECASE):
            fields["hazardous_occupation"] = self._make_field("No", source)

        return fields

    def _extract_financial(self, text: str, source: str) -> Dict[str, ExtractedField]:
        fields = {}

        # Income
        income_match = re.search(
            r"(?:annual\s*)?income[:\s]*(?:Rs\.?|₹)?\s*([\d,]+)", text, re.IGNORECASE
        )
        if income_match:
            income = int(income_match.group(1).replace(",", ""))
            fields["annual_income"] = self._make_field(income, source)

        # Existing insurance
        ins_match = re.search(
            r"(?:existing\s*)?(?:insurance|cover)[:\s]*(?:Rs\.?|₹)?\s*([\d,]+)",
            text,
            re.IGNORECASE,
        )
        if ins_match:
            amount = int(ins_match.group(1).replace(",", ""))
            fields["existing_insurance"] = self._make_field(amount, source)

        return fields


class FieldAggregator:
    """STEP 4: Merge fields from multiple documents."""

    @staticmethod
    def aggregate(
        extractions: List[Dict[str, ExtractedField]],
    ) -> Dict[str, ExtractedField]:
        """
        Merge extracted fields.
        If conflict → choose higher confidence.
        """
        merged = {}

        for extraction in extractions:
            for field_name, field_value in extraction.items():
                if field_name not in merged:
                    merged[field_name] = field_value
                else:
                    # Conflict resolution: higher confidence wins
                    if field_value.confidence > merged[field_name].confidence:
                        merged[field_name] = field_value

        return merged


class CompletenessChecker:
    """STEP 5: Check if all 29 fields are present."""

    @staticmethod
    def check(merged_fields: Dict[str, ExtractedField]) -> Dict[str, Any]:
        """Check completeness against 29 canonical fields."""
        present = []
        missing = []

        for field in CANONICAL_FIELDS:
            if field in merged_fields and merged_fields[field].value is not None:
                present.append(field)
            else:
                missing.append(field)

        return {
            "is_complete": len(missing) == 0,
            "present_count": len(present),
            "missing_count": len(missing),
            "present_fields": present,
            "missing_fields": missing,
        }


class ProfileGenerator:
    """STEP 6: Generate patient_profile.txt from merged fields."""

    @staticmethod
    def generate(
        patient_id: str, merged_fields: Dict[str, ExtractedField], output_dir: str
    ) -> str:
        """
        Create patient_profile.txt in the specified directory.
        This file is the ONLY thing underwriting sees.
        """
        # Build PatientProfile
        profile = PatientProfile(patient_id=patient_id)

        for field_name in CANONICAL_FIELDS:
            if field_name in merged_fields:
                setattr(profile, field_name, merged_fields[field_name])

        # Calculate derived fields if needed
        if profile.height_cm and profile.weight_kg and not profile.bmi:
            h = profile.height_cm.value / 100
            w = profile.weight_kg.value
            bmi = round(w / (h * h), 1)
            profile.bmi = ExtractedField(
                value=bmi, confidence=0.95, source_document="CALCULATED"
            )

        # Generate profile content
        content = profile.to_profile_txt()

        # Add completeness report
        report = profile.get_completeness_report()
        content += f"\n\n# COMPLETENESS REPORT"
        content += f"\nFIELDS_PRESENT: {report['present']}/{report['total']}"
        content += f"\nCOMPLETENESS: {report['completeness_pct']:.1f}%"
        if report["missing_fields"]:
            content += f"\nMISSING: {', '.join(report['missing_fields'])}"

        # Save to file
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "patient_profile.txt")

        with open(output_path, "w") as f:
            f.write(content)

        print(f"[DPU] Profile saved: {output_path}")
        return output_path


class DocumentProcessingUnit:
    """
    Main DPU Class.
    Orchestrates: Intake → Classification → Extraction → Aggregation → Profile.
    """

    def __init__(self):
        self.classifier = DocumentClassifier()
        self.extractor = DocumentExtractor()
        self.aggregator = FieldAggregator()
        self.checker = CompletenessChecker()
        self.generator = ProfileGenerator()

        # Text file extractor (no Docling needed)
        from src.dpu.text_extractor import TextFileExtractor

        self.text_extractor = TextFileExtractor()

    def process_patient_folder(
        self, patient_folder: str, output_folder: str
    ) -> Dict[str, Any]:
        """
        Process all documents in a patient's folder.
        Generate patient_profile.txt.
        """
        patient_id = os.path.basename(patient_folder)
        print(f"\n{'='*60}")
        print(f"[DPU] Processing Patient: {patient_id}")
        print(f"{'='*60}")

        # Step 1: Document Intake
        documents = []
        for file in Path(patient_folder).glob("*"):
            if file.suffix.lower() in [".pdf", ".jpg", ".jpeg", ".png", ".txt"]:
                documents.append(str(file))

        print(f"\n[Step 1] Found {len(documents)} documents")

        # Step 2: Classification
        classified = {}
        for doc in documents:
            doc_type = self.classifier.classify(os.path.basename(doc))
            classified[doc] = doc_type
            print(f"  {os.path.basename(doc)} → {doc_type.value}")

        # Step 3: Extraction
        print(f"\n[Step 3] Extracting fields...")
        all_extractions = []
        for doc in documents:
            try:
                # Use text extractor for .txt files, Docling for PDFs
                if doc.lower().endswith(".txt"):
                    fields = self.text_extractor.extract(doc)
                else:
                    fields = self.extractor.extract(doc)
                print(f"  {os.path.basename(doc)}: {len(fields)} fields")
                all_extractions.append(fields)
            except Exception as e:
                print(f"  {os.path.basename(doc)}: ERROR - {e}")

        # Step 4: Aggregation
        print(f"\n[Step 4] Aggregating fields...")
        merged = self.aggregator.aggregate(all_extractions)
        print(f"  Total unique fields: {len(merged)}")

        # Step 5: Completeness
        print(f"\n[Step 5] Checking completeness...")
        report = self.checker.check(merged)
        print(f"  Present: {report['present_count']}/29")
        print(f"  Missing: {report['missing_count']}/29")
        if report["missing_fields"]:
            print(f"  Missing fields: {', '.join(report['missing_fields'][:5])}...")

        # Step 6: Generate Profile
        print(f"\n[Step 6] Generating patient_profile.txt...")
        profile_path = self.generator.generate(patient_id, merged, output_folder)

        return {
            "patient_id": patient_id,
            "documents_processed": len(documents),
            "fields_extracted": len(merged),
            "completeness": report,
            "profile_path": profile_path,
        }
