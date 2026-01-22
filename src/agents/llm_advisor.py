"""
LLM Advisory Layer.
LLM provides recommendations, NOT decisions.
Output: recommendation, evidence cited, confidence.
Never outputs: premium, accept/decline.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

from rich.console import Console
from rich.panel import Panel

from src.domain.risk_case import RiskCase
from src.infrastructure.llm_client import LLMClient

console = Console()


@dataclass
class LLMAdvisory:
    """LLM advisory output - non-binding."""

    # Recommendation (non-binding)
    recommendation: str = ""  # "Consider approval", "Suggest review", etc.

    # Evidence cited for recommendation
    evidence_cited: List[str] = field(default_factory=list)

    # Confidence in recommendation (0-1)
    confidence: float = 0.0

    # Conflicts/inconsistencies detected
    conflicts_detected: List[str] = field(default_factory=list)

    # Suggested actions for underwriter
    suggested_actions: List[str] = field(default_factory=list)

    # Medical narrative summary
    medical_summary: str = ""

    # Risk assessment narrative
    risk_narrative: str = ""

    # Source
    source: str = "LLM"  # LLM or FALLBACK

    # Raw response (for audit)
    raw_response: Optional[Dict[str, Any]] = None


class LLMAdvisor:
    """
    LLM Advisory Layer.

    Responsibilities:
    - Summarize medical records
    - Classify disease severity
    - Highlight conflicts/inconsistencies
    - Suggest underwriting actions

    Never:
    - Output premium
    - Make accept/decline decisions
    """

    SYSTEM_PROMPT = """You are a Medical Underwriting Advisor for Life Insurance in India.

Your role is to ADVISE, not DECIDE. You provide recommendations to human underwriters.

## YOUR RESPONSIBILITIES:
1. Summarize the medical profile in plain language
2. Identify risk factors and their severity
3. Detect any conflicts or inconsistencies in the data
4. Suggest what the underwriter should consider
5. Provide confidence in your assessment

## YOU MUST NEVER:
- Make accept/decline decisions
- Recommend specific premium amounts
- Recommend specific loading percentages
- Claim to have decision authority

## OUTPUT FORMAT (MANDATORY JSON):
{
    "medical_summary": "Brief plain-language summary of medical profile",
    "risk_factors_identified": [
        {"factor": "name", "severity": "low/moderate/high", "evidence": "what data shows this"}
    ],
    "conflicts_detected": ["Any inconsistencies in the data"],
    "suggested_actions": ["What the underwriter should consider"],
    "overall_assessment": "low_risk/moderate_risk/high_risk/requires_review",
    "confidence_score": 0.0 to 1.0,
    "recommendation_narrative": "Brief narrative recommendation for underwriter"
}

