"""
Underwriting Pipeline.
Reads ONLY from patient_profile.txt.
Documents are NEVER accessed here.
"""

import os
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class UnderwritingDecision(str, Enum):
    APPROVE = "APPROVE"
    DECLINE = "DECLINE"
    REFER = "REFER"


@dataclass
class PolicyCheckResult:
    rule_id: str
    passed: bool
    details: str


@dataclass
class UnderwritingResult:
    decision: UnderwritingDecision
    policy_checks: List[PolicyCheckResult]
    risk_factors: List[str]
    confidence: float
    reasoning: str


class ProfileParser:
    """Parse patient_profile.txt into structured data."""

    @staticmethod
    def parse(profile_path: str) -> Dict[str, Any]:
        """Parse profile file into dict."""
        if not os.path.exists(profile_path):
            raise FileNotFoundError(f"Profile not found: {profile_path}")

        with open(profile_path, "r") as f:
            content = f.read()

        data = {}

        for line in content.split("\n"):
            if ":" in line and not line.startswith("#"):
                parts = line.split(":", 1)
                key = parts[0].strip().lower()
                value = parts[1].strip()

                if value and value != "[MISSING]":
                    # Try to parse as number
                    try:
                        if "." in value:
                            data[key] = float(value)
                        else:
                            data[key] = int(value)
                    except ValueError:
                        data[key] = value

        return data


class PolicyEngine:
    """
    Hard policy rules.
    No AI, no interpretation - pure code.
    """

    @staticmethod
    def evaluate(profile: Dict[str, Any]) -> List[PolicyCheckResult]:
        """Run all policy checks."""
        results = []

        # Age limits
        age = profile.get("age")
        if age:
            if age < 18:
                results.append(PolicyCheckResult("AGE_MIN", False, f"Age {age} < 18"))
            elif age > 65:
                results.append(PolicyCheckResult("AGE_MAX", False, f"Age {age} > 65"))
            else:
                results.append(
                    PolicyCheckResult("AGE_OK", True, f"Age {age} within limits")
                )
        else:
            results.append(PolicyCheckResult("AGE_MISSING", False, "Age not provided"))

        # BMI limits
        bmi = profile.get("bmi")
        if bmi:
            if bmi > 40:
                results.append(
                    PolicyCheckResult(
                        "BMI_MORBID", False, f"BMI {bmi} > 40 (morbid obesity)"
                    )
                )
            elif bmi > 35:
                results.append(
                    PolicyCheckResult("BMI_HIGH", False, f"BMI {bmi} > 35 (severe)")
                )
            else:
                results.append(
                    PolicyCheckResult("BMI_OK", True, f"BMI {bmi} acceptable")
                )

        # HbA1c limits
        hba1c = profile.get("hba1c")
        if hba1c:
            if hba1c > 10:
                results.append(
                    PolicyCheckResult("DIABETES_SEVERE", False, f"HbA1c {hba1c} > 10")
                )
            elif hba1c > 8.5:
                results.append(
                    PolicyCheckResult(
                        "DIABETES_UNCONTROLLED", False, f"HbA1c {hba1c} > 8.5"
                    )
                )
            else:
                results.append(
                    PolicyCheckResult("DIABETES_OK", True, f"HbA1c {hba1c} acceptable")
                )

        # Liver function
        sgpt = profile.get("sgpt")
        if sgpt:
            if sgpt > 120:  # 3x normal
                results.append(
                    PolicyCheckResult(
                        "LIVER_ELEVATED", False, f"SGPT {sgpt} > 3x normal"
                    )
                )

        # Kidney function
        creatinine = profile.get("creatinine")
        if creatinine:
            if creatinine > 2.0:
                results.append(
                    PolicyCheckResult(
                        "KIDNEY_IMPAIRED", False, f"Creatinine {creatinine} > 2.0"
                    )
                )

        return results


