"""
RiskCase: Core stateful object for production underwriting.
Replaces patient_profile.txt with auditable, replayable state.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid
import json

from src.domain.evidence import (
    IdentityEvidence,
    MedicalEvidence,
    LifestyleEvidence,
    FinancialEvidence,
    EvidenceValue,
)


class CaseStatus(str, Enum):
    """Underwriting case status."""

    DRAFT = "DRAFT"
    PENDING_REQUIREMENTS = "PENDING_REQUIREMENTS"
    UNDER_REVIEW = "UNDER_REVIEW"
    PENDING_MEDICAL = "PENDING_MEDICAL"
    STP_ELIGIBLE = "STP_ELIGIBLE"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    DECISION_READY = "DECISION_READY"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"
    REFERRED = "REFERRED"
    WITHDRAWN = "WITHDRAWN"


class RequirementStatus(str, Enum):
    """Status of a requirement."""

    PENDING = "PENDING"
    RECEIVED = "RECEIVED"
    VERIFIED = "VERIFIED"
    WAIVED = "WAIVED"
    NOT_REQUIRED = "NOT_REQUIRED"


@dataclass
class Requirement:
    """A requirement for underwriting."""

    requirement_id: str
    category: str  # Medical, Financial, KYC, Third_Party
    requirement_type: str  # e.g., "HbA1c", "ITR", "CIBIL"
    description: str
    status: RequirementStatus = RequirementStatus.PENDING
    mandatory: bool = True
    triggered_by: Optional[str] = None  # What triggered this requirement
    received_date: Optional[datetime] = None
    document_id: Optional[str] = None


@dataclass
class ProposalContext:
    """Proposal details."""

    proposal_id: str
    proposal_date: datetime

    # Product
    product_code: str = "TERM_LIFE"
    product_name: str = "Term Life Insurance"

    # Sum Assured
    sum_assured: float = 0
    policy_term: int = 20  # years
    premium_term: int = 20

    # Channel
    channel: str = "Direct"  # Direct, Agent, Banca, Digital


@dataclass
class DerivedMetrics:
    """Calculated metrics from evidence."""

    # Body metrics
    bmi: Optional[float] = None
    bmi_category: str = "Unknown"

    # Disease control scores (0-100, higher = better controlled)
    diabetes_control_score: Optional[float] = None
    bp_control_score: Optional[float] = None

    # Trend indicators
    bmi_trend: str = "Stable"  # Improving, Stable, Worsening
    hba1c_trend: str = "Stable"
    bp_trend: str = "Stable"

    # Risk flags
    risk_flags: List[str] = field(default_factory=list)

    # Aggregate risk
    medical_risk_class: str = "Standard"  # Preferred, Standard, Substandard
    lifestyle_risk_class: str = "Standard"
    financial_risk_class: str = "Standard"


@dataclass
class UnderwritingState:
    """Current state of underwriting process."""

    status: CaseStatus = CaseStatus.DRAFT

    # Eligibility
    stp_eligible: bool = False
    stp_ineligibility_reasons: List[str] = field(default_factory=list)

    # Manual review
    manual_review_required: bool = False
    manual_review_reasons: List[str] = field(default_factory=list)

    # Pending items
    pending_requirements: List[Requirement] = field(default_factory=list)

    # Review
    assigned_underwriter: Optional[str] = None
    review_date: Optional[datetime] = None


@dataclass
class PricingBasis:
    """Basis for pricing calculation."""

    # Base
    base_rate_per_1000: float = 0
    base_premium_annual: float = 0

    # Loadings (multiple can apply)
    loadings: List[Dict[str, Any]] = field(default_factory=list)
    total_loading_percent: float = 0

    # Exclusions
    exclusions: List[str] = field(default_factory=list)

    # Waiting periods
    waiting_periods: List[Dict[str, Any]] = field(default_factory=list)

    # Final
    loaded_premium_annual: float = 0
    risk_class: str = "Standard"


@dataclass
class AuditEntry:
    """Audit trail entry - every mutation logged."""

    entry_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = field(default_factory=datetime.utcnow)
    action: str = ""  # What was done
    actor: str = "SYSTEM"  # Who did it (SYSTEM, LLM, HUMAN)
    component: str = ""  # Which component

    # State change
    field_changed: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None

    # Evidence
    evidence_refs: List[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "action": self.action,
            "actor": self.actor,
            "component": self.component,
            "field_changed": self.field_changed,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "evidence_refs": self.evidence_refs,
            "reason": self.reason,
        }


@dataclass
class RiskCase:
    """
    Core stateful object for underwriting.
    Replaces patient_profile.txt.
    Auditable, replayable, evidence-backed.
    """

    # Identity
    case_id: str = field(default_factory=lambda: f"CASE-{uuid.uuid4().hex[:8].upper()}")
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Core evidence collections
    identity: Optional[IdentityEvidence] = None
    proposal: Optional[ProposalContext] = None
    medical: MedicalEvidence = field(default_factory=MedicalEvidence)
    lifestyle: LifestyleEvidence = field(default_factory=LifestyleEvidence)
    financial: FinancialEvidence = field(default_factory=FinancialEvidence)

    # Derived & computed
    derived_metrics: DerivedMetrics = field(default_factory=DerivedMetrics)

    # Underwriting state
    underwriting_state: UnderwritingState = field(default_factory=UnderwritingState)

    # Pricing (computed by rating engine)
    pricing_basis: Optional[PricingBasis] = None

    # Full audit trail
    audit_trail: List[AuditEntry] = field(default_factory=list)

    def log_audit(
        self,
        action: str,
        actor: str,
        component: str,
        field_changed: str = None,
        old_value: str = None,
        new_value: str = None,
        reason: str = "",
        evidence_refs: List[str] = None,
    ):
        """Log an audit entry."""
        entry = AuditEntry(
            action=action,
            actor=actor,
            component=component,
            field_changed=field_changed,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            evidence_refs=evidence_refs or [],
        )
        self.audit_trail.append(entry)
        self.updated_at = datetime.utcnow()
        return entry

    def add_requirement(self, req: Requirement):
        """Add a pending requirement."""
        self.underwriting_state.pending_requirements.append(req)
        self.log_audit(
            action="REQUIREMENT_ADDED",
            actor="SYSTEM",
            component="RequirementEngine",
            field_changed="pending_requirements",
            new_value=req.requirement_type,
            reason=req.triggered_by or "Standard requirement",
        )

    def satisfy_requirement(self, requirement_id: str, document_id: str):
        """Mark a requirement as satisfied."""
        for req in self.underwriting_state.pending_requirements:
            if req.requirement_id == requirement_id:
                old_status = req.status.value
                req.status = RequirementStatus.RECEIVED
                req.received_date = datetime.utcnow()
                req.document_id = document_id
                self.log_audit(
                    action="REQUIREMENT_SATISFIED",
                    actor="SYSTEM",
                    component="EvidenceCollection",
                    field_changed=f"requirement.{requirement_id}.status",
                    old_value=old_status,
                    new_value="RECEIVED",
                    evidence_refs=[document_id],
                )
                break

    def get_pending_requirements(self) -> List[Requirement]:
        """Get all pending requirements."""
        return [
            r
            for r in self.underwriting_state.pending_requirements
            if r.status == RequirementStatus.PENDING
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for storage/audit."""
        return {
            "case_id": self.case_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.underwriting_state.status.value,
            "sum_assured": self.proposal.sum_assured if self.proposal else 0,
            "audit_trail_count": len(self.audit_trail),
        }

    def get_audit_summary(self) -> str:
        """Get human-readable audit summary."""
        lines = [f"Audit Trail for {self.case_id}:"]
        lines.append("=" * 50)
        for entry in self.audit_trail:
            lines.append(
                f"[{entry.timestamp.strftime('%H:%M:%S')}] {entry.actor}: {entry.action}"
            )
            if entry.field_changed:
                lines.append(f"   Field: {entry.field_changed}")
            if entry.reason:
                lines.append(f"   Reason: {entry.reason}")
        return "\n".join(lines)
