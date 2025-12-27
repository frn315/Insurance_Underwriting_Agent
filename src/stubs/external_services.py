"""
External Service Stubs.
These consume patient_profile.txt and return deterministic outputs.
In , these would call actual APIs.
"""

from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    PENDING = "PENDING"


class CreditBand(str, Enum):
    EXCELLENT = "EXCELLENT"  # 750+
    GOOD = "GOOD"  # 650-749
    FAIR = "FAIR"  # 550-649
    POOR = "POOR"  # Below 550


class FraudRisk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class KYCResult:
    """KYC Verification Result."""

    status: VerificationStatus
    aadhaar_verified: bool
    pan_verified: bool
    name_match: bool
    address_match: bool
    remarks: str


@dataclass
class CIBILResult:
    """Credit Bureau Check Result."""

    score: int
    band: CreditBand
    active_loans: int
    credit_utilization_pct: int
    payment_history: str
    remarks: str


@dataclass
class IIBResult:
    """Insurance Information Bureau Result."""

    claims_found: bool
    claims_count: int
    fraud_flag: bool
    fraud_risk: FraudRisk
    cumulative_sum_assured: int
    remarks: str


class KYCService:
    """
    STUB: KYC Verification Service.
    In  → DigiLocker API, NSDL PAN verification.
    """

    @staticmethod
    def verify(profile: Dict[str, Any]) -> KYCResult:
        """
        Verify KYC from patient profile.
        STUB: Returns deterministic success.
        """
        aadhaar = str(profile.get("aadhaar", ""))
        pan = str(profile.get("pan", ""))
        name = str(profile.get("full_name", "Unknown"))

        print(f"[STUB:KYC] Verifying: {name}")
        print(f"  Aadhaar: {aadhaar[:4] if aadhaar else 'N/A'}****")
        print(f"  PAN: {pan[:4] if pan else 'N/A'}****")

        return KYCResult(
            status=VerificationStatus.VERIFIED,
            aadhaar_verified=bool(aadhaar),
            pan_verified=bool(pan),
            name_match=True,
            address_match=True,
            remarks="KYC verified successfully (STUB)",
        )


class CIBILService:
    """
    STUB: CIBIL Credit Bureau Service.
    In  → TransUnion CIBIL API.
    """

    # Stub scores based on profile characteristics
    DEFAULT_SCORE = 750

    @staticmethod
    def check(profile: Dict[str, Any]) -> CIBILResult:
        """
        Check credit score from patient profile.
        STUB: Returns deterministic good score.
        """
        name = str(profile.get("full_name", "Unknown"))
        pan = str(profile.get("pan", ""))

        print(f"[STUB:CIBIL] Checking credit for: {name}")
        print(f"  PAN: {pan[:4] if pan else 'N/A'}****")

        score = CIBILService.DEFAULT_SCORE

        # Determine band
        if score >= 750:
            band = CreditBand.EXCELLENT
        elif score >= 650:
            band = CreditBand.GOOD
        elif score >= 550:
            band = CreditBand.FAIR
        else:
            band = CreditBand.POOR

        return CIBILResult(
            score=score,
            band=band,
            active_loans=1,
            credit_utilization_pct=30,
            payment_history="GOOD",
            remarks=f"Credit score {score} - {band.value} (STUB)",
        )


class IIBService:
    """
    STUB: Insurance Information Bureau (IIB) / Sibyl.
    In  → IIB API for claims history and fraud check.
    """

    @staticmethod
    def check(profile: Dict[str, Any]) -> IIBResult:
        """
        Check insurance claims history and fraud flags.
        STUB: Returns deterministic clean result.
        """
        name = str(profile.get("full_name", "Unknown"))
        aadhaar = str(profile.get("aadhaar", ""))

        print(f"[STUB:IIB] Checking claims history for: {name}")

        return IIBResult(
            claims_found=False,
            claims_count=0,
            fraud_flag=False,
            fraud_risk=FraudRisk.LOW,
            cumulative_sum_assured=0,
            remarks="No claims history, no fraud flags (STUB)",
        )


class ExternalCheckRunner:
    """
    Runs all external checks on a patient profile.
    """

    def __init__(self):
        self.kyc = KYCService()
        self.cibil = CIBILService()
        self.iib = IIBService()

    def run_all(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Run all external checks and return aggregated results."""
        print("\n" + "=" * 50)
        print("[EXTERNAL CHECKS]")
        print("=" * 50)

        kyc_result = self.kyc.verify(profile)
        cibil_result = self.cibil.check(profile)
        iib_result = self.iib.check(profile)

        # Aggregate findings
        all_passed = (
            kyc_result.status == VerificationStatus.VERIFIED
            and cibil_result.band in [CreditBand.EXCELLENT, CreditBand.GOOD]
            and not iib_result.fraud_flag
        )

        print("\n[Results Summary]")
        print(f"  KYC: {kyc_result.status.value}")
        print(f"  CIBIL: {cibil_result.score} ({cibil_result.band.value})")
        print(f"  IIB Fraud: {'YES' if iib_result.fraud_flag else 'NO'}")
        print(f"  Overall: {'PASS' if all_passed else 'FAIL'}")

        return {
            "kyc": {
                "status": kyc_result.status.value,
                "aadhaar_verified": kyc_result.aadhaar_verified,
                "pan_verified": kyc_result.pan_verified,
                "remarks": kyc_result.remarks,
            },
            "cibil": {
                "score": cibil_result.score,
                "band": cibil_result.band.value,
                "active_loans": cibil_result.active_loans,
                "remarks": cibil_result.remarks,
            },
            "iib": {
                "claims_found": iib_result.claims_found,
                "claims_count": iib_result.claims_count,
                "fraud_flag": iib_result.fraud_flag,
                "fraud_risk": iib_result.fraud_risk.value,
                "remarks": iib_result.remarks,
            },
            "all_passed": all_passed,
        }
