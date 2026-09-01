# SPDX-FileCopyrightText: 2026 denis-samatov
# SPDX-License-Identifier: Apache-2.0
# SPDX-PackageName: rai-toolkit

from pathlib import Path

from rai_toolkit.assessment import Assessor
from rai_toolkit.cli import main
from rai_toolkit.compliance.engine import ComplianceMappingEngine
from rai_toolkit.examples import DEMO_EXAMPLE_BUNDLES
from rai_toolkit.models.base import BaseModel, ModelResponse
from rai_toolkit.monitoring import recommended_reassessment_interval_days
from rai_toolkit.workflow import ApplicationProfile, Industry, scope_assessor


class StubModel(BaseModel):
    async def predict(
        self,
        input_text: str,
        context: str = "",
        **kwargs: object,
    ) -> ModelResponse:
        return ModelResponse(output="stub")


def test_hr_industry_round_trips_through_profile_dict() -> None:
    profile = ApplicationProfile(
        name="Hiring assistant",
        description="Supports candidate review",
        owner_team="people",
        owner_email="people@example.com",
        industry=Industry.HR,
    )

    payload = profile.to_dict()
    restored = ApplicationProfile.from_dict(payload)

    assert payload["industry"] == "hr"
    assert restored.industry is Industry.HR


def test_hr_preset_resolves_expected_mit_categories() -> None:
    profile = ComplianceMappingEngine().create_profile_from_preset("hr")

    assert profile.category_ids == [
        "MIT-1.1",
        "MIT-1.3",
        "MIT-2.1",
        "MIT-3.1",
        "MIT-5.1",
        "MIT-5.2",
        "MIT-7.2",
    ]


def test_hr_demo_bundle_uses_bias_benchmarks() -> None:
    assert DEMO_EXAMPLE_BUNDLES["hr"] == ["bbq", "bold"]


def test_hr_sample_scoping_composes_existing_defaults() -> None:
    profile = ApplicationProfile(
        name="Hiring assistant",
        description="Supports candidate review",
        owner_team="people",
        owner_email="people@example.com",
        industry=Industry.HR,
        allow_sample_datasets=True,
    )

    assessor, decision = scope_assessor(profile, StubModel())

    assert decision.preset == "hr"
    assert decision.datasets == ["bbq", "bold"]
    assert assessor.datasets == ["bbq", "bold"]
    assert decision.policies_dir is not None
    assert (Path(decision.policies_dir) / "fairness_baseline.yaml").is_file()


def test_hr_uses_high_impact_redteam_severity_gate() -> None:
    assessor = Assessor(
        model=StubModel(),
        preset="hr",
        datasets=["bbq"],
        run_redteam=False,
    )

    assert assessor.redteam_severity_gate == 3


def test_hr_uses_30_day_reassessment_cadence() -> None:
    assert recommended_reassessment_interval_days("hr") == 30


def test_demo_datasets_cli_filters_to_hr(capsys) -> None:
    exit_code = main(["datasets", "demo-datasets", "--preset", "hr"])

    assert exit_code == 0
    assert capsys.readouterr().out == "hr                      bbq, bold\n"
