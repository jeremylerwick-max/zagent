"""
Parallel Context Orchestrator - Main Coordinator

The orchestrator is the central brain of PCO. It:
1. Receives user requests
2. Routes them through security
3. Dispatches to parallel windows
4. Collects and validates outputs
5. Runs consensus/debate
6. Synthesizes final response
7. Logs everything for audit

This is the main entry point for all PCO operations.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, AsyncIterator
from enum import Enum
from datetime import datetime
import uuid
import logging

from .consensus import (
    WeightedConsensus,
    WindowOutput,
    ConsensusResult,
    TaskType,
    DebateRound,
    ReputationTracker,
)
from .context_hierarchy import SlidingContextHierarchy, ContextChunk
from .dispatcher import Dispatcher, DispatchResult
from .collector import Collector, CollectedOutputs
from .router import AdaptiveRouter, RoutingDecision, RoutingMode

# Import security if available
try:
    from ..security import ZeroTrustGate, ProvenanceTracker, TrustLevel
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False
    ZeroTrustGate = None
    ProvenanceTracker = None

logger = logging.getLogger(__name__)


class RequestStatus(Enum):
    """Status of a request through the pipeline."""
    PENDING = "pending"
    VALIDATING = "validating"
    ROUTING = "routing"
    DISPATCHING = "dispatching"
    PROCESSING = "processing"
    COLLECTING = "collecting"
    CONSENSUS = "consensus"
    DEBATING = "debating"
    SYNTHESIZING = "synthesizing"
    COMPLETE = "complete"
    FAILED = "failed"


class WindowStatus(Enum):
    """Status of a window's processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    TIMEOUT = "timeout"
    FAILED = "failed"


@dataclass
class UserRequest:
    """Incoming user request with metadata."""
    id: str
    content: str
    timestamp: datetime
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    routing_hint: Optional[str] = None  # User can hint: "fast", "thorough"
    context: Optional[Dict[str, Any]] = None

    @classmethod
    def create(cls, content: str, **kwargs) -> "UserRequest":
        return cls(
            id=str(uuid.uuid4()),
            content=content,
            timestamp=datetime.utcnow(),
            **kwargs
        )


@dataclass
class ResponseMetadata:
    """Metadata about how a response was generated."""
    request_id: str
    windows_used: List[str]
    windows_failed: List[str]
    consensus_score: float
    consensus_reached: bool
    debate_rounds: int
    routing_mode: str
    total_latency_ms: float
    degraded: bool = False
    provenance_ids: List[str] = field(default_factory=list)


@dataclass
class OrchestratorResponse:
    """Final response from the orchestrator."""
    content: str
    metadata: ResponseMetadata
    status: RequestStatus
    error: Optional[str] = None


