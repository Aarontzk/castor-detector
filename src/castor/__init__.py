"""Castor — hallucination cascade detection for multi-agent LLM pipelines.

Detect (dual-reference drift + NLI), classify (4 CHARM cascade types),
attribute (threshold-based origin candidates with honest confidence).
Passive observer — never blocks or crashes the host pipeline. 100% local.
"""
from .aggregate import AggregatorWeights, aggregate_score
from .analysis import CascadeAnalyzer
from .attribution import attribute
from .calibrate import CalibrationResult, ThresholdProfile, calibrate
from .config import (
    DEFAULT_AGGREGATE_THRESHOLD,
    DEFAULT_DRIFT_THRESHOLD,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_ENTAILMENT_THRESHOLD,
    DEFAULT_NLI_MODEL,
)
from .confidence import CertaintySignal, certainty_signal
from .drift import DriftReport, DriftTracker, StepDrift
from .embedding import Embedder, SentenceTransformerEmbedder, cosine_similarity
from .entailment import CrossEncoderEntailment, EntailmentChecker, EntailmentResult
from .inject import INJECTION_KINDS, InjectionRecord, inject
from .observer import CastorObserver
from .report import CascadeReport, OriginCandidate, StepSignals, TypeScore
from .taxonomy import classify
from .trajectory import Trajectory, TrajectoryStep

__version__ = "0.1.0"

__all__ = [
    "AggregatorWeights",
    "aggregate_score",
    "CascadeAnalyzer",
    "attribute",
    "CalibrationResult",
    "ThresholdProfile",
    "calibrate",
    "DEFAULT_AGGREGATE_THRESHOLD",
    "DEFAULT_DRIFT_THRESHOLD",
    "DEFAULT_EMBEDDING_MODEL",
    "DEFAULT_ENTAILMENT_THRESHOLD",
    "DEFAULT_NLI_MODEL",
    "CertaintySignal",
    "certainty_signal",
    "DriftReport",
    "DriftTracker",
    "StepDrift",
    "Embedder",
    "SentenceTransformerEmbedder",
    "cosine_similarity",
    "CrossEncoderEntailment",
    "EntailmentChecker",
    "EntailmentResult",
    "INJECTION_KINDS",
    "InjectionRecord",
    "inject",
    "CastorObserver",
    "CascadeReport",
    "OriginCandidate",
    "StepSignals",
    "TypeScore",
    "classify",
    "Trajectory",
    "TrajectoryStep",
    "__version__",
]
