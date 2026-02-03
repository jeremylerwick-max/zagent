"""
PCO Core Module

The core components of the Parallel Context Orchestrator.
"""

from .orchestrator import (
    ParallelOrchestrator,
    UserRequest,
    OrchestratorResponse,
    ResponseMetadata,
    RequestStatus,
    StreamEvent,
)

from .consensus import (
    WeightedConsensus,
    WindowOutput,
    ConsensusResult,
    TaskType,
    DebateRound,
    ReputationTracker,
)

from .context_hierarchy import (
    SlidingContextHierarchy,
    ContextChunk,
    ContextTier,
    TierConfig,
)

from .dispatcher import (
    Dispatcher,
    DispatchResult,
    DispatchStatus,
    WindowTask,
    BatchDispatcher,
)

from .collector import (
    Collector,
    CollectedOutputs,
    OutputAggregator,
)

from .router import (
    AdaptiveRouter,
    RoutingDecision,
    RoutingMode,
    RoutingConfig,
    RequestClassifier,
    RequestComplexity,
)

from .synthesizer import (
    Synthesizer,
    SynthesisResult,
    SynthesisStrategies,
    StreamingSynthesizer,
)

__all__ = [
    # Orchestrator
    "ParallelOrchestrator",
    "UserRequest",
    "OrchestratorResponse",
    "ResponseMetadata",
    "RequestStatus",
    "StreamEvent",
    # Consensus
    "WeightedConsensus",
    "WindowOutput",
    "ConsensusResult",
    "TaskType",
    "DebateRound",
    "ReputationTracker",
    # Context
    "SlidingContextHierarchy",
    "ContextChunk",
    "ContextTier",
    "TierConfig",
    # Dispatcher
    "Dispatcher",
    "DispatchResult",
    "DispatchStatus",
    "WindowTask",
    "BatchDispatcher",
    # Collector
    "Collector",
    "CollectedOutputs",
    "OutputAggregator",
    # Router
    "AdaptiveRouter",
    "RoutingDecision",
    "RoutingMode",
    "RoutingConfig",
    "RequestClassifier",
    "RequestComplexity",
    # Synthesizer
    "Synthesizer",
    "SynthesisResult",
    "SynthesisStrategies",
    "StreamingSynthesizer",
]
