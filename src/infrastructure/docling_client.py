"""
 Docling Client with Enhanced Extraction.
Includes pattern recognition for PAN, Aadhaar, and table parsing.
"""

import os
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path


class DoclingExtractor:
    """
     document extractor using IBM Docling.
    Enhanced with pattern recognition for Indian documents.
    """

    def __init__(self):
        from docling.document_converter import DocumentConverter

        self.converter = DocumentConverter()

    def extract_document(self, file_path: str) -> Dict[str, Any]:
        """Extract structured data from a document."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document not found: {file_path}")

        print(f"[Docling] Processing: {os.path.basename(file_path)}")

        result = self.converter.convert(file_path)
        document = result.document
        markdown_text = document.export_to_markdown()

        # Extract using multiple methods
        key_values = self._extract_key_values(markdown_text)
        patterns = self._extract_patterns(markdown_text)
        tables = self._extract_tables(document)
        table_values = self._parse_medical_tables(tables)

        # Merge all extracted data
        key_values.update(patterns)
        key_values.update(table_values)

        page_count = len(document.pages) if hasattr(document, "pages") else 1

        return {
            "file_path": file_path,
            "text": markdown_text,
            "tables": tables,
            "key_values": key_values,
            "page_count": page_count,
            "extraction_timestamp": datetime.utcnow().isoformat(),
        }

    def _extract_patterns(self, text: str) -> Dict[str, str]:
        """Extract values using regex patterns for Indian documents."""
        extracted = {}

        # PAN Pattern: ABCDE1234F
        pan_match = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", text)
        if pan_match:
            extracted["pan_number"] = pan_match.group(1)

        # Aadhaar Pattern: 1234 5678 9012 or 123456789012
        aadhaar_match = re.search(r"\b(\d{4}\s?\d{4}\s?\d{4})\b", text)
        if aadhaar_match:
            extracted["aadhaar_number"] = aadhaar_match.group(1).replace(" ", "")

        # Date patterns: DD/MM/YYYY or DD-MM-YYYY
        dob_match = re.search(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b", text)
        if dob_match:
            extracted["date_of_birth"] = dob_match.group(1)

        # Age pattern: XX years or Age: XX
        age_match = re.search(
            r"(?:age[:\s]*)?(\d{1,3})\s*(?:years?|yrs?)?", text.lower()
        )
        if age_match and 1 <= int(age_match.group(1)) <= 120:
            extracted["age"] = age_match.group(1)

        # Name after "Name" keyword - look for capitalized words
        name_match = re.search(
            r"(?:name|applicant|patient)[:\s/]*##?\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
            text,
            re.IGNORECASE,
        )
        if name_match:
            extracted["full_name"] = name_match.group(1).strip()

        # Gender
        if re.search(r"\bmale\b", text, re.IGNORECASE):
            extracted["gender"] = "Male"
        elif re.search(r"\bfemale\b", text, re.IGNORECASE):
            extracted["gender"] = "Female"

        # Medical values with units
        # HbA1c
        hba1c_match = re.search(
            r"(?:hba1c|a1c|glycated)[:\s]*(\d+\.?\d*)\s*%?", text, re.IGNORECASE
        )
        if hba1c_match:
            extracted["hba1c"] = hba1c_match.group(1)

        # FBS
        fbs_match = re.search(
            r"(?:fbs|fasting\s*(?:blood\s*)?sugar|fbg)[:\s]*(\d+\.?\d*)",
            text,
            re.IGNORECASE,
        )
        if fbs_match:
            extracted["fbs"] = fbs_match.group(1)

        # Blood Pressure
        bp_match = re.search(
            r"(?:bp|blood\s*pressure)[:\s]*(\d{2,3})\s*[/\-]\s*(\d{2,3})",
            text,
            re.IGNORECASE,
        )
        if bp_match:
            extracted["systolic_bp"] = bp_match.group(1)
            extracted["diastolic_bp"] = bp_match.group(2)

        # BMI
        bmi_match = re.search(
            r"(?:bmi|body\s*mass)[:\s]*(\d+\.?\d*)", text, re.IGNORECASE
        )
        if bmi_match:
            extracted["bmi"] = bmi_match.group(1)

        # Height
        height_match = re.search(
            r"(?:height|ht)[:\s]*(\d+\.?\d*)\s*(?:cm)?", text, re.IGNORECASE
        )
        if height_match:
            extracted["height_cm"] = height_match.group(1)

        # Weight
        weight_match = re.search(
            r"(?:weight|wt)[:\s]*(\d+\.?\d*)\s*(?:kg)?", text, re.IGNORECASE
        )
        if weight_match:
            extracted["weight_kg"] = weight_match.group(1)

        # Cholesterol
        chol_match = re.search(
            r"(?:total\s*)?cholesterol[:\s]*(\d+\.?\d*)", text, re.IGNORECASE
        )
        if chol_match:
            extracted["cholesterol"] = chol_match.group(1)

        # Creatinine
        creat_match = re.search(r"creatinine[:\s]*(\d+\.?\d*)", text, re.IGNORECASE)
        if creat_match:
            extracted["creatinine"] = creat_match.group(1)

        # Sum Assured / Policy Amount
        sa_match = re.search(
            r"(?:sum\s*assured|sum\s*insured|cover)[:\s]*(?:Rs\.?|₹)?\s*(\d[\d,]*)",
            text,
            re.IGNORECASE,
        )
        if sa_match:
            extracted["sum_assured"] = sa_match.group(1).replace(",", "")

        # Income
        income_match = re.search(
            r"(?:annual\s*)?income[:\s]*(?:Rs\.?|₹)?\s*(\d[\d,]*)", text, re.IGNORECASE
        )
        if income_match:
            extracted["annual_income"] = income_match.group(1).replace(",", "")

        return extracted

    def _extract_key_values(self, text: str) -> Dict[str, str]:
        """Extract key-value pairs from text."""
        key_values = {}
        pattern = r"([A-Za-z][A-Za-z0-9\s\/\(\)\-\.]+?)\s*[:\-]\s*([^\n\|]+)"
        matches = re.findall(pattern, text)

        for key, value in matches:
            key_clean = (
                key.strip()
                .lower()
                .replace(" ", "_")
                .replace("/", "_")
                .replace(".", "")
                .replace("-", "_")
            )
            value_clean = value.strip()

            if (
                key_clean
                and value_clean
                and len(key_clean) < 50
                and len(value_clean) < 200
            ):
                if any(c.isalpha() for c in key_clean):
                    key_values[key_clean] = value_clean

        return key_values

    def _extract_tables(self, document) -> List[Dict[str, Any]]:
        """Extract tables from document."""
        tables = []
        if hasattr(document, "tables"):
            for idx, table in enumerate(document.tables):
                table_data = {"index": idx, "rows": []}
                if hasattr(table, "data"):
                    for row in table.data:
                        table_data["rows"].append([str(cell) for cell in row])
                tables.append(table_data)
        return tables

    def _parse_medical_tables(self, tables: List[Dict]) -> Dict[str, str]:
        """Parse medical values from tables."""
        extracted = {}

        # Common medical test names to look for
        medical_keys = {
            "fbs": ["fbs", "fasting blood sugar", "fasting glucose"],
            "ppbs": ["ppbs", "post prandial", "pp sugar"],
            "hba1c": ["hba1c", "glycated haemoglobin", "a1c"],
            "cholesterol": ["cholesterol", "total cholesterol"],
            "hdl": ["hdl", "hdl cholesterol"],
            "ldl": ["ldl", "ldl cholesterol"],
            "triglycerides": ["triglycerides", "tg"],
            "creatinine": ["creatinine", "serum creatinine"],
            "urea": ["urea", "blood urea"],
            "sgot": ["sgot", "ast"],
            "sgpt": ["sgpt", "alt"],
        }

        for table in tables:
            for row in table.get("rows", []):
                if len(row) >= 2:
                    key_cell = str(row[0]).lower()
                    value_cell = str(row[1]) if len(row) > 1 else ""

                    for field, aliases in medical_keys.items():
                        if any(alias in key_cell for alias in aliases):
                            # Extract numeric value
                            num_match = re.search(r"(\d+\.?\d*)", value_cell)
                            if num_match:
                                extracted[field] = num_match.group(1)
                            break

        return extracted


class PatientProfileWriter:
    """
    Creates a curated patient profile document from extracted data.
    This profile is used by AI agents for underwriting.
    """

    @staticmethod
    def generate_profile(graph: "EvidenceGraph", output_path: str) -> str:
        """Generate a human-readable patient profile file."""
        lines = []

        lines.append("=" * 60)
        lines.append("PATIENT PROFILE FOR UNDERWRITING")
        lines.append("=" * 60)
        lines.append(f"Generated: {datetime.utcnow().isoformat()}")
        lines.append(f"Application ID: {graph.application_id or 'N/A'}")
        lines.append("")

        # Identity Section
        lines.append("-" * 40)
        lines.append("SECTION 1: IDENTITY & KYC")
        lines.append("-" * 40)
        lines.append(
            PatientProfileWriter._format_field("Full Name", graph.identity.full_name)
        )
        lines.append(
            PatientProfileWriter._format_field(
                "Date of Birth", graph.identity.date_of_birth
            )
        )
        lines.append(
            PatientProfileWriter._format_field("Age (years)", graph.identity.age)
        )
        lines.append(
            PatientProfileWriter._format_field("Gender", graph.identity.gender)
        )
        lines.append(
            PatientProfileWriter._format_field("PAN Number", graph.identity.pan_number)
        )
        lines.append(
            PatientProfileWriter._format_field(
                "Aadhaar Number", graph.identity.aadhaar_number
            )
        )
        lines.append(
            PatientProfileWriter._format_field(
                "Address", graph.identity.current_address
            )
        )
        lines.append("")

        # Medical Vitals
        lines.append("-" * 40)
        lines.append("SECTION 2: MEDICAL VITALS")
        lines.append("-" * 40)
        lines.append(
            PatientProfileWriter._format_field(
                "Height (cm)", graph.medical.vitals.height_cm
            )
        )
        lines.append(
            PatientProfileWriter._format_field(
                "Weight (kg)", graph.medical.vitals.weight_kg
            )
        )
        lines.append(
            PatientProfileWriter._format_field("BMI", graph.medical.vitals.bmi)
        )
        lines.append(
            PatientProfileWriter._format_field(
                "Systolic BP (mmHg)", graph.medical.vitals.systolic_bp
            )
        )
        lines.append(
            PatientProfileWriter._format_field(
                "Diastolic BP (mmHg)", graph.medical.vitals.diastolic_bp
            )
        )
        lines.append(
            PatientProfileWriter._format_field(
                "Pulse (bpm)", graph.medical.vitals.pulse
            )
        )
        lines.append("")

        # Diabetes Panel
        lines.append("-" * 40)
        lines.append("SECTION 3: DIABETES PANEL")
        lines.append("-" * 40)
        lines.append(
            PatientProfileWriter._format_field(
                "Fasting Blood Sugar (mg/dL)", graph.medical.diabetes.fbs
            )
        )
        lines.append(
            PatientProfileWriter._format_field(
                "Post-Prandial Sugar (mg/dL)", graph.medical.diabetes.ppbs
            )
        )
        lines.append(
            PatientProfileWriter._format_field(
                "HbA1c (%)", graph.medical.diabetes.hba1c
            )
        )
        lines.append("")

        # Lipid Profile
        lines.append("-" * 40)
        lines.append("SECTION 4: LIPID PROFILE")
        lines.append("-" * 40)
        lines.append(
            PatientProfileWriter._format_field(
                "Total Cholesterol (mg/dL)", graph.medical.lipid.total_cholesterol
            )
        )
        lines.append(
            PatientProfileWriter._format_field(
                "LDL Cholesterol (mg/dL)", graph.medical.lipid.ldl
            )
        )
        lines.append(
            PatientProfileWriter._format_field(
                "HDL Cholesterol (mg/dL)", graph.medical.lipid.hdl
            )
        )
        lines.append(
            PatientProfileWriter._format_field(
                "Triglycerides (mg/dL)", graph.medical.lipid.triglycerides
            )
        )
        lines.append("")

        # Organ Function
        lines.append("-" * 40)
        lines.append("SECTION 5: LIVER & KIDNEY FUNCTION")
        lines.append("-" * 40)
        lines.append(
            PatientProfileWriter._format_field("SGOT (U/L)", graph.medical.liver.sgot)
        )
        lines.append(
            PatientProfileWriter._format_field("SGPT (U/L)", graph.medical.liver.sgpt)
        )
        lines.append(
            PatientProfileWriter._format_field(
                "Creatinine (mg/dL)", graph.medical.renal.creatinine
            )
        )
        lines.append(
            PatientProfileWriter._format_field("Urea (mg/dL)", graph.medical.renal.urea)
        )
        lines.append("")

        # Lifestyle
        lines.append("-" * 40)
        lines.append("SECTION 6: LIFESTYLE")
        lines.append("-" * 40)
        lines.append(
            PatientProfileWriter._format_field(
                "Smoking Status", graph.lifestyle.smoking_status
            )
        )
        lines.append(
            PatientProfileWriter._format_field(
                "Alcohol Status", graph.lifestyle.alcohol_status
            )
        )
        if graph.lifestyle.hazardous_hobbies:
            lines.append(
                PatientProfileWriter._format_field(
                    "Hazardous Hobbies", graph.lifestyle.hazardous_hobbies
                )
            )
        lines.append("")

        # Financial
        lines.append("-" * 40)
        lines.append("SECTION 7: FINANCIAL")
        lines.append("-" * 40)
        lines.append(
            PatientProfileWriter._format_field(
                "Annual Income (₹)", graph.financial.declared_annual_income
            )
        )
        lines.append(
            PatientProfileWriter._format_field(
                "Sum Assured Requested (₹)", graph.financial.sum_assured_requested
            )
        )
        lines.append(
            PatientProfileWriter._format_field(
                "Existing Cover (₹)", graph.financial.existing_cover_amount
            )
        )
        lines.append("")

        # Occupation
        lines.append("-" * 40)
        lines.append("SECTION 8: OCCUPATION")
        lines.append("-" * 40)
        lines.append(
            PatientProfileWriter._format_field(
                "Occupation", graph.occupational.occupation
            )
        )
        lines.append(
            PatientProfileWriter._format_field(
                "Employer", graph.occupational.employer_name
            )
        )
        lines.append("")

        # Bureau
        lines.append("-" * 40)
        lines.append("SECTION 9: BUREAU CHECKS")
        lines.append("-" * 40)
        lines.append(
            PatientProfileWriter._format_field("CIBIL Score", graph.bureau.cibil_score)
        )
        lines.append(
            PatientProfileWriter._format_field(
                "IIB Fraud Flag", graph.bureau.iib_fraud_flag
            )
        )
        lines.append("")

        # Missing Fields Summary
        lines.append("=" * 60)
        lines.append("MISSING/INCOMPLETE FIELDS")
        lines.append("=" * 60)
        missing = PatientProfileWriter._get_missing_fields(graph)
        if missing:
            for field in missing:
                lines.append(f"  [!] {field}")
        else:
            lines.append("  All critical fields present")
        lines.append("")

        lines.append("=" * 60)
        lines.append("END OF PROFILE")
        lines.append("=" * 60)

        content = "\n".join(lines)

        # Write to file
        with open(output_path, "w") as f:
            f.write(content)

        print(f"[Profile] Written to: {output_path}")
        return content

    @staticmethod
    def _format_field(label: str, node) -> str:
        """Format a field for display."""
        if node is None:
            return f"{label}: [MISSING]"

        value = node.value if hasattr(node, "value") else node
        confidence = node.confidence if hasattr(node, "confidence") else 1.0

        if value is None:
            return f"{label}: [MISSING]"

        conf_indicator = ""
        if confidence < 0.8:
            conf_indicator = f" [UNCERTAIN: {confidence:.0%}]"
        elif confidence < 0.95:
            conf_indicator = f" [{confidence:.0%}]"

        return f"{label}: {value}{conf_indicator}"

    @staticmethod
    def _get_missing_fields(graph) -> List[str]:
        """Get list of missing critical fields."""
        missing = []

        # Identity
        if not graph.identity.full_name or not graph.identity.full_name.value:
            missing.append("Full Name")
        if not graph.identity.age or not graph.identity.age.value:
            missing.append("Age")
        if not graph.identity.pan_number or not graph.identity.pan_number.value:
            missing.append("PAN Number")

        # Medical
        if not graph.medical.vitals.bmi or not graph.medical.vitals.bmi.value:
            missing.append("BMI")
        if not graph.medical.diabetes.hba1c or not graph.medical.diabetes.hba1c.value:
            missing.append("HbA1c")

        # Financial
        if (
            not graph.financial.sum_assured_requested
            or not graph.financial.sum_assured_requested.value
        ):
            missing.append("Sum Assured")

        return missing


class FieldMapper:
    """Maps extracted fields to our domain schema."""

    @classmethod
    def find_field(cls, key_values: Dict[str, str], field_name: str) -> Optional[str]:
        """Find a field value - direct match first, then fuzzy."""
        # Direct match
        if field_name in key_values:
            return key_values[field_name]

        # Check variations
        variations = [
            field_name.replace("_", ""),
            field_name.replace("_", " "),
            field_name + "_number",
            field_name + "_no",
        ]

        for var in variations:
            if var in key_values:
                return key_values[var]

        # Fuzzy match
        for key, value in key_values.items():
            if field_name in key or key in field_name:
                return value

        return None

    @classmethod
    def parse_number(cls, value: str) -> Optional[float]:
        if not value:
            return None
        cleaned = value.replace(",", "").replace(" ", "")
        match = re.search(r"[\d]+\.?[\d]*", cleaned)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        return None

    @classmethod
    def calculate_bmi(cls, height_cm: float, weight_kg: float) -> Optional[float]:
        if not height_cm or not weight_kg or height_cm <= 0:
            return None
        height_m = height_cm / 100
        return round(weight_kg / (height_m**2), 1)

    @classmethod
    def calculate_age(cls, dob: str) -> Optional[int]:
        """Calculate age from DOB string."""
        if not dob:
            return None

        formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"]
        for fmt in formats:
            try:
                birth = datetime.strptime(dob, fmt)
                today = datetime.today()
                age = today.year - birth.year
                if (today.month, today.day) < (birth.month, birth.day):
                    age -= 1
                # Sanity check - DOB should be in past
                if birth.year < 1900 or birth > today:
                    continue
                return age
            except:
                continue
        return None


class ProfileBuilder:
    """Builds EvidenceGraph from extracted document data."""

    def __init__(self):
        self.docling = DoclingExtractor()
        self.mapper = FieldMapper()

    def build_from_documents(
        self, document_paths: List[str], app_id: str
    ) -> "EvidenceGraph":
        """Build complete EvidenceGraph from multiple documents."""
        from src.domain.evidence import (
            EvidenceGraph,
            EvidenceNode,
            EvidenceMetadata,
            IdentityEvidence,
            MedicalEvidence,
            LifestyleEvidence,
            FinancialEvidence,
            OccupationalEvidence,
            ConsentEvidence,
            BureauEvidence,
            VitalsEvidence,
            DiabetesPanel,
            LipidPanel,
            LiverFunction,
            RenalFunction,
            UrineAnalysis,
            CardiacEvidence,
            ImagingEvidence,
            SmokingStatus,
            AlcoholStatus,
        )

        # Aggregate all extracted data
        all_key_values = {}

        for doc_path in document_paths:
            try:
                extraction = self.docling.extract_document(doc_path)
                all_key_values.update(extraction["key_values"])
                print(
                    f"  Extracted {len(extraction['key_values'])} fields from {os.path.basename(doc_path)}"
                )
            except Exception as e:
                print(f"  [ERROR] Failed to extract {os.path.basename(doc_path)}: {e}")

        print(f"\n[Total] {len(all_key_values)} unique fields extracted")

        # Helper to create EvidenceNode
        def make_node(value, confidence: float = 0.90):
            if value is None:
                return None
            return EvidenceNode(
                value=value,
                metadata=EvidenceMetadata(
                    source_document_id=f"doc_{app_id}",
                    extraction_model="Docling-Enhanced",
                    confidence_score=confidence,
                ),
            )

        # Extract fields
        name = self.mapper.find_field(
            all_key_values, "full_name"
        ) or self.mapper.find_field(all_key_values, "name")
        pan = self.mapper.find_field(
            all_key_values, "pan_number"
        ) or self.mapper.find_field(all_key_values, "pan")
        aadhaar = self.mapper.find_field(
            all_key_values, "aadhaar_number"
        ) or self.mapper.find_field(all_key_values, "aadhaar")
        dob = self.mapper.find_field(
            all_key_values, "date_of_birth"
        ) or self.mapper.find_field(all_key_values, "dob")
        age_str = self.mapper.find_field(all_key_values, "age")
        age = self.mapper.parse_number(age_str)

        if not age and dob:
            age = self.mapper.calculate_age(dob)

        gender = self.mapper.find_field(all_key_values, "gender")

        # Build Identity
        identity = IdentityEvidence(
            full_name=make_node(name),
            date_of_birth=make_node(dob),
            age=make_node(int(age) if age else None),
            gender=make_node(gender),
            pan_number=make_node(pan),
            aadhaar_number=make_node(aadhaar),
            current_address=make_node(
                self.mapper.find_field(all_key_values, "address")
            ),
        )

        # Build Medical
        height = self.mapper.parse_number(
            self.mapper.find_field(all_key_values, "height_cm")
            or self.mapper.find_field(all_key_values, "height")
        )
        weight = self.mapper.parse_number(
            self.mapper.find_field(all_key_values, "weight_kg")
            or self.mapper.find_field(all_key_values, "weight")
        )
        bmi = self.mapper.parse_number(self.mapper.find_field(all_key_values, "bmi"))

        if not bmi and height and weight:
            bmi = self.mapper.calculate_bmi(height, weight)

        systolic = self.mapper.parse_number(
            self.mapper.find_field(all_key_values, "systolic_bp")
            or self.mapper.find_field(all_key_values, "systolic")
        )
        diastolic = self.mapper.parse_number(
            self.mapper.find_field(all_key_values, "diastolic_bp")
            or self.mapper.find_field(all_key_values, "diastolic")
        )

        vitals = VitalsEvidence(
            height_cm=make_node(height),
            weight_kg=make_node(weight),
            bmi=make_node(bmi),
            systolic_bp=make_node(int(systolic) if systolic else None),
            diastolic_bp=make_node(int(diastolic) if diastolic else None),
            pulse=make_node(
                self.mapper.parse_number(
                    self.mapper.find_field(all_key_values, "pulse")
                )
            ),
        )

        diabetes = DiabetesPanel(
            fbs=make_node(
                self.mapper.parse_number(self.mapper.find_field(all_key_values, "fbs"))
            ),
            ppbs=make_node(
                self.mapper.parse_number(self.mapper.find_field(all_key_values, "ppbs"))
            ),
            hba1c=make_node(
                self.mapper.parse_number(
                    self.mapper.find_field(all_key_values, "hba1c")
                )
            ),
        )

        lipid = LipidPanel(
            total_cholesterol=make_node(
                self.mapper.parse_number(
                    self.mapper.find_field(all_key_values, "cholesterol")
                )
            ),
            ldl=make_node(
                self.mapper.parse_number(self.mapper.find_field(all_key_values, "ldl"))
            ),
            hdl=make_node(
                self.mapper.parse_number(self.mapper.find_field(all_key_values, "hdl"))
            ),
            triglycerides=make_node(
                self.mapper.parse_number(
                    self.mapper.find_field(all_key_values, "triglycerides")
                )
            ),
        )

        liver = LiverFunction(
            sgot=make_node(
                self.mapper.parse_number(self.mapper.find_field(all_key_values, "sgot"))
            ),
            sgpt=make_node(
                self.mapper.parse_number(self.mapper.find_field(all_key_values, "sgpt"))
            ),
        )

        renal = RenalFunction(
            creatinine=make_node(
                self.mapper.parse_number(
                    self.mapper.find_field(all_key_values, "creatinine")
                )
            ),
            urea=make_node(
                self.mapper.parse_number(self.mapper.find_field(all_key_values, "urea"))
            ),
        )

        medical = MedicalEvidence(
            vitals=vitals,
            diabetes=diabetes,
            lipid=lipid,
            liver=liver,
            renal=renal,
            urine=UrineAnalysis(),
            cardiac=CardiacEvidence(),
            imaging=ImagingEvidence(),
        )

        # Lifestyle
        smoking_value = self.mapper.find_field(all_key_values, "smoking")
        smoking_status = None
        if smoking_value:
            sl = smoking_value.lower()
            if any(x in sl for x in ["no", "non", "never", "nil"]):
                smoking_status = SmokingStatus.NON_SMOKER
            elif "ex" in sl or "former" in sl:
                smoking_status = SmokingStatus.EX_SMOKER
            else:
                smoking_status = SmokingStatus.SMOKER

        alcohol_value = self.mapper.find_field(all_key_values, "alcohol")
        alcohol_status = None
        if alcohol_value:
            al = alcohol_value.lower()
            if any(x in al for x in ["no", "non", "never", "nil"]):
                alcohol_status = AlcoholStatus.NON_DRINKER
            elif any(x in al for x in ["social", "occasional"]):
                alcohol_status = AlcoholStatus.SOCIAL
            elif "regular" in al:
                alcohol_status = AlcoholStatus.REGULAR

        lifestyle = LifestyleEvidence(
            smoking_status=make_node(smoking_status) if smoking_status else None,
            alcohol_status=make_node(alcohol_status) if alcohol_status else None,
        )

        # Financial
        income = self.mapper.parse_number(
            self.mapper.find_field(all_key_values, "annual_income")
            or self.mapper.find_field(all_key_values, "income")
        )
        sum_assured = self.mapper.parse_number(
            self.mapper.find_field(all_key_values, "sum_assured")
        )

        financial = FinancialEvidence(
            declared_annual_income=make_node(income) if income else None,
            sum_assured_requested=make_node(sum_assured) if sum_assured else None,
        )

        # Occupation
        occupation = self.mapper.find_field(all_key_values, "occupation")
        occupational = OccupationalEvidence(
            occupation=make_node(occupation) if occupation else None
        )

        return EvidenceGraph(
            graph_id=f"graph_{app_id}_{datetime.utcnow().timestamp()}",
            application_id=app_id,
            identity=identity,
            medical=medical,
            lifestyle=lifestyle,
            financial=financial,
            occupational=occupational,
            bureau=BureauEvidence(),
            consent=ConsentEvidence(),
        )
