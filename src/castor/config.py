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

# FR-11: embedding-cache sliding window for very long trajectories — the
# anchor embedding is always retained, plus this many most recent steps.
DEFAULT_CACHE_WINDOW = 128
