"""
Weighted Consensus Algorithm for PCO

Based on research: Models with higher accuracy on similar past tasks
get higher reputation weights in future decisions.

Decision_Score = Σ(confidence_i × reputation_weight_i) / n

Where:
- confidence_i: Self-reported confidence from each window (0-1)
- reputation_weight_i: Historical accuracy weight (0-1, starts at 0.5)
- n: Number of participating windows
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import json
from pathlib import Path


class TaskType(Enum):
    CODE = "code"
    REASONING = "reasoning"
    FACTUAL = "factual"
    CREATIVE = "creative"
    GENERAL = "general"


@dataclass
class WindowOutput:
    """Output from a single window with confidence metadata."""
    window_name: str
    content: str
    confidence: float  # 0-1, self-reported by window
    task_type: TaskType
    reasoning: Optional[str] = None
    errors_found: Optional[List[str]] = None

    def to_dict(self) -> dict:
        return {
            "window_name": self.window_name,
            "content": self.content,
            "confidence": self.confidence,
            "task_type": self.task_type.value,
            "reasoning": self.reasoning,
            "errors_found": self.errors_found,
        }


@dataclass
class ConsensusResult:
    """Result of weighted consensus calculation."""
    decision_score: float
    consensus_reached: bool
    winning_content: str
    dissenting_windows: List[str]
    confidence_breakdown: Dict[str, float]

    @property
    def has_strong_consensus(self) -> bool:
        """True if decision_score > 0.8 and no dissent."""
        return self.decision_score > 0.8 and len(self.dissenting_windows) == 0


class ReputationTracker:
    """
    Tracks historical accuracy of each window by task type.

    Reputation increases when a window's output is selected
    and decreases when it's overridden.
    """

    DEFAULT_WEIGHT = 0.5
    LEARNING_RATE = 0.1
    MIN_WEIGHT = 0.1
    MAX_WEIGHT = 0.95

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("data/reputation.json")
        self._weights: Dict[str, Dict[str, float]] = {}
        self._load()

    def _load(self):
        """Load reputation weights from storage."""
        if self.storage_path.exists():
            try:
                self._weights = json.loads(self.storage_path.read_text())
            except (json.JSONDecodeError, IOError):
                self._weights = {}
        else:
            self._weights = {}

    def _save(self):
        """Persist reputation weights."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(json.dumps(self._weights, indent=2))

    def get_weight(self, window_name: str, task_type: TaskType) -> float:
        """Get reputation weight for a window on a task type."""
        window_weights = self._weights.get(window_name, {})
        return window_weights.get(task_type.value, self.DEFAULT_WEIGHT)

    def update_weight(self, window_name: str, task_type: TaskType, was_selected: bool):
        """
        Update reputation based on whether this window's output was selected.

        Args:
            window_name: The window being updated
            task_type: Type of task
            was_selected: True if this window's output was used in final response
        """
        if window_name not in self._weights:
            self._weights[window_name] = {}

        current = self._weights[window_name].get(task_type.value, self.DEFAULT_WEIGHT)

        if was_selected:
            # Increase weight
            new_weight = current + self.LEARNING_RATE * (1 - current)
        else:
            # Decrease weight
            new_weight = current - self.LEARNING_RATE * current

        # Clamp to valid range
        self._weights[window_name][task_type.value] = max(
            self.MIN_WEIGHT,
            min(self.MAX_WEIGHT, new_weight)
        )

        self._save()

    def get_all_weights(self) -> Dict[str, Dict[str, float]]:
        """Get all reputation weights for debugging/monitoring."""
        return self._weights.copy()


