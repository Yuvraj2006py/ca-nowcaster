"""Production model selection for the live nowcast pipeline.

Phase 3 Evaluation Skeptic verdict (docs/evaluation_report.md): no regression
candidate beats the AR(1) reference on headline RMSE with Diebold-Mariano and
bootstrap CI support. Honest-result rule → ship v1 with the AR(1) baseline.
"""

from __future__ import annotations

# Registry name / version must match nowcaster.models.baselines.AR1Baseline.
PRODUCTION_MODEL_NAME = "ar1"
PRODUCTION_MODEL_VERSION = "0.1.0"

PRODUCTION_MODEL_RATIONALE = (
    "Phase 3 evaluation (docs/evaluation_report.md) found that no regression "
    "candidate (bridge, dynamic_factor, gradient_boosting) beats the AR(1) "
    "reference on headline RMSE with Diebold-Mariano significance and bootstrap "
    "CI support. Direction classifiers are scored separately and are not used "
    "as the GDP MoM point nowcast. Under the honest-result rule, v1 ships with "
    "AR(1) as the production model rather than a candidate that failed to clear "
    "the skeptic bar."
)

PRIMARY_TARGET_SERIES_ID = "ca_gdp_basic_prices"


def production_model_meta() -> dict[str, str]:
    """Return production model identity and rationale for logs / docs.

    Inputs: none (constants only).
    Outputs: dict with name, version, rationale.
    Time allowed to know: none (policy metadata only).
    """
    return {
        "model_name": PRODUCTION_MODEL_NAME,
        "model_version": PRODUCTION_MODEL_VERSION,
        "rationale": PRODUCTION_MODEL_RATIONALE,
    }
