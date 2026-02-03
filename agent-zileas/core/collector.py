"""
Output Collector for PCO

Gathers outputs from parallel windows, validates them,
and prepares them for consensus calculation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from .consensus import WindowOutput, TaskType
from .dispatcher import DispatchResult, DispatchStatus

logger = logging.getLogger(__name__)


@dataclass
class CollectedOutputs:
    """Collection of outputs from parallel windows."""
    valid_outputs: List[WindowOutput]
    failed_windows: List[str]
    timeout_windows: List[str]
    total_windows: int
    collection_time_ms: float

    @property
    def success_rate(self) -> float:
        """Percentage of windows that succeeded."""
        if self.total_windows == 0:
            return 0.0
        return len(self.valid_outputs) / self.total_windows

    @property
    def has_minimum_outputs(self) -> bool:
        """Check if we have at least one valid output."""
        return len(self.valid_outputs) > 0

    @property
    def has_consensus_quorum(self) -> bool:
        """Check if we have enough outputs for meaningful consensus."""
        return len(self.valid_outputs) >= 2

    def get_by_window(self, window_name: str) -> Optional[WindowOutput]:
        """Get output from a specific window."""
        for output in self.valid_outputs:
            if output.window_name == window_name:
                return output
        return None

    def get_highest_confidence(self) -> Optional[WindowOutput]:
        """Get the output with highest confidence."""
        if not self.valid_outputs:
            return None
        return max(self.valid_outputs, key=lambda o: o.confidence)


class Collector:
    """
    Collects and validates outputs from parallel windows.

    Responsibilities:
    - Extract outputs from dispatch results
    - Validate output format and content
    - Filter out invalid/empty outputs
    - Calculate collection statistics
    """

    def __init__(
        self,
        min_confidence: float = 0.0,
        require_content: bool = True,
    ):
        """
        Initialize the collector.

        Args:
            min_confidence: Minimum confidence to accept output
            require_content: Whether to require non-empty content
        """
        self.min_confidence = min_confidence
        self.require_content = require_content

    def collect(self, dispatch_result: DispatchResult) -> CollectedOutputs:
        """
        Collect outputs from a dispatch result.

        Args:
            dispatch_result: Result from Dispatcher.dispatch()

        Returns:
            CollectedOutputs with validated outputs
        """
        valid_outputs = []
        failed_windows = []
        timeout_windows = []

        for task in dispatch_result.tasks:
            if task.status == DispatchStatus.COMPLETE and task.result:
                # Validate the output
                if self._is_valid_output(task.result):
                    valid_outputs.append(task.result)
                else:
                    logger.warning(
                        f"Window {task.window_name} output invalid: "
                        f"confidence={task.result.confidence}, "
                        f"content_len={len(task.result.content)}"
                    )
                    failed_windows.append(task.window_name)

            elif task.status == DispatchStatus.TIMEOUT:
                timeout_windows.append(task.window_name)

            elif task.status in (DispatchStatus.FAILED, DispatchStatus.CANCELLED):
                failed_windows.append(task.window_name)

        return CollectedOutputs(
            valid_outputs=valid_outputs,
            failed_windows=failed_windows,
            timeout_windows=timeout_windows,
            total_windows=len(dispatch_result.tasks),
            collection_time_ms=dispatch_result.total_latency_ms,
        )

    def _is_valid_output(self, output: WindowOutput) -> bool:
        """Check if an output is valid for consensus."""
        # Check confidence threshold
        if output.confidence < self.min_confidence:
            return False

        # Check content requirement
        if self.require_content and not output.content.strip():
            return False

        return True

    def merge_outputs(
        self,
        primary: CollectedOutputs,
        secondary: CollectedOutputs,
    ) -> CollectedOutputs:
        """
        Merge two collections, preferring primary outputs.

        Useful when running retry/fallback dispatches.
        """
        # Get window names from primary
        primary_windows = {o.window_name for o in primary.valid_outputs}

        # Add secondary outputs that aren't in primary
        merged_outputs = list(primary.valid_outputs)
        for output in secondary.valid_outputs:
            if output.window_name not in primary_windows:
                merged_outputs.append(output)

        # Merge failed lists (deduplicate)
        all_failed = list(set(primary.failed_windows + secondary.failed_windows))
        all_timeout = list(set(primary.timeout_windows + secondary.timeout_windows))

        # Remove from failed if now in valid
        valid_names = {o.window_name for o in merged_outputs}
        all_failed = [w for w in all_failed if w not in valid_names]
        all_timeout = [w for w in all_timeout if w not in valid_names]

        return CollectedOutputs(
            valid_outputs=merged_outputs,
            failed_windows=all_failed,
            timeout_windows=all_timeout,
            total_windows=primary.total_windows,
            collection_time_ms=primary.collection_time_ms + secondary.collection_time_ms,
        )

    def filter_by_task_type(
        self,
        collected: CollectedOutputs,
        task_type: TaskType,
    ) -> CollectedOutputs:
        """
        Filter outputs to only those matching a task type.

        Useful for specialized processing.
        """
        filtered = [
            o for o in collected.valid_outputs
            if o.task_type == task_type
        ]

        return CollectedOutputs(
            valid_outputs=filtered,
            failed_windows=collected.failed_windows,
            timeout_windows=collected.timeout_windows,
            total_windows=collected.total_windows,
            collection_time_ms=collected.collection_time_ms,
        )

    def deduplicate_outputs(
        self,
        collected: CollectedOutputs,
        similarity_threshold: float = 0.9,
    ) -> CollectedOutputs:
        """
        Remove near-duplicate outputs, keeping highest confidence.

        Uses simple string similarity for now.
        """
        if len(collected.valid_outputs) <= 1:
            return collected

        unique_outputs = []
        seen_contents = []

        # Sort by confidence descending
        sorted_outputs = sorted(
            collected.valid_outputs,
            key=lambda o: o.confidence,
            reverse=True,
        )

        for output in sorted_outputs:
            is_duplicate = False
            for seen in seen_contents:
                if self._similarity(output.content, seen) >= similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_outputs.append(output)
                seen_contents.append(output.content)

        return CollectedOutputs(
            valid_outputs=unique_outputs,
            failed_windows=collected.failed_windows,
            timeout_windows=collected.timeout_windows,
            total_windows=collected.total_windows,
            collection_time_ms=collected.collection_time_ms,
        )

    def _similarity(self, s1: str, s2: str) -> float:
        """
        Calculate simple similarity between two strings.

        Uses character-level Jaccard similarity.
        """
        if not s1 or not s2:
            return 0.0

        # Convert to word sets
        set1 = set(s1.lower().split())
        set2 = set(s2.lower().split())

        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0


class OutputAggregator:
    """
    Aggregates outputs for specific use cases.

    Provides utilities for combining outputs in different ways:
    - Code concatenation
    - Reasoning chain building
    - Error list merging
    """

    @staticmethod
    def aggregate_code(outputs: List[WindowOutput]) -> str:
        """
        Aggregate code outputs, combining unique code blocks.
        """
        code_blocks = []

        for output in outputs:
            # Extract code from content
            content = output.content
            if "```" in content:
                # Extract code blocks
                parts = content.split("```")
                for i in range(1, len(parts), 2):
                    code = parts[i]
                    # Remove language identifier
                    if "\n" in code:
                        code = code.split("\n", 1)[1]
                    code_blocks.append(code.strip())
            else:
                code_blocks.append(content.strip())

        # Deduplicate
        unique_blocks = list(dict.fromkeys(code_blocks))

        return "\n\n".join(unique_blocks)

    @staticmethod
    def aggregate_errors(outputs: List[WindowOutput]) -> List[str]:
        """
        Aggregate error lists from verifier outputs.
        """
        all_errors = []

        for output in outputs:
            if output.errors_found:
                all_errors.extend(output.errors_found)

        # Deduplicate while preserving order
        return list(dict.fromkeys(all_errors))

    @staticmethod
    def build_reasoning_chain(outputs: List[WindowOutput]) -> str:
        """
        Build a reasoning chain from multiple outputs.
        """
        chain_parts = []

        for i, output in enumerate(outputs, 1):
            chain_parts.append(f"## Step {i}: {output.window_name.upper()}")
            chain_parts.append(output.content)
            chain_parts.append(f"*Confidence: {output.confidence:.2f}*")
            chain_parts.append("")

        return "\n".join(chain_parts)