class WeightedConsensus:
    """
    Implements weighted consensus algorithm for multi-model synthesis.

    The algorithm:
    1. Collect outputs with confidence scores from all windows
    2. Weight each output by (confidence × reputation_weight)
    3. Calculate decision score
    4. If score > threshold, we have consensus
    5. If not, trigger debate round (MAD protocol)
    """

    CONSENSUS_THRESHOLD = 0.7
    STRONG_CONSENSUS_THRESHOLD = 0.85

    def __init__(self, reputation_tracker: Optional[ReputationTracker] = None):
        self.reputation = reputation_tracker or ReputationTracker()

    def calculate_consensus(
        self,
        outputs: List[WindowOutput],
        task_type: TaskType
    ) -> ConsensusResult:
        """
        Calculate weighted consensus from multiple window outputs.

        Args:
            outputs: List of outputs from parallel windows
            task_type: The type of task being evaluated

        Returns:
            ConsensusResult with decision score and winning content
        """
        if not outputs:
            return ConsensusResult(
                decision_score=0.0,
                consensus_reached=False,
                winning_content="",
                dissenting_windows=[],
                confidence_breakdown={},
            )

        # Calculate weighted scores
        weighted_scores: Dict[str, float] = {}
        total_weight = 0.0

        for output in outputs:
            reputation_weight = self.reputation.get_weight(
                output.window_name,
                task_type
            )
            weighted_score = output.confidence * reputation_weight
            weighted_scores[output.window_name] = weighted_score
            total_weight += weighted_score

        # Normalize and find winner
        if total_weight == 0:
            total_weight = 1.0  # Avoid division by zero

        normalized_scores = {
            name: score / total_weight
            for name, score in weighted_scores.items()
        }

        # Decision score is the max normalized score
        # (could also be entropy-based or other metrics)
        decision_score = max(normalized_scores.values()) if normalized_scores else 0.0

        # Find winning window
        winner_name = max(normalized_scores.keys(), key=lambda k: normalized_scores[k])
        winner_output = next(o for o in outputs if o.window_name == winner_name)

        # Find dissenters (windows with significantly lower confidence in the winner)
        avg_score = sum(normalized_scores.values()) / len(normalized_scores)
        dissenting = [
            name for name, score in normalized_scores.items()
            if score < avg_score * 0.7 and name != winner_name
        ]

        return ConsensusResult(
            decision_score=decision_score,
            consensus_reached=decision_score >= self.CONSENSUS_THRESHOLD,
            winning_content=winner_output.content,
            dissenting_windows=dissenting,
            confidence_breakdown=normalized_scores,
        )

    def update_reputation_from_result(
        self,
        outputs: List[WindowOutput],
        selected_window: str,
        task_type: TaskType
    ):
        """
        Update reputation weights after synthesis completes.

        Called by the synthesizer after determining which window's
        output was most used in the final response.
        """
        for output in outputs:
            was_selected = output.window_name == selected_window
            self.reputation.update_weight(
                output.window_name,
                task_type,
                was_selected
            )


class DebateRound:
    """
    Implements Multi-Agent Debate (MAD) protocol when consensus fails.

    Process:
    1. Present conflicting outputs to all windows
    2. Each window critiques others' outputs
    3. Windows can revise their outputs based on critiques
    4. Re-run consensus calculation
    """

    MAX_ROUNDS = 3

    def __init__(self, consensus: WeightedConsensus):
        self.consensus = consensus
        self.round_history: List[ConsensusResult] = []

    async def run_debate(
        self,
        outputs: List[WindowOutput],
        task_type: TaskType,
        debate_callback  # async func(outputs) -> List[WindowOutput]
    ) -> ConsensusResult:
        """
        Run debate rounds until consensus or max rounds reached.

        Args:
            outputs: Initial conflicting outputs
            task_type: Type of task
            debate_callback: Async function that runs one debate round
                           Takes outputs, returns revised outputs

        Returns:
            Final ConsensusResult after debate
        """
        current_outputs = outputs

        for round_num in range(self.MAX_ROUNDS):
            # Check if we have consensus
            result = self.consensus.calculate_consensus(current_outputs, task_type)
            self.round_history.append(result)

            if result.consensus_reached:
                return result

            # No consensus - run debate round
            current_outputs = await debate_callback(current_outputs)

        # Max rounds reached - return best effort
        return self.consensus.calculate_consensus(current_outputs, task_type)

    def get_debate_history(self) -> List[dict]:
        """Get history of consensus attempts for debugging."""
        return [
            {
                "round": i + 1,
                "decision_score": r.decision_score,
                "consensus_reached": r.consensus_reached,
                "dissenting_windows": r.dissenting_windows,
            }
            for i, r in enumerate(self.round_history)
        ]
