"""Single config location for all default thresholds and model names (FR-5).

All values are starting points inherited from CHARM and are expected to be
recalibrated per domain (`castor calibrate`, phase 4+). Never hardcode these
inline elsewhere.
"""

# FR-5: drift flagging threshold (CHARM delta_drift). Configurable per DriftTracker instance.
DEFAULT_DRIFT_THRESHOLD = 0.18

# FR-4 (phase 2, unused in phase 1): entailment threshold (CHARM tau_entail).
DEFAULT_ENTAILMENT_THRESHOLD = 0.72

# FR-2: default local embedding model, consistent with CHARM for comparability.
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"

# FR-4: default local NLI cross-encoder, consistent with CHARM.
DEFAULT_NLI_MODEL = "cross-encoder/nli-deberta-v3-base"

# Aggregate anomaly threshold (CHARM theta). Same caveat: starting point only.
DEFAULT_AGGREGATE_THRESHOLD = 0.55

# Aggregator weights (drift, entailment, confidence-language), inherited from
# CHARM as reasonable manual defaults, NOT learned values — documented known
# limitation (PRD 3.3). Recalibrated from synthetic data in v1.
DEFAULT_AGGREGATOR_WEIGHTS = (0.4, 0.4, 0.2)

# FR-6: minimum rule-based score for a cascade type to appear in the
# multi-label classification output.
DEFAULT_CLASSIFICATION_THRESHOLD = 0.4

# v1 item 3: trajectory-level verdict triggers.
#
# The aggregate above is a weighted MEAN, so one collapsed signal is diluted by
# the calm ones: an entailment of 0.003 is strong evidence on its own, but
# averaged at weight 0.4 against low drift and a flat certainty delta it lands
# under theta. Measured consequence on the organic set: the aggregate rule fired
# on 0 of 24 annotated cascades that per-step flags all caught.
#
# The verdict is therefore a DISJUNCTION — aggregate OR any single signal
# collapsing on its own. These trigger levels are deliberately stricter than the
# per-step flag thresholds: a step is worth showing the user at the flag level,
# but the trajectory verdict should need collapse-grade evidence.
#
# `None` disables a trigger, leaving the disjunction to the remaining ones.
#
# UNMEASURED (2026-08-08): the entailment and drift levels below are reasoned
# starting points, NOT calibrated values — the full organic scoring pass that
# would fix them is pending (`validation/sweep_verdict.py --refresh`). Treat
# them as provisional and recalibrate per domain. See STATUS.md.
DEFAULT_ENTAIL_COLLAPSE: float | None = 0.01
DEFAULT_DRIFT_COLLAPSE: float | None = 0.9

# MEASURED, and the measurement is why this is None. Over the 28 annotated
# organic chains the maximum per-chain omission is 0.67/0.67/0.75/1.00 on the
# four chains annotated CLEAN — the top of the range, overlapping the cascaded
# chains (0.33-1.00) completely. Every threshold below 0.67 flags 4/4 clean
# chains; 0.75 keeps only 17% recall. Omission earns its place as a per-step
# attribution signal (it doubled exact-origin accuracy) but it cannot separate
# broken trajectories from healthy ones, so it is not a verdict trigger.
DEFAULT_OMISSION_COLLAPSE: float | None = None

# FR-11: embedding-cache sliding window for very long trajectories — the
# anchor embedding is always retained, plus this many most recent steps.
DEFAULT_CACHE_WINDOW = 128

# v1 item 1 (omission/completeness signal). A source fact counts as still
# carried by a step when the step entails it at or above this probability.
# Starting point only, same caveat as every other threshold here: entailment
# mass is domain-dependent and this needs recalibration per pipeline.
DEFAULT_COVERAGE_THRESHOLD = 0.5

# v1 item 1: flag level for the per-step drop in source-fact coverage.
DEFAULT_OMISSION_THRESHOLD = 0.25

# v1 item 1: cap on anchor facts scored per step. Bounds the NLI cost of the
# coverage check at (steps x facts) pairs on long source documents (FR-11).
DEFAULT_MAX_ANCHOR_FACTS = 12

# v1 item 1: sentence fragments shorter than this are merged into the previous
# fact instead of becoming their own hypothesis.
DEFAULT_MIN_FACT_CHARS = 25
