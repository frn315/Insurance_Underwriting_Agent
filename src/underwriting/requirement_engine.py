"""
Requirement Determination Engine.
Answers: "What evidence is required to underwrite this case?"

Based on:
- Age
- Sum Assured (SA)
- Product
- Channel
- Disclosures
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from src.domain.risk_case import (
    RiskCase,
    Requirement,
    RequirementStatus,
    ProposalContext,
)


class RequirementCategory(str, Enum):
    MEDICAL = "MEDICAL"
    FINANCIAL = "FINANCIAL"
    KYC = "KYC"
    THIRD_PARTY = "THIRD_PARTY"


# ============================================================================
# MEDICAL GRID (Based on Sum Assured slabs - IRDAI standard)
# ============================================================================

# Sum Assured slabs and required tests
SA_MEDICAL_GRID = {
    # SA Range: (min, max) -> List of required tests
    (0, 2500000): ["Basic_Proposal"],  # Up to 25L: No medicals required
    (2500001, 5000000): ["Basic_Proposal", "PPBS", "HIV"],  # 25L-50L
    (5000001, 10000000): ["Full_Medical", "Lipid_Profile", "LFT", "KFT", "HIV"],
    (10000001, 25000000): [
        "Full_Medical",
        "ECG",
        "Lipid_Profile",
        "LFT",
        "KFT",
        "HIV",
        "HbA1c",
    ],
    (25000001, 50000000): [
        "Full_Medical",
        "ECG",
        "TMT",
        "Full_Blood",
        "HIV",
        "HbA1c",
        "USG_Abdomen",
    ],
    (50000001, 100000000): [
        "Full_Medical",
        "ECG",
        "2D_Echo",
        "TMT",
        "Full_Blood",
        "HIV",
        "HbA1c",
        "CT_Chest",
    ],
    (100000001, float("inf")): [
        "Full_Medical",
        "ECG",
        "2D_Echo",
        "TMT",
        "Full_Blood",
        "HIV",
        "HbA1c",
        "CT_Chest",
        "Specialist_Opinion",
    ],
}

# Age modifiers (additional tests based on age)
AGE_MEDICAL_MODIFIERS = {
    (0, 35): [],
    (36, 45): ["ECG"],  # ECG mandatory above 35
    (46, 55): ["ECG", "Lipid_Profile", "HbA1c"],
    (56, 60): ["ECG", "TMT", "Lipid_Profile", "HbA1c", "PSA_if_male"],
    (61, 65): ["ECG", "2D_Echo", "TMT", "Full_Blood", "HbA1c"],
}

# Disclosure-triggered requirements
DISCLOSURE_REQUIREMENTS = {
    "diabetes": ["HbA1c", "FBS", "PPBS", "KFT", "Urine_ACR", "Fundoscopy"],
    "hypertension": ["ECG", "2D_Echo", "KFT", "Fundoscopy"],
    "heart_disease": ["ECG", "2D_Echo", "TMT", "Angiography_if_needed"],
    "cancer_history": ["Oncologist_Report", "PET_CT", "Tumor_Markers"],
    "kidney_disease": ["KFT_Series", "Nephrologist_Opinion", "USG_Kidney"],
    "liver_disease": ["LFT_Series", "Fibroscan", "Gastroenterologist_Opinion"],
    "respiratory": ["PFT", "Chest_Xray", "HRCT_if_needed"],
    "psychiatric": ["Psychiatrist_Report"],
    "smoking": ["Cotinine_Test"],
    "heavy_alcohol": ["GGT", "MCV", "Liver_Screen"],
}


# ============================================================================
# FINANCIAL GRID (Based on SA/Income ratio)
# ============================================================================

SA_INCOME_RATIO_REQUIREMENTS = {
    # HLV multiplier thresholds
    (0, 10): ["Income_Declaration"],  # Normal - SA is < 10x income
    (10, 15): ["Income_Declaration", "ITR_1year"],
    (15, 20): ["ITR_2years", "Bank_Statement_6months"],
    (20, 25): ["ITR_3years", "Bank_Statement_12months", "CA_Certificate"],
    (25, float("inf")): ["ITR_3years", "Networth_Statement", "Special_Approval"],
}


@dataclass
class RequirementSet:
    """Set of requirements determined for a case."""

    medical_requirements: List[Requirement] = field(default_factory=list)
    financial_requirements: List[Requirement] = field(default_factory=list)
    kyc_requirements: List[Requirement] = field(default_factory=list)
    third_party_requirements: List[Requirement] = field(default_factory=list)

    @property
    def all_requirements(self) -> List[Requirement]:
        return (
            self.medical_requirements
            + self.financial_requirements
            + self.kyc_requirements
            + self.third_party_requirements
        )

    @property
    def total_count(self) -> int:
        return len(self.all_requirements)

    def to_summary(self) -> Dict[str, Any]:
        return {
            "medical": [r.requirement_type for r in self.medical_requirements],
            "financial": [r.requirement_type for r in self.financial_requirements],
            "kyc": [r.requirement_type for r in self.kyc_requirements],
            "third_party": [r.requirement_type for r in self.third_party_requirements],
            "total": self.total_count,
        }


class RequirementEngine:
    """
    Determines what evidence is required for underwriting.
    This runs BEFORE policy checks.
    """

    def __init__(self):
        self.req_counter = 0

    def _make_req_id(self) -> str:
        self.req_counter += 1
        return f"REQ-{self.req_counter:04d}"

    def determine(self, risk_case: RiskCase) -> RequirementSet:
        """
        Determine all requirements for this case.
        """
        print("\n" + "=" * 60)
        print("[REQUIREMENT ENGINE]")
        print("=" * 60)

        result = RequirementSet()

        if not risk_case.proposal:
            print("  [ERROR] No proposal context in RiskCase")
            return result

        proposal = risk_case.proposal
        identity = risk_case.identity

        print(f"  Proposal: {proposal.proposal_id}")
        print(f"  Sum Assured: ₹{proposal.sum_assured:,.0f}")
        print(f"  Age: {identity.age if identity else 'Unknown'}")

        # 1. Medical Requirements (SA-based)
        print("\n  [Medical Grid - SA Based]")
        sa = proposal.sum_assured
        for (min_sa, max_sa), tests in SA_MEDICAL_GRID.items():
            if min_sa <= sa <= max_sa:
                print(f"    SA Slab: ₹{min_sa:,} - ₹{max_sa:,}")
                for test in tests:
                    req = Requirement(
                        requirement_id=self._make_req_id(),
                        category=RequirementCategory.MEDICAL.value,
                        requirement_type=test,
                        description=f"Required for SA slab",
                        triggered_by=f"SA_SLAB_{min_sa}_{max_sa}",
                    )
                    result.medical_requirements.append(req)
                    print(f"      + {test}")
                break

        # 2. Age modifiers
        if identity and identity.age:
            print("\n  [Medical Grid - Age Based]")
            age = identity.age
            for (min_age, max_age), tests in AGE_MEDICAL_MODIFIERS.items():
                if min_age <= age <= max_age:
                    print(f"    Age Band: {min_age}-{max_age} years")
                    for test in tests:
                        # Check if not already added
                        existing = [
                            r.requirement_type for r in result.medical_requirements
                        ]
                        if test not in existing:
                            req = Requirement(
                                requirement_id=self._make_req_id(),
                                category=RequirementCategory.MEDICAL.value,
                                requirement_type=test,
                                description=f"Required for age {age}",
                                triggered_by=f"AGE_BAND_{min_age}_{max_age}",
                            )
                            result.medical_requirements.append(req)
                            print(f"      + {test}")
                    break

        # 3. Disclosure triggers
        print("\n  [Disclosure-Triggered Requirements]")
        disclosures = self._extract_disclosures(risk_case)
        for disclosure in disclosures:
            if disclosure in DISCLOSURE_REQUIREMENTS:
                tests = DISCLOSURE_REQUIREMENTS[disclosure]
                print(f"    Disclosure: {disclosure}")
                for test in tests:
                    existing = [r.requirement_type for r in result.medical_requirements]
                    if test not in existing:
                        req = Requirement(
                            requirement_id=self._make_req_id(),
                            category=RequirementCategory.MEDICAL.value,
                            requirement_type=test,
                            description=f"Triggered by {disclosure} disclosure",
                            triggered_by=f"DISCLOSURE_{disclosure.upper()}",
                        )
                        result.medical_requirements.append(req)
                        print(f"      + {test}")

        # 4. Financial Requirements
        print("\n  [Financial Requirements]")
        if risk_case.financial.income.declared_annual:
            declared_income = risk_case.financial.income.declared_annual.value
            if declared_income and declared_income > 0:
                ratio = sa / declared_income
                print(f"    SA/Income Ratio: {ratio:.1f}x")
                for (
                    min_ratio,
                    max_ratio,
                ), docs in SA_INCOME_RATIO_REQUIREMENTS.items():
                    if min_ratio <= ratio < max_ratio:
                        for doc in docs:
                            req = Requirement(
                                requirement_id=self._make_req_id(),
                                category=RequirementCategory.FINANCIAL.value,
                                requirement_type=doc,
                                description=f"Required for SA/Income ratio {ratio:.1f}x",
                                triggered_by=f"INCOME_RATIO_{min_ratio}_{max_ratio}",
                            )
                            result.financial_requirements.append(req)
                            print(f"      + {doc}")
                        break
        else:
            # Default financial requirements
            for doc in ["Income_Declaration", "PAN_Verification"]:
                req = Requirement(
                    requirement_id=self._make_req_id(),
                    category=RequirementCategory.FINANCIAL.value,
                    requirement_type=doc,
                    description="Standard requirement",
                    triggered_by="DEFAULT",
                )
                result.financial_requirements.append(req)
                print(f"      + {doc}")

        # 5. KYC Requirements (always required)
        print("\n  [KYC Requirements]")
        for doc in ["Aadhaar_Verification", "PAN_Verification", "Photo_ID"]:
            req = Requirement(
                requirement_id=self._make_req_id(),
                category=RequirementCategory.KYC.value,
                requirement_type=doc,
                description="Mandatory KYC",
                triggered_by="MANDATORY_KYC",
            )
            result.kyc_requirements.append(req)
            print(f"      + {doc}")

        # 6. Third-party Requirements
        print("\n  [Third-Party Checks]")
        for check in ["CIBIL_Score", "IIB_Claims_Check"]:
            req = Requirement(
                requirement_id=self._make_req_id(),
                category=RequirementCategory.THIRD_PARTY.value,
                requirement_type=check,
                description="Bureau check",
                triggered_by="MANDATORY_BUREAU",
            )
            result.third_party_requirements.append(req)
            print(f"      + {check}")

        # Summary
        print("\n  " + "-" * 40)
        print(f"  TOTAL REQUIREMENTS: {result.total_count}")
        print(f"    Medical: {len(result.medical_requirements)}")
        print(f"    Financial: {len(result.financial_requirements)}")
        print(f"    KYC: {len(result.kyc_requirements)}")
        print(f"    Third-Party: {len(result.third_party_requirements)}")

        # Log to audit trail
        risk_case.log_audit(
            action="REQUIREMENTS_DETERMINED",
            actor="SYSTEM",
            component="RequirementEngine",
            new_value=str(result.total_count),
            reason=f"SA={sa:,.0f}, Age={identity.age if identity else 'N/A'}",
        )

        # Add all requirements to risk case
        for req in result.all_requirements:
            risk_case.add_requirement(req)

        return result

    def _extract_disclosures(self, risk_case: RiskCase) -> List[str]:
        """Extract disclosures from the risk case."""
        disclosures = []

        # Check diabetes
        if risk_case.medical.diabetes.is_diabetic.value in ["Yes", "Prediabetic"]:
            disclosures.append("diabetes")

        # Check smoking
        if risk_case.lifestyle.smoking.status == "Current":
            disclosures.append("smoking")

        # Check alcohol
        if risk_case.lifestyle.alcohol.status == "Heavy":
            disclosures.append("heavy_alcohol")

        # Check hypertension (from BP readings or medical history)
        if (
            risk_case.medical.history
            and "hypertension" in str(risk_case.medical.history.conditions).lower()
        ):
            disclosures.append("hypertension")

        return disclosures
