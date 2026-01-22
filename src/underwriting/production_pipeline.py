"""
Production Underwriting Pipeline.
Correct flow:
1. Evidence Normalization
2. Requirement Determination
3. Risk State Builder
4. Deterministic Rating Engine
5. LLM Advisory Layer (non-binding)
6. Offer Constructor
7. Decision + Premium
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.domain.risk_case import (
    RiskCase,
    IdentityEvidence,
    ProposalContext,
    CaseStatus,
    PricingBasis,
)
from src.domain.evidence import (
    EvidenceValue,
    EvidenceMetadata,
    EvidenceSource,
    MedicalEvidence,
    LifestyleEvidence,
    FinancialEvidence,
    VitalsEvidence,
    DiabetesEvidence,
    LiverPanel,
    RenalPanel,
    SmokingEvidence,
    AlcoholEvidence,
    OccupationEvidence,
    IncomeEvidence,
    BPReading,
)
from src.underwriting.requirement_engine import RequirementEngine
from src.underwriting.rating_engine import DeterministicRatingEngine, DecisionType
from src.agents.llm_advisor import LLMAdvisor

console = Console()


@dataclass
class UnderwritingOffer:
    """Final underwriting offer."""

    case_id: str
    decision: str  # APPROVE, DECLINE, REFER

    # Pricing (only if approved)
    sum_assured: float = 0
    base_premium_annual: float = 0
    loadings: List[Dict[str, Any]] = field(default_factory=list)
    total_loading_percent: int = 0
    loaded_premium_annual: float = 0

    # Terms
    exclusions: List[str] = field(default_factory=list)
    waiting_periods: List[Dict[str, Any]] = field(default_factory=list)

    # Risk class
    risk_class: str = "Standard"

    # Reasoning
    reasoning: str = ""

    # Advisory (non-binding)
    llm_advisory_summary: str = ""

    # Audit
    audit_trail_count: int = 0


# Base rates per 1000 SA by age
BASE_RATES = {
    (18, 25): 1.20,
    (26, 30): 1.50,
    (31, 35): 1.90,
    (36, 40): 2.50,
    (41, 45): 3.30,
    (46, 50): 4.50,
    (51, 55): 6.20,
    (56, 60): 8.50,
    (61, 65): 11.80,
}


class ProductionPipeline:
    """
    Production-grade underwriting pipeline.

    Flow:
    1. Build RiskCase from evidence
    2. Determine requirements
    3. Rate deterministically
    4. Get LLM advisory (non-binding)
    5. Construct offer
    """

    def __init__(self):
        self.requirement_engine = RequirementEngine()
        self.rating_engine = DeterministicRatingEngine()
        self.llm_advisor = LLMAdvisor()

    def process(self, risk_case: RiskCase) -> UnderwritingOffer:
        """Process a RiskCase through the full pipeline."""

        console.print()
        console.rule(
            "[bold cyan]PRODUCTION UNDERWRITING PIPELINE[/bold cyan]", style="cyan"
        )
        console.print(f"  [bold]Case ID:[/bold] {risk_case.case_id}")
        console.print(
            f"  [bold]Applicant:[/bold] {risk_case.identity.full_name.value if risk_case.identity else 'Unknown'}"
        )
        if risk_case.proposal:
            console.print(
                f"  [bold]Sum Assured:[/bold] Rs.{risk_case.proposal.sum_assured:,.0f}"
            )

        # Log start
        risk_case.log_audit(
            action="PIPELINE_STARTED",
            actor="SYSTEM",
            component="ProductionPipeline",
        )

        # Step 1: Determine Requirements
        console.print()
        console.rule("STEP 1: REQUIREMENT DETERMINATION")
        requirements = self.requirement_engine.determine(risk_case)

        # For demo, assume all requirements satisfied
        risk_case.underwriting_state.status = CaseStatus.UNDER_REVIEW

        # Step 2: Deterministic Rating
        console.print()
        console.rule("STEP 2: DETERMINISTIC RATING")
        rating_result = self.rating_engine.rate(risk_case)

        # Step 3: LLM Advisory (non-binding)
        console.print()
        console.rule("STEP 3: LLM ADVISORY (Non-Binding)")
        advisory = self.llm_advisor.advise(risk_case)

        # Step 4: Construct Offer
        console.print()
        console.rule("STEP 4: OFFER CONSTRUCTION")
        offer = self._construct_offer(risk_case, rating_result, advisory)

        # Update case status
        if (
            rating_result.decision == DecisionType.APPROVE
            or rating_result.decision == DecisionType.APPROVE_WITH_LOADING
        ):
            risk_case.underwriting_state.status = CaseStatus.APPROVED
        elif rating_result.decision == DecisionType.DECLINE:
            risk_case.underwriting_state.status = CaseStatus.DECLINED
        else:
            risk_case.underwriting_state.status = CaseStatus.REFERRED

        # Log completion
        risk_case.log_audit(
            action="PIPELINE_COMPLETED",
            actor="SYSTEM",
            component="ProductionPipeline",
            new_value=offer.decision,
            reason=offer.reasoning,
        )

        # Final summary
        console.print()
        decision_style = (
            "green"
            if offer.decision in ["APPROVE", "APPROVE_WITH_LOADING"]
            else "red" if offer.decision == "DECLINE" else "yellow"
        )
        console.rule(
            f"[bold {decision_style}]DECISION: {offer.decision}[/bold {decision_style}]",
            style=decision_style,
        )

        if offer.decision in ["APPROVE", "APPROVE_WITH_LOADING"]:
            # Create pricing table
            pricing_table = Table(show_header=False, box=None, padding=(0, 2))
            pricing_table.add_column("Label", style="bold")
            pricing_table.add_column("Value")
            pricing_table.add_row("Sum Assured", f"Rs.{offer.sum_assured:,.0f}")
            pricing_table.add_row(
                "Base Premium", f"Rs.{offer.base_premium_annual:,.0f}/year"
            )
            if offer.loadings:
                for l in offer.loadings:
                    pricing_table.add_row(f"  + {l['condition']}", f"+{l['percent']}%")
            pricing_table.add_row("Total Loading", f"{offer.total_loading_percent}%")
            pricing_table.add_row(
                "Loaded Premium", f"Rs.{offer.loaded_premium_annual:,.0f}/year"
            )
            pricing_table.add_row("Risk Class", offer.risk_class)
            if offer.exclusions:
                pricing_table.add_row("Exclusions", ", ".join(offer.exclusions))
            console.print(pricing_table)

        console.print(f"\n  [bold]Reasoning:[/bold] {offer.reasoning}")
        console.print(f"  [bold]LLM Advisory:[/bold] {offer.llm_advisory_summary}")
        console.print(f"  [bold]Audit Trail:[/bold] {offer.audit_trail_count} entries")

        return offer

    def _construct_offer(
        self, risk_case: RiskCase, rating_result, advisory
    ) -> UnderwritingOffer:
        """Construct the final offer."""

        offer = UnderwritingOffer(
            case_id=risk_case.case_id,
            decision=rating_result.decision.value,
            risk_class=rating_result.risk_class.value,
            reasoning=rating_result.reasoning,
            llm_advisory_summary=advisory.recommendation,
            audit_trail_count=len(risk_case.audit_trail),
        )

        # If approved, calculate pricing
        if rating_result.decision in [
            DecisionType.APPROVE,
            DecisionType.APPROVE_WITH_LOADING,
            DecisionType.APPROVE_WITH_EXCLUSION,
        ]:
            sa = risk_case.proposal.sum_assured if risk_case.proposal else 0
            age = risk_case.identity.age if risk_case.identity else 35

            # Get base rate
            base_rate = 2.50  # default
            for (min_age, max_age), rate in BASE_RATES.items():
                if min_age <= age <= max_age:
                    base_rate = rate
                    break

            # Calculate
            offer.sum_assured = sa
            offer.base_premium_annual = (sa / 1000) * base_rate

            offer.loadings = [
                {
                    "condition": l.condition,
                    "percent": l.loading_percent,
                    "reason": l.reason,
                }
                for l in rating_result.loadings
            ]
            offer.total_loading_percent = rating_result.total_loading_percent

            loading_amount = offer.base_premium_annual * (
                rating_result.total_loading_percent / 100
            )
            offer.loaded_premium_annual = offer.base_premium_annual + loading_amount

            offer.exclusions = [e.exclusion_text for e in rating_result.exclusions]

            # Store in risk case
            risk_case.pricing_basis = PricingBasis(
                base_rate_per_1000=base_rate,
                base_premium_annual=offer.base_premium_annual,
                total_loading_percent=offer.total_loading_percent,
                loaded_premium_annual=offer.loaded_premium_annual,
                exclusions=offer.exclusions,
                risk_class=offer.risk_class,
            )

        return offer


def create_risk_case_from_synthetic(data: Dict[str, Any]) -> RiskCase:
    """Create a RiskCase from synthetic data (since we can't extract real docs)."""

    case = RiskCase()

    # Identity
    case.identity = IdentityEvidence(
        full_name=EvidenceValue(
            value=data.get("full_name", "Unknown"),
            metadata=EvidenceMetadata(
                source_type=EvidenceSource.PROPOSAL_FORM,
                source_document_id="synthetic",
                extraction_date=datetime.utcnow(),
            ),
        ),
        date_of_birth=EvidenceValue(value=data.get("dob")) if data.get("dob") else None,
        age=data.get("age"),
        gender=data.get("gender"),
        pan=EvidenceValue(value=data.get("pan")) if data.get("pan") else None,
        aadhaar=(
            EvidenceValue(value=data.get("aadhaar")) if data.get("aadhaar") else None
        ),
        address=data.get("address"),
    )

    # Proposal
    case.proposal = ProposalContext(
        proposal_id=f"PROP-{uuid.uuid4().hex[:8].upper()}",
        proposal_date=datetime.utcnow(),
        sum_assured=data.get("sum_assured", 1000000),
    )

    # Medical - Vitals
    case.medical.vitals = VitalsEvidence(
        height_cm=(
            EvidenceValue(value=data.get("height_cm"))
            if data.get("height_cm")
            else None
        ),
        weight_kg=(
            EvidenceValue(value=data.get("weight_kg"))
            if data.get("weight_kg")
            else None
        ),
        bmi=EvidenceValue(value=data.get("bmi")) if data.get("bmi") else None,
        bmi_category=_categorize_bmi(data.get("bmi")),
    )

    if data.get("bp_systolic") and data.get("bp_diastolic"):
        case.medical.vitals.bp_readings = [
            BPReading(
                systolic=data["bp_systolic"],
                diastolic=data["bp_diastolic"],
                reading_date=datetime.utcnow(),
            )
        ]

    # Medical - Diabetes
    case.medical.diabetes = DiabetesEvidence(
        is_diabetic=EvidenceValue(value=data.get("diabetes_declared", "No")),
        hba1c=EvidenceValue(value=data.get("hba1c")) if data.get("hba1c") else None,
        fbs=EvidenceValue(value=data.get("fbs")) if data.get("fbs") else None,
        duration_years=data.get("diabetes_duration"),
        treatment_type=data.get("diabetes_treatment"),
    )

    # Medical - Liver
    case.medical.liver = LiverPanel(
        sgot=EvidenceValue(value=data.get("sgot")) if data.get("sgot") else None,
        sgpt=EvidenceValue(value=data.get("sgpt")) if data.get("sgpt") else None,
        status=data.get("liver_status", "Normal"),
    )

    # Medical - Kidney
    case.medical.renal = RenalPanel(
        creatinine=(
            EvidenceValue(value=data.get("creatinine"))
            if data.get("creatinine")
            else None
        ),
        urea=EvidenceValue(value=data.get("urea")) if data.get("urea") else None,
        status=data.get("kidney_status", "Normal"),
    )

    # Lifestyle
    case.lifestyle.smoking = SmokingEvidence(
        status=data.get("smoking_status", "Never"),
        pack_years=data.get("pack_years"),
    )

    case.lifestyle.alcohol = AlcoholEvidence(
        status=data.get("alcohol_status", "Never"),
        units_per_week=data.get("alcohol_units_per_week"),
    )

    case.lifestyle.occupation = OccupationEvidence(
        occupation=data.get("occupation", "Office Worker"),
        occupation_class=data.get("occupation_class", 1),
    )

    # Financial
    case.financial.income = IncomeEvidence(
        declared_annual=(
            EvidenceValue(value=data.get("annual_income"))
            if data.get("annual_income")
            else None
        ),
    )
    case.financial.sum_assured_requested = data.get("sum_assured", 0)

    # Log creation
    case.log_audit(
        action="RISK_CASE_CREATED",
        actor="SYSTEM",
        component="SyntheticDataLoader",
        reason="Created from synthetic data",
    )

    return case


def _categorize_bmi(bmi: Optional[float]) -> str:
    if not bmi:
        return "Unknown"
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal"
    if bmi < 30:
        return "Overweight"
    if bmi < 35:
        return "Obese"
    return "Morbidly Obese"