class ReasoningAgent:
    """
    AI reasoning agent.
    Reads profile, evaluates soft risks, provides recommendation.
    """

    def evaluate(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate profile and return structured recommendation.
        In , this would call LLM.
        For now, uses rule-based logic.
        """
        risk_factors = []
        confidence = 0.90

        # Analyze risks
        age = profile.get("age", 35)
        bmi = profile.get("bmi")
        hba1c = profile.get("hba1c")
        smoking = profile.get("smoking", "No")
        alcohol = profile.get("alcohol", "No")

        # Age-based risk
        if age > 50:
            risk_factors.append("Age > 50")
            confidence -= 0.05

        # BMI risk
        if bmi:
            if bmi > 30:
                risk_factors.append(f"Obese (BMI {bmi})")
                confidence -= 0.10
            elif bmi > 25:
                risk_factors.append(f"Overweight (BMI {bmi})")
                confidence -= 0.05

        # Diabetes risk
        if hba1c:
            if hba1c > 7.5:
                risk_factors.append(f"Suboptimal diabetes control (HbA1c {hba1c})")
                confidence -= 0.10
            elif hba1c > 6.5:
                risk_factors.append(f"Diabetic (HbA1c {hba1c})")
                confidence -= 0.05

        # Lifestyle
        if smoking and smoking.lower() == "yes":
            risk_factors.append("Smoker")
            confidence -= 0.10

        if alcohol and alcohol.lower() == "yes":
            risk_factors.append("Alcohol consumer")
            confidence -= 0.03

        # Determine recommendation
        if not risk_factors:
            scenario = "HEALTHY_STANDARD"
            recommendation = "APPROVE"
        elif len(risk_factors) == 1:
            scenario = "SINGLE_RISK_FACTOR"
            recommendation = "APPROVE"
        elif len(risk_factors) <= 3:
            scenario = "MODERATE_RISK"
            recommendation = "REFER"
        else:
            scenario = "HIGH_RISK"
            recommendation = "DECLINE"

        return {
            "scenario": scenario,
            "recommendation": recommendation,
            "risk_factors": risk_factors,
            "confidence": max(0.5, confidence),
        }


class UnderwritingPipeline:
    """
    Main underwriting pipeline.
    Reads ONLY from patient_profile.txt.
    """

    def __init__(self):
        self.parser = ProfileParser()
        self.policy_engine = PolicyEngine()
        self.reasoning_agent = ReasoningAgent()

        # External service stubs
        from src.stubs.external_services import ExternalCheckRunner

        self.external_checks = ExternalCheckRunner()

    def underwrite(self, profile_path: str) -> UnderwritingResult:
        """
        Run full underwriting process.
        """
        print(f"\n{'='*60}")
        print("[UNDERWRITING] Starting...")
        print(f"{'='*60}")
        print(f"Profile: {profile_path}")

        # Parse profile
        profile = self.parser.parse(profile_path)
        print(f"\nParsed {len(profile)} fields from profile")

        # 1. Policy checks
        print("\n[Policy Engine]")
        policy_results = self.policy_engine.evaluate(profile)

        for p in policy_results:
            status = "" if p.passed else "❌"
            print(f"  {status} {p.rule_id}: {p.details}")

        # Check for hard failures
        failed = [p for p in policy_results if not p.passed]
        if failed:
            print("\n[DECISION] DECLINE - Policy violation")
            return UnderwritingResult(
                decision=UnderwritingDecision.DECLINE,
                policy_checks=policy_results,
                risk_factors=[f.details for f in failed],
                confidence=1.0,
                reasoning="Hard policy violation",
            )

        # 2. External Checks (CIBIL, IIB, KYC)
        external_results = self.external_checks.run_all(profile)

        if not external_results["all_passed"]:
            # Check for fraud flag
            if external_results["iib"]["fraud_flag"]:
                print("\n[DECISION] DECLINE - Fraud flag detected")
                return UnderwritingResult(
                    decision=UnderwritingDecision.DECLINE,
                    policy_checks=policy_results,
                    risk_factors=["IIB Fraud Flag"],
                    confidence=1.0,
                    reasoning="Fraud flag from IIB",
                )

            # Check for KYC failure
            if external_results["kyc"]["status"] != "VERIFIED":
                print("\n[DECISION] REFER - KYC verification failed")
                return UnderwritingResult(
                    decision=UnderwritingDecision.REFER,
                    policy_checks=policy_results,
                    risk_factors=["KYC Verification Failed"],
                    confidence=0.5,
                    reasoning="KYC verification incomplete",
                )

        # 3. Reasoning agent
        print("\n[Reasoning Agent]")
        agent_result = self.reasoning_agent.evaluate(profile)

        print(f"  Scenario: {agent_result['scenario']}")
        print(f"  Risk Factors: {agent_result['risk_factors']}")
        print(f"  Recommendation: {agent_result['recommendation']}")
        print(f"  Confidence: {agent_result['confidence']:.0%}")

        # 3. Final decision
        decision = UnderwritingDecision(agent_result["recommendation"])

        print(f"\n{'='*60}")
        print(f"[FINAL DECISION] {decision.value}")
        print(f"{'='*60}")

        return UnderwritingResult(
            decision=decision,
            policy_checks=policy_results,
            risk_factors=agent_result["risk_factors"],
            confidence=agent_result["confidence"],
            reasoning=agent_result["scenario"],
        )
