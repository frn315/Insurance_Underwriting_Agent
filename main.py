#!/usr/bin/env python3
"""
Insurance Underwriting Agent - Textual TUI
A professional interface for the underwriting system.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import (
    Header,
    Footer,
    Button,
    Static,
    ListView,
    ListItem,
    Label,
    LoadingIndicator,
)
from textual import events
from rich.text import Text
from rich.panel import Panel
from rich.console import Console, Group
from rich.table import Table

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.underwriting.production_pipeline import (
    ProductionPipeline,
    create_risk_case_from_synthetic,
)


class ResultsPanel(Static):
    """Component to display underwriting results."""

    def on_mount(self) -> None:
        self.update(
            Panel(
                "Select a patient profile to begin underwriting analysis.",
                title="Analysis Results",
            )
        )


class UnderwritingApp(App):
    """Main Textual application for insurance underwriting."""

    CSS = """
    Screen {
        background: $surface;
    }

    Header {
        background: $primary-darken-2;
        color: white;
        text-style: bold;
    }

    #main_container {
        padding: 1;
        height: 100%;
        layout: horizontal;
    }

    #left_pane {
        width: 30%;
        height: 100%;
        border-right: solid $primary;
        padding-right: 1;
    }

    #right_pane {
        width: 70%;
        height: 100%;
        padding-left: 1;
    }

    ListView {
        height: 1fr;
        border: solid $primary;
        margin-bottom: 1;
    }
    
    ListItem {
        padding: 1;
    }
    
    ListItem:hover {
        background: $accent;
    }

    Button {
        width: 100%;
        margin-bottom: 1;
    }

    .section_title {
        background: $primary;
        color: white;
        padding: 1;
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self.pipeline = ProductionPipeline()
        self.patient_profiles = self._load_patient_profiles()
        self.profile_keys = list(self.patient_profiles.keys())

    def _load_patient_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Load available patient profiles."""
        profiles = {}
        # Add synthetic profiles for demo
        profiles["Synthetic: Priya Sharma"] = {"type": "synthetic", "id": "priya"}
        profiles["Synthetic: Rahul Mehta"] = {"type": "synthetic", "id": "rahul"}

        profile_dir = Path("patient_profiles")
        if profile_dir.exists():
            for patient_dir in profile_dir.iterdir():
                if patient_dir.is_dir() and not patient_dir.name.startswith("."):
                    profile_file = patient_dir / "patient_profile.txt"
                    if profile_file.exists():
                        profiles[f"File: {patient_dir.name}"] = {
                            "path": str(profile_file)
                        }
        return profiles

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()

        with Container(id="main_container"):
            # Left Pane: Selection & Controls
            with Container(id="left_pane"):
                yield Static("Available Profiles", classes="section_title")

                if self.profile_keys:
                    list_items = [ListItem(Label(name)) for name in self.profile_keys]
                    yield ListView(*list_items, id="profile_list")
                else:
                    yield Static("No patient profiles found.")

                yield Button(
                    "RUN ANALYSIS", id="process_btn", variant="primary", disabled=True
                )
                yield Button("EXIT SYSTEM", id="exit_btn", variant="error")

            # Right Pane: Results
            with VerticalScroll(id="right_pane"):
                yield ResultsPanel(id="results_panel")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Enable process button when profile is selected."""
        self.query_one("#process_btn").disabled = False

        # Show immediate feedback
        list_view = self.query_one("#profile_list", ListView)
        if list_view.index is not None and list_view.index < len(self.profile_keys):
            profile_name = self.profile_keys[list_view.index]

            self.query_one("#results_panel").update(
                Panel(
                    f"Selected: [bold]{profile_name}[/bold]\n\nPress 'RUN ANALYSIS' to start the underwriting pipeline.",
                    title="Ready to Process",
                    border_style="blue",
                )
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "process_btn":
            self._process_underwriting()
        elif event.button.id == "exit_btn":
            self.exit()

    def _process_underwriting(self) -> None:
        """Run the underwriting pipeline for selected profile."""
        list_view = self.query_one("#profile_list", ListView)
        if list_view.index is not None and list_view.index < len(self.profile_keys):
            profile_name = self.profile_keys[list_view.index]
        else:
            return

        results_panel = self.query_one("#results_panel", ResultsPanel)
        results_panel.update(
            Panel(LoadingIndicator(), title="Processing...", border_style="yellow")
        )

        # Schedule the pipeline run
        self.call_later(self._run_pipeline, profile_name)

    def _run_pipeline(self, profile_name: str) -> None:
        """Actual execution of pipeline."""
        results_panel = self.query_one("#results_panel", ResultsPanel)

        try:
            # Get data
            synthetic_data = self._get_synthetic_data_for_profile(profile_name)

            risk_case = create_risk_case_from_synthetic(synthetic_data)
            offer = self.pipeline.process(risk_case)

            # Format results for TUI display
            result_content = self._format_results(offer, risk_case)
            results_panel.update(result_content)

        except Exception as e:
            error_text = (
                f"[bold red]Error processing underwriting:[/bold red]\n{str(e)}"
            )
            import traceback

            error_text += f"\n\n{traceback.format_exc()}"
            results_panel.update(Panel(error_text, title="Error", border_style="red"))

    def _format_results(self, offer, risk_case) -> Panel:
        """Format the offer into a nice Rich renderable."""

        # Decision Header
        decision_color = (
            "green"
            if offer.decision in ["APPROVE", "APPROVE_WITH_LOADING"]
            else "red" if offer.decision == "DECLINE" else "yellow"
        )

        # Main Table
        table = Table(show_header=False, box=None, padding=(0, 2), expand=True)
        table.add_column("Key", style="bold white")
        table.add_column("Value")

        table.add_row(
            "Decision",
            f"[{decision_color} bold reverse] {offer.decision} [/{decision_color} bold reverse]",
        )
        table.add_row("Risk Class", offer.risk_class)

        if offer.decision in ["APPROVE", "APPROVE_WITH_LOADING"]:
            table.add_row("Sum Assured", f"Rs.{offer.sum_assured:,.0f}")
            table.add_row("Base Premium", f"Rs.{offer.base_premium_annual:,.0f}/year")
            if offer.total_loading_percent > 0:
                table.add_row("Total Loading", f"+{offer.total_loading_percent}%")
            table.add_row(
                "Final Premium",
                f"[bold]Rs.{offer.loaded_premium_annual:,.0f}/year[/bold]",
            )

        section_text = Text()
        section_text.append("\nReasoning:\n", style="bold underline")
        section_text.append(offer.reasoning + "\n")

        section_text.append("\nLLM Advisory:\n", style="bold underline")
        section_text.append(offer.llm_advisory_summary + "\n")

        if offer.loadings:
            section_text.append("\nActive Loadings:\n", style="bold underline")
            for l in offer.loadings:
                section_text.append(f"• {l['condition']}: +{l['percent']}%\n")

        if offer.exclusions:
            section_text.append("\nExclusions:\n", style="bold underline red")
            for ex in offer.exclusions:
                section_text.append(f"• {ex}\n")

        # Combine
        content = Group(
            Text(f"Case ID: {risk_case.case_id}", style="dim"),
            Text(f"Applicant: {risk_case.identity.full_name.value}", style="bold"),
            Text(""),
            table,
            section_text,
        )

        return Panel(
            content,
            title=f"Underwriting Decision: {offer.decision}",
            border_style=decision_color,
        )

    def _get_synthetic_data_for_profile(self, profile_name: str) -> Dict[str, Any]:
        """Get synthetic data for demo."""

        # Default benign case
        data = {
            "full_name": "Priya Sharma",
            "dob": "15/03/1988",
            "age": 36,
            "gender": "Female",
            "sum_assured": 15000000,
            "height_cm": 162,
            "weight_kg": 58,
            "bmi": 22.1,
            "diabetes_declared": "No",
            "smoking_status": "Never",
            "alcohol_status": "Social",
            "occupation": "Software Engineer",
            "annual_income": 2400000,
            "bp_systolic": 118,
            "bp_diastolic": 78,
        }

        # Override for high risk case
        if "Rahul" in profile_name:
            data.update(
                {
                    "full_name": "Rahul Mehta",
                    "age": 45,
                    "gender": "Male",
                    "weight_kg": 95,
                    "height_cm": 175,
                    "bmi": 31.0,  # Obese
                    "diabetes_declared": "Type 2",
                    "hba1c": 8.2,  # Uncontrolled
                    "smoking_status": "Current",
                    "pack_years": 15,
                    "bp_systolic": 145,
                    "bp_diastolic": 95,
                }
            )

        return data


def main():
    app = UnderwritingApp()
    app.run()


if __name__ == "__main__":
    main()
