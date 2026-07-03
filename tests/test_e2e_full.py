"""Full-pipeline e2e with REAL models (mpnet + NLI cross-encoder).

Extends the canonical phase-1 fixture: verdict, classification, attribution
must all point at step 3 (the deliberate logical leap).
"""
from castor import CascadeAnalyzer
from tests.test_e2e import TRAJECTORY


def test_full_pipeline_attributes_step3():
    report = CascadeAnalyzer().analyze(TRAJECTORY)

    assert report.monitoring_failure is None, report.monitoring_failure
    assert not report.degraded
    assert report.verdict
    assert len(report.steps) == 5

    # Entailment collapses exactly at the leap transition (2 -> 3).
    step3 = next(s for s in report.steps if s.step_id == 3)
    assert step3.entailment is not None and step3.entailment < 0.5
    assert step3.conclusive  # "Therefore, ..."

    # Step 3 carries the highest aggregate anomaly score.
    scored = [s for s in report.steps if s.aggregate is not None]
    top = max(scored, key=lambda s: s.aggregate)
    assert top.step_id == 3, [(s.step_id, s.aggregate) for s in scored]

    # Classification is non-empty and every entry carries confidence.
    assert report.classification
    assert all(0.0 <= t.confidence <= 1.0 for t in report.classification)

    # Attribution: step 3 among the candidates, honesty fields mandatory.
    origin_steps = [c.origin_step for c in report.attribution]
    assert 3 in origin_steps
    assert all(c.method == "threshold-based" for c in report.attribution)

    # Reproducibility fields (FR-8).
    assert report.models["embedding"]
    assert report.models["nli"]
    assert report.castor_version