@dataclass
class StreamEvent:
    """Event emitted during streaming."""
    type: str  # "status", "window_complete", "consensus", "content", "error"
    data: Any
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ParallelOrchestrator:
    """
    Main coordinator for Parallel Context Orchestrator.

    Manages the full request lifecycle:
    Request → Security → Routing → Dispatch → Collect → Consensus → Synthesize → Response
    """

    def __init__(
        self,
        windows: Optional[Dict[str, Any]] = None,
        router: Optional[AdaptiveRouter] = None,
        consensus: Optional[WeightedConsensus] = None,
        context_hierarchy: Optional[SlidingContextHierarchy] = None,
        security_gate: Optional["ZeroTrustGate"] = None,
        provenance: Optional["ProvenanceTracker"] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the orchestrator.

        Args:
            windows: Dict of window_name -> Window instance
            router: Adaptive router for request classification
            consensus: Weighted consensus calculator
            context_hierarchy: Sliding context manager for Scout
            security_gate: Zero Trust security gate
            provenance: Memory provenance tracker
            config: Additional configuration
        """
        self.config = config or {}

        # Core components
        self.windows = windows or {}
        self.router = router or AdaptiveRouter()
        self.consensus = consensus or WeightedConsensus()
        self.context = context_hierarchy or SlidingContextHierarchy()

        # Security (optional but recommended)
        self.security = security_gate
        self.provenance = provenance

        # Internal components
        self.dispatcher = Dispatcher(self.windows)
        self.collector = Collector()

        # Metrics tracking
        self._request_count = 0
        self._active_requests: Dict[str, RequestStatus] = {}

        logger.info(f"ParallelOrchestrator initialized with {len(self.windows)} windows")

    async def process(self, request: UserRequest) -> OrchestratorResponse:
        """
        Process a user request through the full pipeline.

        This is the main entry point for synchronous processing.

        Args:
            request: The user request to process

        Returns:
            OrchestratorResponse with content and metadata
        """
        start_time = time.time()
        self._request_count += 1
        self._active_requests[request.id] = RequestStatus.PENDING

        try:
            # 1. Security validation
            self._update_status(request.id, RequestStatus.VALIDATING)
            if self.security:
                allowed, reason = self.security.check_request(
                    actor=f"user:{request.user_id or 'anonymous'}",
                    action="process_request",
                    input_text=request.content,
                    context="general",
                )
                if not allowed:
                    return self._create_error_response(
                        request, f"Security validation failed: {reason}", start_time
                    )

            # 2. Route request
            self._update_status(request.id, RequestStatus.ROUTING)
            routing = self.router.classify_and_route(request)
            logger.info(f"Request {request.id} routed: mode={routing.mode.name}, windows={routing.windows}")

            # 3. Dispatch to parallel windows
            self._update_status(request.id, RequestStatus.DISPATCHING)
            dispatch_result = await self.dispatcher.dispatch(
                request=request,
                windows=routing.windows,
                timeout=routing.timeout,
            )

            # 4. Collect outputs
            self._update_status(request.id, RequestStatus.COLLECTING)
            collected = self.collector.collect(dispatch_result)

            if not collected.valid_outputs:
                return self._create_error_response(
                    request, "All windows failed to produce output", start_time
                )

            # 5. Run consensus
            self._update_status(request.id, RequestStatus.CONSENSUS)
            consensus_result = self.consensus.calculate_consensus(
                outputs=collected.valid_outputs,
                task_type=routing.task_type,
            )

            # 6. Debate if needed
            debate_rounds = 0
            if not consensus_result.consensus_reached and routing.mode != RoutingMode.FAST:
                self._update_status(request.id, RequestStatus.DEBATING)
                debate = DebateRound(self.consensus)
                consensus_result = await debate.run_debate(
                    outputs=collected.valid_outputs,
                    task_type=routing.task_type,
                    debate_callback=lambda outputs: self._run_debate_round(request, outputs),
                )
                debate_rounds = len(debate.round_history)

            # 7. Synthesize final response
            self._update_status(request.id, RequestStatus.SYNTHESIZING)
            final_content = await self._synthesize(
                request=request,
                outputs=collected.valid_outputs,
                consensus=consensus_result,
                routing=routing,
            )

            # 8. Create provenance records
            provenance_ids = []
            if self.provenance:
                for output in collected.valid_outputs:
                    prov = self.provenance.create_provenance(
                        content=output.content,
                        source=f"window:{output.window_name}",
                    )
                    if consensus_result.winning_content == output.content:
                        self.provenance.record_verification(prov.id, "consensus", True)
                    provenance_ids.append(prov.id)

            # 9. Update reputation
            if consensus_result.winning_content:
                winner_name = self._find_winner_name(collected.valid_outputs, consensus_result)
                self.consensus.update_reputation_from_result(
                    outputs=collected.valid_outputs,
                    selected_window=winner_name,
                    task_type=routing.task_type,
                )

            # 10. Add to context hierarchy
            self.context.add_context(
                content=f"User: {request.content}\n\nAssistant: {final_content}",
                source="conversation",
            )

            # Create response
            self._update_status(request.id, RequestStatus.COMPLETE)
            total_latency = (time.time() - start_time) * 1000

            return OrchestratorResponse(
                content=final_content,
                metadata=ResponseMetadata(
                    request_id=request.id,
                    windows_used=[o.window_name for o in collected.valid_outputs],
                    windows_failed=collected.failed_windows,
                    consensus_score=consensus_result.decision_score,
                    consensus_reached=consensus_result.consensus_reached,
                    debate_rounds=debate_rounds,
                    routing_mode=routing.mode.name,
                    total_latency_ms=total_latency,
                    degraded=len(collected.failed_windows) > 0,
                    provenance_ids=provenance_ids,
                ),
                status=RequestStatus.COMPLETE,
            )

        except Exception as e:
            logger.exception(f"Error processing request {request.id}")
            self._update_status(request.id, RequestStatus.FAILED)
            return self._create_error_response(request, str(e), start_time)

    async def process_streaming(
        self,
        request: UserRequest
    ) -> AsyncIterator[StreamEvent]:
        """
        Process a request with streaming events.

        Yields events as processing progresses, allowing clients
        to show real-time progress.

        Args:
            request: The user request to process

        Yields:
            StreamEvent objects with progress updates
        """
        start_time = time.time()
        self._request_count += 1
        self._active_requests[request.id] = RequestStatus.PENDING

        try:
            # 1. Security validation
            yield StreamEvent(type="status", data={"status": "validating"})
            if self.security:
                allowed, reason = self.security.check_request(
                    actor=f"user:{request.user_id or 'anonymous'}",
                    action="process_request",
                    input_text=request.content,
                    context="general",
                )
                if not allowed:
                    yield StreamEvent(type="error", data={"error": reason})
                    return

            # 2. Route request
            yield StreamEvent(type="status", data={"status": "routing"})
            routing = self.router.classify_and_route(request)
            yield StreamEvent(type="routing", data={
                "mode": routing.mode.name,
                "windows": routing.windows,
                "task_type": routing.task_type.value,
            })

            # 3. Dispatch with streaming updates
            yield StreamEvent(type="status", data={"status": "processing"})

            # Create tasks for each window
            tasks = {}
            for window_name in routing.windows:
                if window_name in self.windows:
                    task = asyncio.create_task(
                        self._process_window_with_timeout(
                            window_name, request, routing.timeout
                        )
                    )
                    tasks[window_name] = task

            # Wait for windows and yield progress
            completed_windows = set()
            outputs = []

            while len(completed_windows) < len(tasks):
                done, _ = await asyncio.wait(
                    tasks.values(),
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=1.0,
                )

                for task in done:
                    # Find which window this task belongs to
                    for name, t in tasks.items():
                        if t == task and name not in completed_windows:
                            completed_windows.add(name)
                            try:
                                output = task.result()
                                outputs.append(output)
                                yield StreamEvent(type="window_complete", data={
                                    "window": name,
                                    "status": "success",
                                    "confidence": output.confidence,
                                    "progress": len(completed_windows) / len(tasks),
                                })
                            except Exception as e:
                                yield StreamEvent(type="window_complete", data={
                                    "window": name,
                                    "status": "failed",
                                    "error": str(e),
                                    "progress": len(completed_windows) / len(tasks),
                                })
                            break

            # 4. Consensus
            yield StreamEvent(type="status", data={"status": "consensus"})
            valid_outputs = [o for o in outputs if o.confidence > 0]

            if not valid_outputs:
                yield StreamEvent(type="error", data={"error": "All windows failed"})
                return

            consensus_result = self.consensus.calculate_consensus(
                outputs=valid_outputs,
                task_type=routing.task_type,
            )

            yield StreamEvent(type="consensus", data={
                "score": consensus_result.decision_score,
                "reached": consensus_result.consensus_reached,
                "dissenters": consensus_result.dissenting_windows,
            })

            # 5. Synthesize
            yield StreamEvent(type="status", data={"status": "synthesizing"})
            final_content = await self._synthesize(
                request=request,
                outputs=valid_outputs,
                consensus=consensus_result,
                routing=routing,
            )

            # 6. Final response
            total_latency = (time.time() - start_time) * 1000
            yield StreamEvent(type="complete", data={
                "content": final_content,
                "latency_ms": total_latency,
                "windows_used": [o.window_name for o in valid_outputs],
            })

        except Exception as e:
            logger.exception(f"Error in streaming process {request.id}")
            yield StreamEvent(type="error", data={"error": str(e)})

    async def _process_window_with_timeout(
        self,
        window_name: str,
        request: UserRequest,
        timeout: float,
    ) -> WindowOutput:
        """Process a single window with timeout handling."""
        window = self.windows.get(window_name)
        if not window:
            return WindowOutput(
                window_name=window_name,
                content="",
                confidence=0.0,
                task_type=TaskType.GENERAL,
            )

        try:
            result = await asyncio.wait_for(
                window.process(request),
                timeout=timeout,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Window {window_name} timed out after {timeout}s")
            return WindowOutput(
                window_name=window_name,
                content="",
                confidence=0.0,
                task_type=TaskType.GENERAL,
            )
        except Exception as e:
            logger.error(f"Window {window_name} failed: {e}")
            return WindowOutput(
                window_name=window_name,
                content="",
                confidence=0.0,
                task_type=TaskType.GENERAL,
            )

    async def _run_debate_round(
        self,
        request: UserRequest,
        outputs: List[WindowOutput]
    ) -> List[WindowOutput]:
        """
        Run one round of debate where windows critique each other.

        Each window sees all outputs and provides revised output.
        """
        debate_prompt = self._build_debate_prompt(request, outputs)

        tasks = []
        for output in outputs:
            if output.window_name in self.windows:
                window = self.windows[output.window_name]
                task = asyncio.create_task(
                    window.debate(request, outputs, debate_prompt)
                )
                tasks.append((output.window_name, task))

        revised_outputs = []
        for window_name, task in tasks:
            try:
                revised = await asyncio.wait_for(task, timeout=60.0)
                revised_outputs.append(revised)
            except Exception as e:
                logger.warning(f"Debate failed for {window_name}: {e}")
                # Keep original output
                original = next((o for o in outputs if o.window_name == window_name), None)
                if original:
                    revised_outputs.append(original)

        return revised_outputs

    def _build_debate_prompt(
        self,
        request: UserRequest,
        outputs: List[WindowOutput]
    ) -> str:
        """Build the debate prompt showing all window outputs."""
        parts = [
            "# Debate Round",
            "",
            "Other windows have produced the following outputs for this request.",
            "Review them, identify any issues, and provide your revised response.",
            "",
            f"## Original Request",
            request.content,
            "",
        ]

        for output in outputs:
            parts.extend([
                f"## {output.window_name.upper()} Output (confidence: {output.confidence})",
                output.content,
                "",
            ])

        parts.extend([
            "## Your Task",
            "1. Identify errors or issues in other outputs",
            "2. Consider their valid points",
            "3. Provide your revised, improved response",
        ])

        return "\n".join(parts)

    async def _synthesize(
        self,
        request: UserRequest,
        outputs: List[WindowOutput],
        consensus: ConsensusResult,
        routing: RoutingDecision,
    ) -> str:
        """
        Synthesize final response from window outputs.

        If a synthesizer window is available, uses it.
        Otherwise, uses consensus winner directly.
        """
        synthesizer = self.windows.get("synthesizer")

        if synthesizer:
            # Get relevant context from hierarchy
            context_str = self.context.build_context_window(
                query=request.content,
                include_warm=True,
                max_tokens=500_000,  # 500K tokens for synthesis context
            )

            return await synthesizer.synthesize(
                request=request,
                outputs=outputs,
                consensus=consensus,
                context=context_str,
            )
        else:
            # Fallback: use consensus winner
            return consensus.winning_content

    def _find_winner_name(
        self,
        outputs: List[WindowOutput],
        consensus: ConsensusResult
    ) -> str:
        """Find the name of the window that produced the winning content."""
        for output in outputs:
            if output.content == consensus.winning_content:
                return output.window_name
        return outputs[0].window_name if outputs else "unknown"

    def _update_status(self, request_id: str, status: RequestStatus):
        """Update request status for tracking."""
        self._active_requests[request_id] = status
        logger.debug(f"Request {request_id} status: {status.value}")

    def _create_error_response(
        self,
        request: UserRequest,
        error: str,
        start_time: float,
    ) -> OrchestratorResponse:
        """Create an error response."""
        return OrchestratorResponse(
            content="",
            metadata=ResponseMetadata(
                request_id=request.id,
                windows_used=[],
                windows_failed=[],
                consensus_score=0.0,
                consensus_reached=False,
                debate_rounds=0,
                routing_mode="failed",
                total_latency_ms=(time.time() - start_time) * 1000,
            ),
            status=RequestStatus.FAILED,
            error=error,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            "total_requests": self._request_count,
            "active_requests": len(self._active_requests),
            "windows": list(self.windows.keys()),
            "reputation_weights": self.consensus.reputation.get_all_weights(),
            "context_stats": self.context.get_stats(),
        }

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all components."""
        health = {
            "orchestrator": "healthy",
            "windows": {},
        }

        for name, window in self.windows.items():
            try:
                if hasattr(window, "ping"):
                    await asyncio.wait_for(window.ping(), timeout=5.0)
                health["windows"][name] = "healthy"
            except Exception as e:
                health["windows"][name] = f"unhealthy: {e}"
                health["orchestrator"] = "degraded"

        return health
