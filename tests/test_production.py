"""
Test: Production Underwriting Pipeline.
Tests the correct flow: Requirements → Rating → LLM Advisory → Offer
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.underwriting.production_pipeline import (
    ProductionPipeline,
    create_risk_case_from_synthetic,
)


def run_test():
    print("\n" + "=" * 70)
    print("PRODUCTION UNDERWRITING PIPELINE TEST")
    print("=" * 70)
    print(
        """
    Correct Flow:
    1. Requirement Determination (What evidence needed?)
    2. Deterministic Rating (Actuarial tables, no LLM)
    3. LLM Advisory (Non-binding recommendations)
    4. Offer Construction (Final decision + premium)
    """
    )

    # Create synthetic data (simulating document extraction)
    synthetic_data = {
        # Identity
        "full_name": "Priya Sharma",
        "dob": "15/03/1988",
        "age": 36,
        "gender": "Female",
        "pan": "BCDPS7890K",
        "aadhaar": "987654321098",
        "address": "42, Green Valley, Bangalore",
        # Proposal
        "sum_assured": 15000000,  # 1.5 Cr
        # Vitals
        "height_cm": 162,
        "weight_kg": 58,
        "bmi": 22.1,
        "bp_systolic": 118,
        "bp_diastolic": 76,
        # Diabetes
        "diabetes_declared": "Prediabetic",
        "hba1c": 6.2,
        "fbs": 105,
        "diabetes_duration": 2,
        "diabetes_treatment": "Diet control",
        # Liver
        "sgot": 28,
        "sgpt": 32,
        "liver_status": "Normal",
        # Kidney
        "creatinine": 0.85,
        "urea": 26,
        "kidney_status": "Normal",
        # Lifestyle
        "smoking_status": "Never",
        "alcohol_status": "Social",
        "alcohol_units_per_week": 4,
        # Occupation
        "occupation": "Software Engineer",
        "occupation_class": 1,
        # Financial
        "annual_income": 2400000,
    }

    # Create RiskCase
    print("\n[Creating RiskCase from synthetic data...]")
    risk_case = create_risk_case_from_synthetic(synthetic_data)

    # Run pipeline
    pipeline = ProductionPipeline()
    offer = pipeline.process(risk_case)

    # =========================================================================
    # AUDIT TRAIL
    # =========================================================================
    print("\n" + "=" * 70)
    print("AUDIT TRAIL")
    print("=" * 70)
    print(risk_case.get_audit_summary())

    # =========================================================================
    # FINAL RESULT
    # =========================================================================
    print("\n" + "=" * 70)
    print("FINAL OFFER")
    print("=" * 70)

    box_width = 50

    print(
        f"""
    ┌{'─' * box_width}┐
    │{'UNDERWRITING DECISION'.center(box_width)}│
    ├{'─' * box_width}┤
    │{' ' * box_width}│
    │{f'Case: {offer.case_id}'.center(box_width)}│
    │{f'Decision: {offer.decision}'.center(box_width)}│
    │{f'Risk Class: {offer.risk_class}'.center(box_width)}│
    │{' ' * box_width}│"""
    )

    if offer.decision in ["APPROVE", "APPROVE_WITH_LOADING"]:
        print(
            f"""    │{f'Sum Assured: ₹{offer.sum_assured:,.0f}'.center(box_width)}│
    │{f'Base Premium: ₹{offer.base_premium_annual:,.0f}/yr'.center(box_width)}│
    │{f'Loading: {offer.total_loading_percent}%'.center(box_width)}│
    │{f'Final Premium: ₹{offer.loaded_premium_annual:,.0f}/yr'.center(box_width)}│
    │{' ' * box_width}│"""
        )

    print(
        f"""    │{'(LLM provided non-binding advisory)'.center(box_width)}│
    │{' ' * box_width}│
    └{'─' * box_width}┘
    """
    )


if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"\nTEST ERROR: {e}")
        import traceback

        traceback.print_exc()