IMPORTANT: Output ONLY valid JSON. No other text."""

    def __init__(self):
        self.llm_client = None
        self._init_llm()

    def _init_llm(self):
        try:
            self.llm_client = LLMClient()
        except Exception as e:
            print(f"[WARN] LLM Client init failed: {e}")
            self.llm_client = None

    def advise(self, risk_case: RiskCase) -> LLMAdvisory:
        """
        Get LLM advisory on the risk case.
        Returns non-binding recommendations.
        """
        console.print()
        console.rule("[bold]LLM ADVISORY LAYER[/bold]")
        console.print("  Role: Advisory (non-binding)")

        prompt = self._build_prompt(risk_case)

        # Try LLM
        if self.llm_client:
            try:
                console.print("  Calling Azure OpenAI for advisory...")
                response = self.llm_client.generate_json(prompt, self.SYSTEM_PROMPT)
                console.print("  [green][OK][/green] Response received")

                return self._parse_response(response, risk_case)

            except Exception as e:
                console.print(f"  [yellow][WARN][/yellow] LLM call failed: {e}")
                console.print("  Falling back to rule-based advisory...")

        # Fallback
        return self._fallback_advisory(risk_case)

    def _build_prompt(self, risk_case: RiskCase) -> str:
        """Build prompt from RiskCase."""
        lines = ["## RISK CASE FOR ADVISORY REVIEW\n"]

        # Identity
        if risk_case.identity:
            lines.append("### IDENTITY")
            lines.append(
                f"- Name: {risk_case.identity.full_name.value if risk_case.identity.full_name else 'Unknown'}"
            )
            lines.append(f"- Age: {risk_case.identity.age or 'Unknown'} years")
            lines.append(f"- Gender: {risk_case.identity.gender or 'Unknown'}")
            lines.append("")

        # Proposal
        if risk_case.proposal:
            lines.append("### PROPOSAL")
            lines.append(f"- Sum Assured: ₹{risk_case.proposal.sum_assured:,.0f}")
            lines.append(f"- Product: {risk_case.proposal.product_name}")
            lines.append("")

        # Vitals
        lines.append("### VITALS")
        vitals = risk_case.medical.vitals
        if vitals.height_cm:
            lines.append(f"- Height: {vitals.height_cm.value} cm")
        if vitals.weight_kg:
            lines.append(f"- Weight: {vitals.weight_kg.value} kg")
        if vitals.bmi:
            lines.append(f"- BMI: {vitals.bmi.value} ({vitals.bmi_category})")
        if vitals.bp_readings:
            bp = vitals.bp_readings[-1]
            lines.append(f"- BP: {bp.systolic}/{bp.diastolic} mmHg")
        lines.append("")

        # Diabetes
        lines.append("### DIABETES PANEL")
        diabetes = risk_case.medical.diabetes
        lines.append(f"- Diabetic: {diabetes.is_diabetic.value}")
        if diabetes.duration_years:
            lines.append(f"- Duration: {diabetes.duration_years} years")
        if diabetes.hba1c:
            lines.append(f"- HbA1c: {diabetes.hba1c.value}%")
        if diabetes.fbs:
            lines.append(f"- FBS: {diabetes.fbs.value} mg/dL")
        if diabetes.treatment_type:
            lines.append(f"- Treatment: {diabetes.treatment_type}")
        if diabetes.has_complications:
            lines.append(f"- Complications: {diabetes.complications}")
        lines.append("")

        # Liver
        lines.append("### LIVER FUNCTION")
        liver = risk_case.medical.liver
        if liver.sgot:
            lines.append(f"- SGOT: {liver.sgot.value} U/L")
        if liver.sgpt:
            lines.append(f"- SGPT: {liver.sgpt.value} U/L")
        lines.append(f"- Status: {liver.status}")
        lines.append("")

        # Kidney
        lines.append("### KIDNEY FUNCTION")
        renal = risk_case.medical.renal
        if renal.creatinine:
            lines.append(f"- Creatinine: {renal.creatinine.value} mg/dL")
        if renal.urea:
            lines.append(f"- Urea: {renal.urea.value} mg/dL")
        lines.append(f"- Status: {renal.status}")
        lines.append("")

        # Lifestyle
        lines.append("### LIFESTYLE")
        lines.append(f"- Smoking: {risk_case.lifestyle.smoking.status}")
        if risk_case.lifestyle.smoking.pack_years:
            lines.append(f"  Pack-years: {risk_case.lifestyle.smoking.pack_years}")
        lines.append(f"- Alcohol: {risk_case.lifestyle.alcohol.status}")
        if risk_case.lifestyle.alcohol.units_per_week:
            lines.append(f"  Units/week: {risk_case.lifestyle.alcohol.units_per_week}")
        lines.append("")

        # Task
        lines.append("## TASK")
        lines.append("Provide your advisory assessment in the JSON format specified.")
        lines.append("Remember: You are ADVISING, not DECIDING.")

        return "\n".join(lines)

    def _parse_response(
        self, response: Dict[str, Any], risk_case: RiskCase
    ) -> LLMAdvisory:
        """Parse LLM response into advisory."""
        advisory = LLMAdvisory(
            source="LLM",
            raw_response=response,
        )

        # Medical summary
        advisory.medical_summary = response.get("medical_summary", "")

        # Risk factors as evidence cited
        risk_factors = response.get("risk_factors_identified", [])
        advisory.evidence_cited = [
            f"{rf.get('factor', 'Unknown')}: {rf.get('evidence', 'N/A')}"
            for rf in risk_factors
        ]

        # Conflicts
        advisory.conflicts_detected = response.get("conflicts_detected", [])

        # Suggested actions
        advisory.suggested_actions = response.get("suggested_actions", [])

        # Confidence
        advisory.confidence = response.get("confidence_score", 0.8)

        # Recommendation narrative
        advisory.recommendation = response.get("recommendation_narrative", "")
        advisory.risk_narrative = response.get("overall_assessment", "")

        # Log to audit
        risk_case.log_audit(
            action="LLM_ADVISORY_RECEIVED",
            actor="LLM",
            component="LLMAdvisor",
            new_value=advisory.risk_narrative,
            reason=advisory.recommendation,
        )

        # Print summary
        console.print(
            f"\n  Medical Summary: {advisory.medical_summary[:100]}..."
            if len(advisory.medical_summary) > 100
            else f"\n  Medical Summary: {advisory.medical_summary}"
        )
        console.print(f"  Risk Assessment: {advisory.risk_narrative}")
        console.print(f"  Confidence: {advisory.confidence:.0%}")
        if advisory.conflicts_detected:
            console.print(
                f"  [yellow][WARN][/yellow] Conflicts: {advisory.conflicts_detected}"
            )

        return advisory

    def _fallback_advisory(self, risk_case: RiskCase) -> LLMAdvisory:
        """Fallback rule-based advisory when LLM unavailable."""
        advisory = LLMAdvisory(
            source="FALLBACK",
        )

        risk_factors = []

        # Check BMI
        if risk_case.medical.vitals.bmi:
            bmi = risk_case.medical.vitals.bmi.value
            if bmi and bmi > 30:
                risk_factors.append(f"Elevated BMI ({bmi})")

        # Check diabetes
        if risk_case.medical.diabetes.hba1c:
            hba1c = risk_case.medical.diabetes.hba1c.value
            if hba1c and hba1c > 7:
                risk_factors.append(f"Suboptimal diabetes control (HbA1c {hba1c}%)")
            elif hba1c and hba1c > 6.5:
                risk_factors.append(f"Diabetic (HbA1c {hba1c}%)")

        # Check smoking
        if risk_case.lifestyle.smoking.status == "Current":
            risk_factors.append("Current smoker")

        advisory.evidence_cited = risk_factors
        advisory.confidence = 0.75

        if not risk_factors:
            advisory.recommendation = (
                "No significant risk factors identified. Standard terms may apply."
            )
            advisory.risk_narrative = "low_risk"
        elif len(risk_factors) <= 2:
            advisory.recommendation = (
                "Some risk factors present. Consider loading or review."
            )
            advisory.risk_narrative = "moderate_risk"
        else:
            advisory.recommendation = (
                "Multiple risk factors. Recommend underwriter review."
            )
            advisory.risk_narrative = "high_risk"

        advisory.medical_summary = f"Profile shows {len(risk_factors)} risk factor(s)."

        # Log
        risk_case.log_audit(
            action="LLM_ADVISORY_FALLBACK",
            actor="SYSTEM",
            component="LLMAdvisor",
            new_value=advisory.risk_narrative,
            reason="LLM unavailable, using rule-based fallback",
        )

        console.print(f"\n  [bold]Fallback Advisory[/bold]")
        console.print(f"  Risk Assessment: {advisory.risk_narrative}")
        console.print(f"  Recommendation: {advisory.recommendation}")

        return advisory
