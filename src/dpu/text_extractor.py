"""
Text File Extractor.
For .txt files, we don't need Docling - just direct regex extraction.
"""

import os
import re
from typing import Dict, Any

from src.domain.patient_profile import ExtractedField


class TextFileExtractor:
    """Extract fields from plain text files."""

    def extract(self, file_path: str) -> Dict[str, ExtractedField]:
        """Extract fields from a text file."""
        print(f"[DPU] Extracting (text): {os.path.basename(file_path)}")

        with open(file_path, "r") as f:
            text = f.read()

        fields = {}
        source = os.path.basename(file_path)

        # Run all extractors
        fields.update(self._extract_identity(text, source))
        fields.update(self._extract_vitals(text, source))
        fields.update(self._extract_diabetes(text, source))
        fields.update(self._extract_liver_kidney(text, source))
        fields.update(self._extract_lifestyle(text, source))
        fields.update(self._extract_financial(text, source))

        return fields

    def _make_field(
        self, value: Any, source: str, confidence: float = 0.95
    ) -> ExtractedField:
        return ExtractedField(
            value=value, confidence=confidence, source_document=source
        )

    def _extract_identity(self, text: str, source: str) -> Dict[str, ExtractedField]:
        fields = {}

        # Full Name
        name_match = re.search(
            r"(?:full\s*)?name[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            text,
            re.IGNORECASE,
        )
        if name_match:
            fields["full_name"] = self._make_field(name_match.group(1).strip(), source)

        # DOB
        dob_match = re.search(
            r"(?:date\s*of\s*birth|dob)[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})",
            text,
            re.IGNORECASE,
        )
        if dob_match:
            fields["date_of_birth"] = self._make_field(dob_match.group(1), source)

        # Age
        age_match = re.search(r"age[:\s]+(\d+)\s*(?:years?)?", text, re.IGNORECASE)
        if age_match:
            age = int(age_match.group(1))
            if 1 <= age <= 120:
                fields["age"] = self._make_field(age, source)

        # Gender
        gender_match = re.search(r"gender[:\s]+(Male|Female)", text, re.IGNORECASE)
        if gender_match:
            fields["gender"] = self._make_field(
                gender_match.group(1).capitalize(), source
            )

        # Aadhaar
        aadhaar_match = re.search(
            r"(?:aadhaar|aadhar)[:\s\w]*?(\d{4}\s?\d{4}\s?\d{4})", text, re.IGNORECASE
        )
        if aadhaar_match:
            aadhaar = aadhaar_match.group(1).replace(" ", "")
            fields["aadhaar_number"] = self._make_field(aadhaar, source)

        # PAN
        pan_match = re.search(
            r"(?:pan)[:\s\w]*?([A-Z]{5}[0-9]{4}[A-Z])", text, re.IGNORECASE
        )
        if pan_match:
            fields["pan_number"] = self._make_field(pan_match.group(1).upper(), source)

        # Mobile
        mobile_match = re.search(
            r"(?:mobile|phone)[:\s]+([6-9]\d{9})", text, re.IGNORECASE
        )
        if mobile_match:
            fields["mobile_number"] = self._make_field(mobile_match.group(1), source)

        # Address
        addr_match = re.search(
            r"address[:\s]+(.+?)(?:\n\n|\n[A-Z])", text, re.IGNORECASE | re.DOTALL
        )
        if addr_match:
            address = addr_match.group(1).replace("\n", ", ").strip()
            fields["address"] = self._make_field(address, source, 0.90)

        return fields

    def _extract_vitals(self, text: str, source: str) -> Dict[str, ExtractedField]:
        fields = {}

        # Height
        height_match = re.search(
            r"height[:\s]+(\d+\.?\d*)\s*(?:cm)?", text, re.IGNORECASE
        )
        if height_match:
            fields["height_cm"] = self._make_field(float(height_match.group(1)), source)

        # Weight
        weight_match = re.search(
            r"weight[:\s]+(\d+\.?\d*)\s*(?:kg)?", text, re.IGNORECASE
        )
        if weight_match:
            fields["weight_kg"] = self._make_field(float(weight_match.group(1)), source)

        # BMI
        bmi_match = re.search(r"bmi[:\s]+(\d+\.?\d*)", text, re.IGNORECASE)
        if bmi_match:
            fields["bmi"] = self._make_field(float(bmi_match.group(1)), source)

        # Blood Pressure - look for "118/76" or "BP Systolic: 118"
        bp_combined = re.search(
            r"(?:blood\s*pressure|bp)[:\s]+(\d{2,3})[/\-](\d{2,3})", text, re.IGNORECASE
        )
        if bp_combined:
            fields["bp_systolic"] = self._make_field(int(bp_combined.group(1)), source)
            fields["bp_diastolic"] = self._make_field(int(bp_combined.group(2)), source)
        else:
            # Separate systolic/diastolic
            sys_match = re.search(
                r"(?:bp\s*)?systolic[:\s]+(\d{2,3})", text, re.IGNORECASE
            )
            if sys_match:
                fields["bp_systolic"] = self._make_field(
                    int(sys_match.group(1)), source
                )

            dia_match = re.search(
                r"(?:bp\s*)?diastolic[:\s]+(\d{2,3})", text, re.IGNORECASE
            )
            if dia_match:
                fields["bp_diastolic"] = self._make_field(
                    int(dia_match.group(1)), source
                )

        return fields

    def _extract_diabetes(self, text: str, source: str) -> Dict[str, ExtractedField]:
        fields = {}

        # Diabetes declared
        diabetes_match = re.search(
            r"diabetes\s*(?:declared)?[:\s]+(Yes|No)", text, re.IGNORECASE
        )
        if diabetes_match:
            fields["diabetes_declared"] = self._make_field(
                diabetes_match.group(1).capitalize(), source
            )

        # FBS
        fbs_match = re.search(
            r"(?:fasting\s*blood\s*sugar|fbs)[:\s\(]*(\d+\.?\d*)", text, re.IGNORECASE
        )
        if fbs_match:
            fields["fbs"] = self._make_field(float(fbs_match.group(1)), source)

        # HbA1c
        hba1c_match = re.search(r"hba1c[:\s]+(\d+\.?\d*)", text, re.IGNORECASE)
        if hba1c_match:
            fields["hba1c"] = self._make_field(float(hba1c_match.group(1)), source)

        # Diabetes control
        control_match = re.search(
            r"(?:diabetes\s*)?control(?:\s*status)?[:\s]+(Controlled|Uncontrolled)",
            text,
            re.IGNORECASE,
        )
        if control_match:
            fields["diabetes_control"] = self._make_field(
                control_match.group(1).capitalize(), source
            )

        return fields

    def _extract_liver_kidney(
        self, text: str, source: str
    ) -> Dict[str, ExtractedField]:
        fields = {}

        # SGOT
        sgot_match = re.search(r"sgot[:\s\(A-Za-z\)]*(\d+\.?\d*)", text, re.IGNORECASE)
        if sgot_match:
            fields["sgot"] = self._make_field(float(sgot_match.group(1)), source)

        # SGPT
        sgpt_match = re.search(r"sgpt[:\s\(A-Za-z\)]*(\d+\.?\d*)", text, re.IGNORECASE)
        if sgpt_match:
            fields["sgpt"] = self._make_field(float(sgpt_match.group(1)), source)

        # Liver status
        liver_match = re.search(
            r"liver\s*status[:\s]+(Normal|Abnormal)", text, re.IGNORECASE
        )
        if liver_match:
            fields["liver_status"] = self._make_field(
                liver_match.group(1).capitalize(), source
            )

        # Creatinine
        creat_match = re.search(r"creatinine[:\s]+(\d+\.?\d*)", text, re.IGNORECASE)
        if creat_match:
            fields["creatinine"] = self._make_field(float(creat_match.group(1)), source)

        # Urea
        urea_match = re.search(r"urea[:\s]+(\d+\.?\d*)", text, re.IGNORECASE)
        if urea_match:
            fields["urea"] = self._make_field(float(urea_match.group(1)), source)

        # Kidney status
        kidney_match = re.search(
            r"kidney\s*status[:\s]+(Normal|Abnormal)", text, re.IGNORECASE
        )
        if kidney_match:
            fields["kidney_status"] = self._make_field(
                kidney_match.group(1).capitalize(), source
            )

        return fields

    def _extract_lifestyle(self, text: str, source: str) -> Dict[str, ExtractedField]:
        fields = {}

        # Smoking
        smoking_match = re.search(
            r"smoking(?:\s*status)?[:\s]+(Yes|No)", text, re.IGNORECASE
        )
        if smoking_match:
            fields["smoking_status"] = self._make_field(
                smoking_match.group(1).capitalize(), source
            )

        # Alcohol - handle "Yes" or descriptive text
        alcohol_match = re.search(
            r"alcohol(?:\s*consumption)?[:\s]+(Yes|No)", text, re.IGNORECASE
        )
        if alcohol_match:
            fields["alcohol_status"] = self._make_field(
                alcohol_match.group(1).capitalize(), source
            )

        # Alcohol frequency
        freq_match = re.search(
            r"alcohol\s*frequency[:\s]+([^\n]+)", text, re.IGNORECASE
        )
        if freq_match:
            fields["alcohol_frequency"] = self._make_field(
                freq_match.group(1).strip(), source
            )

        # Hazardous occupation
        hazard_match = re.search(
            r"hazardous\s*(?:occupation|hobby)[:\s]+(Yes|No)", text, re.IGNORECASE
        )
        if hazard_match:
            fields["hazardous_occupation"] = self._make_field(
                hazard_match.group(1).capitalize(), source
            )

        return fields

    def _extract_financial(self, text: str, source: str) -> Dict[str, ExtractedField]:
        fields = {}

        # Annual income
        income_match = re.search(
            r"annual\s*income[:\s]+(?:Rs\.?|₹)?\s*(\d+)", text, re.IGNORECASE
        )
        if income_match:
            fields["annual_income"] = self._make_field(
                int(income_match.group(1)), source
            )

        # Existing insurance
        existing_match = re.search(
            r"existing\s*(?:insurance)?(?:\s*cover)?(?:\s*amount)?[:\s]+(?:Rs\.?|₹)?\s*(\d+)",
            text,
            re.IGNORECASE,
        )
        if existing_match:
            fields["existing_insurance"] = self._make_field(
                int(existing_match.group(1)), source
            )

        return fields
