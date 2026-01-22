"""
Deterministic Rating Engine.
Uses actuarial tables and condition-specific rules.
NEVER calls LLM. Always explainable.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.domain.risk_case import RiskCase, PricingBasis, AuditEntry

console = Console()


class RiskClass(str, Enum):
    PREFERRED = "PREFERRED"
    STANDARD = "STANDARD"
    SUBSTANDARD_1 = "SUBSTANDARD_1"  # +25%
    SUBSTANDARD_2 = "SUBSTANDARD_2"  # +50%
    SUBSTANDARD_3 = "SUBSTANDARD_3"  # +75%
    SUBSTANDARD_4 = "SUBSTANDARD_4"  # +100%
    DECLINE = "DECLINE"


class DecisionType(str, Enum):
    APPROVE = "APPROVE"
    APPROVE_WITH_LOADING = "APPROVE_WITH_LOADING"
    APPROVE_WITH_EXCLUSION = "APPROVE_WITH_EXCLUSION"
    DECLINE = "DECLINE"
    REFER = "REFER"


@dataclass
class LoadingReason:
    """A single loading with reason."""

    category: str  # Medical, Lifestyle, Occupation
    condition: str  # e.g., "Diabetes", "Smoking"
    loading_percent: int
    reason: str
    evidence_ref: Optional[str] = None


@dataclass
class ExclusionReason:
    """A single exclusion with reason."""

    condition: str
    exclusion_text: str
    reason: str = ""
    duration: Optional[str] = None  # e.g., "Permanent", "5 years"


@dataclass
class RatingResult:
    """Complete rating result."""

    decision: DecisionType
    risk_class: RiskClass

    # Loadings
    loadings: List[LoadingReason] = field(default_factory=list)
    total_loading_percent: int = 0

    # Exclusions
    exclusions: List[ExclusionReason] = field(default_factory=list)

    # Waiting periods
    waiting_periods: List[Dict[str, Any]] = field(default_factory=list)

    # Decline reasons (if declined)
    decline_reasons: List[str] = field(default_factory=list)

    # Refer reasons (if referred)
    refer_reasons: List[str] = field(default_factory=list)

    # Explanation
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "risk_class": self.risk_class.value,
            "loadings": [
                {
                    "category": l.category,
                    "condition": l.condition,
                    "percent": l.loading_percent,
                    "reason": l.reason,
                }
                for l in self.loadings
            ],
            "total_loading_percent": self.total_loading_percent,
            "exclusions": [
                {
                    "condition": e.condition,
                    "text": e.exclusion_text,
                    "duration": e.duration,
                }
                for e in self.exclusions
            ],
            "decline_reasons": self.decline_reasons,
            "refer_reasons": self.refer_reasons,
        }


# ============================================================================
# RATING TABLES (Actuarial - no LLM)
# ============================================================================

# Base mortality rates per 1000 by age (simplified)
BASE_RATES_PER_1000 = {
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

# Condition-based loading tables
DIABETES_LOADING_TABLE = {
    # (HbA1c range, Duration) -> Loading %
    ("controlled", "short"): 25,  # HbA1c <7, duration <5 years
    ("controlled", "long"): 50,  # HbA1c <7, duration >5 years
    ("suboptimal", "short"): 75,  # HbA1c 7-8.5, short duration
    ("suboptimal", "long"): 100,  # HbA1c 7-8.5, long duration
    ("uncontrolled", "any"): "DECLINE",  # HbA1c >8.5
}

BMI_LOADING_TABLE = {
    # BMI range -> Loading %
    (0, 18.5): 25,  # Underweight
    (18.5, 25): 0,  # Normal
    (25, 30): 25,  # Overweight
    (30, 35): 50,  # Obese Class 1
    (35, 40): 100,  # Obese Class 2
    (40, 100): "DECLINE",  # Morbid obesity
}

SMOKING_LOADING_TABLE = {
    "Never": 0,
    "Former_5plus": 0,  # Quit > 5 years ago
    "Former_2to5": 25,  # Quit 2-5 years ago
    "Former_1to2": 50,  # Quit 1-2 years ago
    "Current_Light": 75,  # <10/day
    "Current_Moderate": 100,  # 10-20/day
    "Current_Heavy": "DECLINE",  # >20/day
}

ALCOHOL_LOADING_TABLE = {
    "Never": 0,
    "Social": 0,  # <7 units/week
    "Regular": 25,  # 7-14 units/week
    "Heavy": "DECLINE",  # >21 units/week
}

BP_LOADING_TABLE = {
    # (Systolic range, Diastolic range) -> Loading %
    "Normal": 0,  # <120/80
    "Elevated": 0,  # 120-129/<80
    "Stage1_Controlled": 25,  # 130-139/80-89 on meds
    "Stage2_Controlled": 50,  # 140+/90+ controlled
    "Uncontrolled": "REFER",  # Uncontrolled
}


class DeterministicRatingEngine:
    """
    Deterministic rating using actuarial tables.
    - Never calls LLM
    - Always produces explainable deltas
    - Uses condition-specific rules
    """

    def rate(self, risk_case: RiskCase) -> RatingResult:
        """
        Rate the risk case and produce loadings/exclusions/decision.
        """
        console.print()
        console.rule("[bold]DETERMINISTIC RATING ENGINE[/bold]")

        result = RatingResult(
            decision=DecisionType.APPROVE,
            risk_class=RiskClass.STANDARD,
        )

        # 1. Check for auto-decline conditions
        console.print("\n  [bold]Auto-Decline Checks[/bold]")
        decline_reasons = self._check_auto_decline(risk_case)
        if decline_reasons:
            result.decision = DecisionType.DECLINE
            result.risk_class = RiskClass.DECLINE
            result.decline_reasons = decline_reasons
            for reason in decline_reasons:
                console.print(f"    [red][DECLINE][/red] {reason}")
            result.reasoning = f"Declined: {'; '.join(decline_reasons)}"
            self._log_rating(risk_case, result)
            return result
        console.print("    [green][PASS][/green] No auto-decline conditions")

        # 2. Calculate medical loadings
        console.print("\n  [bold]Medical Loadings[/bold]")
        medical_loadings = self._calculate_medical_loadings(risk_case)
        result.loadings.extend(medical_loadings)
        for loading in medical_loadings:
            console.print(
                f"    [yellow]+[/yellow] {loading.condition}: +{loading.loading_percent}%"
            )

        # 3. Calculate lifestyle loadings
        console.print("\n  [bold]Lifestyle Loadings[/bold]")
        lifestyle_loadings = self._calculate_lifestyle_loadings(risk_case)
        result.loadings.extend(lifestyle_loadings)
        for loading in lifestyle_loadings:
            console.print(
                f"    [yellow]+[/yellow] {loading.condition}: +{loading.loading_percent}%"
            )

        # 4. Calculate occupation loadings
        console.print("\n  [bold]Occupation Loadings[/bold]")
        occ_loadings = self._calculate_occupation_loadings(risk_case)
        result.loadings.extend(occ_loadings)
        for loading in occ_loadings:
            console.print(
                f"    [yellow]+[/yellow] {loading.condition}: +{loading.loading_percent}%"
            )

        # 5. Calculate total loading
        result.total_loading_percent = sum(l.loading_percent for l in result.loadings)
        console.print(
            f"\n  [bold]Total Loading:[/bold] {result.total_loading_percent}%"
        )

        # 6. Determine risk class
        result.risk_class = self._determine_risk_class(result.total_loading_percent)
        console.print(f"  [bold]Risk Class:[/bold] {result.risk_class.value}")

        # 7. Check for exclusions
        console.print("\n  [bold]Exclusions[/bold]")
        exclusions = self._determine_exclusions(risk_case)
        result.exclusions = exclusions
        if exclusions:
            for exc in exclusions:
                console.print(
                    f"    [yellow][EXCL][/yellow] {exc.condition}: {exc.exclusion_text}"
                )
        else:
            console.print("    None")

        # 8. Check for refer conditions
        refer_reasons = self._check_refer_conditions(
            risk_case, result.total_loading_percent
        )
        if refer_reasons:
            result.decision = DecisionType.REFER
            result.refer_reasons = refer_reasons
            console.print(f"\n  [bold yellow]Referred for Manual Review[/bold yellow]")
            for reason in refer_reasons:
                console.print(f"    [cyan][REFER][/cyan] {reason}")
        elif result.loadings or exclusions:
            result.decision = (
                DecisionType.APPROVE_WITH_LOADING
                if result.loadings
                else DecisionType.APPROVE_WITH_EXCLUSION
            )

        # 9. Build reasoning
        result.reasoning = self._build_reasoning(result)

        # Log to audit
        self._log_rating(risk_case, result)

        console.print(f"\n  [bold]DECISION:[/bold] {result.decision.value}")

        return result

    def _check_auto_decline(self, risk_case: RiskCase) -> List[str]:
        """Check for conditions that result in automatic decline."""
        reasons = []

        # Age limits
        if risk_case.identity and risk_case.identity.age:
            age = risk_case.identity.age
            if age < 18:
                reasons.append(f"Age {age} below minimum (18)")
            if age > 65:
                reasons.append(f"Age {age} above maximum (65)")

        # BMI limits
        if risk_case.medical.vitals.bmi:
            bmi = risk_case.medical.vitals.bmi.value
            if bmi and bmi > 40:
                reasons.append(f"BMI {bmi} indicates morbid obesity")

        # Uncontrolled diabetes
        if risk_case.medical.diabetes.hba1c:
            hba1c = risk_case.medical.diabetes.hba1c.value
            if hba1c and hba1c > 10:
                reasons.append(f"HbA1c {hba1c}% indicates severe uncontrolled diabetes")

        # Heavy alcohol
        if risk_case.lifestyle.alcohol.status == "Heavy":
            reasons.append("Heavy alcohol consumption")

        # Heavy smoking
        if (
            risk_case.lifestyle.smoking.status == "Current"
            and risk_case.lifestyle.smoking.pack_years
        ):
            if risk_case.lifestyle.smoking.pack_years > 30:
                reasons.append("Heavy smoking history (>30 pack-years)")

        return reasons

    def _calculate_medical_loadings(self, risk_case: RiskCase) -> List[LoadingReason]:
        """Calculate medical loadings from evidence."""
        loadings = []

        # BMI loading
        if risk_case.medical.vitals.bmi:
            bmi = risk_case.medical.vitals.bmi.value
            if bmi:
                for (min_bmi, max_bmi), loading in BMI_LOADING_TABLE.items():
                    if (
                        min_bmi <= bmi < max_bmi
                        and loading != "DECLINE"
                        and loading > 0
                    ):
                        loadings.append(
                            LoadingReason(
                                category="Medical",
                                condition=f"BMI_{risk_case.medical.vitals.bmi_category}",
                                loading_percent=loading,
                                reason=f"BMI {bmi:.1f} in category {risk_case.medical.vitals.bmi_category}",
                            )
                        )
                        break

        # Diabetes loading
        if risk_case.medical.diabetes.hba1c:
            hba1c = risk_case.medical.diabetes.hba1c.value
            if hba1c:
                duration = risk_case.medical.diabetes.duration_years or 0

                if hba1c <= 7:
                    control = "controlled"
                elif hba1c <= 8.5:
                    control = "suboptimal"
                else:
                    control = "uncontrolled"

                dur_key = "short" if duration < 5 else "long"

                key = (
                    (control, dur_key)
                    if control != "uncontrolled"
                    else ("uncontrolled", "any")
                )
                loading = DIABETES_LOADING_TABLE.get(key)

                if loading and loading != "DECLINE":
                    loadings.append(
                        LoadingReason(
                            category="Medical",
                            condition="Diabetes",
                            loading_percent=loading,
                            reason=f"HbA1c {hba1c}%, {control} control, {duration:.0f} years duration",
                        )
                    )

        # BP loading
        bp_readings = risk_case.medical.vitals.bp_readings
        if bp_readings:
            latest = bp_readings[-1]
            if latest.systolic >= 140 or latest.diastolic >= 90:
                loadings.append(
                    LoadingReason(
                        category="Medical",
                        condition="Hypertension",
                        loading_percent=50,
                        reason=f"BP {latest.systolic}/{latest.diastolic} indicates hypertension",
                    )
                )
            elif latest.systolic >= 130 or latest.diastolic >= 80:
                loadings.append(
                    LoadingReason(
                        category="Medical",
                        condition="Elevated_BP",
                        loading_percent=25,
                        reason=f"BP {latest.systolic}/{latest.diastolic} is elevated",
                    )
                )

        return loadings

    def _calculate_lifestyle_loadings(self, risk_case: RiskCase) -> List[LoadingReason]:
        """Calculate lifestyle loadings."""
        loadings = []

        # Smoking
        smoking = risk_case.lifestyle.smoking
        if smoking.status == "Current":
            loading = 75 if smoking.pack_years and smoking.pack_years < 10 else 100
            loadings.append(
                LoadingReason(
                    category="Lifestyle",
                    condition="Smoking",
                    loading_percent=loading,
                    reason=f"Current smoker, {smoking.pack_years or 'unknown'} pack-years",
                )
            )
        elif smoking.status == "Former":
            if smoking.years_since_quit and smoking.years_since_quit < 2:
                loadings.append(
                    LoadingReason(
                        category="Lifestyle",
                        condition="Recent_Ex_Smoker",
                        loading_percent=50,
                        reason=f"Quit {smoking.years_since_quit:.1f} years ago",
                    )
                )
            elif smoking.years_since_quit and smoking.years_since_quit < 5:
                loadings.append(
                    LoadingReason(
                        category="Lifestyle",
                        condition="Ex_Smoker",
                        loading_percent=25,
                        reason=f"Quit {smoking.years_since_quit:.1f} years ago",
                    )
                )

        # Alcohol
        alcohol = risk_case.lifestyle.alcohol
        if alcohol.status == "Regular":
            loadings.append(
                LoadingReason(
                    category="Lifestyle",
                    condition="Regular_Alcohol",
                    loading_percent=25,
                    reason=f"Regular alcohol consumption, {alcohol.units_per_week or 'unknown'} units/week",
                )
            )

        return loadings

    def _calculate_occupation_loadings(
        self, risk_case: RiskCase
    ) -> List[LoadingReason]:
        """Calculate occupation loadings."""
        loadings = []

        occ = risk_case.lifestyle.occupation
        if occ.occupation_class >= 3:
            loading = 25 if occ.occupation_class == 3 else 50
            loadings.append(
                LoadingReason(
                    category="Occupation",
                    condition=f"Occupation_Class_{occ.occupation_class}",
                    loading_percent=loading,
                    reason=f"Occupation: {occ.occupation}, Class {occ.occupation_class}",
                )
            )

        return loadings

    def _determine_risk_class(self, total_loading: int) -> RiskClass:
        """Determine risk class from total loading."""
        if total_loading == 0:
            return RiskClass.PREFERRED
        elif total_loading <= 25:
            return RiskClass.STANDARD
        elif total_loading <= 50:
            return RiskClass.SUBSTANDARD_1
        elif total_loading <= 75:
            return RiskClass.SUBSTANDARD_2
        elif total_loading <= 100:
            return RiskClass.SUBSTANDARD_3
        else:
            return RiskClass.SUBSTANDARD_4

    def _determine_exclusions(self, risk_case: RiskCase) -> List[ExclusionReason]:
        """Determine exclusions based on pre-existing conditions."""
        exclusions = []

        # Diabetes exclusion for complications
        if risk_case.medical.diabetes.has_complications:
            exclusions.append(
                ExclusionReason(
                    condition="Diabetes_Complications",
                    exclusion_text="Claims related to diabetic complications excluded",
                    duration="Permanent",
                    reason="Pre-existing diabetic complications disclosed",
                )
            )

        return exclusions

    def _check_refer_conditions(
        self, risk_case: RiskCase, total_loading: int
    ) -> List[str]:
        """Check for conditions requiring manual review."""
        reasons = []

        # High loading
        if total_loading > 100:
            reasons.append(
                f"Total loading {total_loading}% exceeds auto-approve threshold"
            )

        # Complex medical
        if risk_case.medical.diabetes.has_complications:
            reasons.append("Diabetic complications require underwriter review")

        # Cardiac issues
        if risk_case.medical.cardiac.ecg_abnormal:
            reasons.append("Abnormal ECG requires underwriter review")

        return reasons

    def _build_reasoning(self, result: RatingResult) -> str:
        """Build human-readable reasoning."""
        parts = []

        if result.decision == DecisionType.APPROVE:
            parts.append("Standard risk, no significant loadings.")
        elif result.decision == DecisionType.APPROVE_WITH_LOADING:
            parts.append(f"Approved with {result.total_loading_percent}% loading.")
            parts.append(
                "Loadings for: " + ", ".join(l.condition for l in result.loadings)
            )
        elif result.decision == DecisionType.DECLINE:
            parts.append("Declined due to: " + ", ".join(result.decline_reasons))
        elif result.decision == DecisionType.REFER:
            parts.append(
                "Referred for manual review: " + ", ".join(result.refer_reasons)
            )

        return " ".join(parts)

    def _log_rating(self, risk_case: RiskCase, result: RatingResult):
        """Log rating to audit trail."""
        risk_case.log_audit(
            action="RATING_COMPLETED",
            actor="SYSTEM",
            component="DeterministicRatingEngine",
            new_value=f"{result.decision.value}|{result.risk_class.value}|{result.total_loading_percent}%",
            reason=result.reasoning,
        )
