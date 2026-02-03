"""
Adaptive Router for PCO

Classifies requests and determines optimal routing:
- Which windows to activate
- What routing mode to use
- Timeout settings
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from enum import Enum
import re
import logging

from .consensus import TaskType

logger = logging.getLogger(__name__)


class RoutingMode(Enum):
    """Routing modes with different speed/accuracy tradeoffs."""
    FAST = "fast"           # Quick response, minimal verification
    BALANCED = "balanced"   # Normal processing
    THOROUGH = "thorough"   # Full verification and debate

    @property
    def max_windows(self) -> int:
        return {
            RoutingMode.FAST: 2,
            RoutingMode.BALANCED: 3,
            RoutingMode.THOROUGH: 4,
        }[self]

    @property
    def timeout(self) -> float:
        return {
            RoutingMode.FAST: 30.0,
            RoutingMode.BALANCED: 60.0,
            RoutingMode.THOROUGH: 120.0,
        }[self]

    @property
    def debate_rounds(self) -> int:
        return {
            RoutingMode.FAST: 0,
            RoutingMode.BALANCED: 1,
            RoutingMode.THOROUGH: 3,
        }[self]

    @property
    def consensus_threshold(self) -> float:
        return {
            RoutingMode.FAST: 0.6,
            RoutingMode.BALANCED: 0.7,
            RoutingMode.THOROUGH: 0.8,
        }[self]


class RequestComplexity(Enum):
    """Complexity levels for request classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class RoutingDecision:
    """Result of routing decision."""
    mode: RoutingMode
    windows: List[str]
    task_type: TaskType
    timeout: float
    debate_rounds: int
    consensus_threshold: float
    reasoning: str  # Why this routing was chosen


@dataclass
class RoutingConfig:
    """Configuration for routing rules."""
    # Required windows for each task type
    required_windows: Dict[str, List[str]] = field(default_factory=lambda: {
        "code": ["coder", "verifier"],
        "reasoning": ["reasoner", "verifier"],
        "factual": ["verifier"],
        "creative": ["coder"],
        "general": ["verifier"],
    })

    # Optional windows for each task type
    optional_windows: Dict[str, List[str]] = field(default_factory=lambda: {
        "code": ["reasoner"],
        "reasoning": ["coder"],
        "factual": ["reasoner"],
        "creative": ["verifier", "reasoner"],
        "general": ["coder", "reasoner"],
    })

    # Default mode for each task type
    default_modes: Dict[str, RoutingMode] = field(default_factory=lambda: {
        "code": RoutingMode.BALANCED,
        "reasoning": RoutingMode.THOROUGH,
        "factual": RoutingMode.FAST,
        "creative": RoutingMode.BALANCED,
        "general": RoutingMode.BALANCED,
    })


class RequestClassifier:
    """
    Classifies requests by type and complexity.

    Uses keyword matching and heuristics to determine:
    - Task type (code, reasoning, factual, etc.)
    - Complexity (low, medium, high)
    """

    # Keywords for task type classification
    CODE_KEYWORDS = {
        "code", "function", "class", "implement", "write", "debug", "fix",
        "python", "javascript", "typescript", "java", "rust", "go",
        "program", "script", "algorithm", "api", "database", "sql",
        "frontend", "backend", "react", "vue", "node", "django",
    }

    REASONING_KEYWORDS = {
        "why", "how", "explain", "analyze", "compare", "evaluate",
        "reason", "think", "consider", "logic", "argument", "proof",
        "step by step", "break down", "understand", "deduce",
    }

    FACTUAL_KEYWORDS = {
        "what is", "who is", "when", "where", "define", "meaning",
        "fact", "information", "tell me about", "describe",
    }

    CREATIVE_KEYWORDS = {
        "write", "story", "poem", "essay", "creative", "imagine",
        "invent", "design", "brainstorm", "ideas",
    }

    # Complexity indicators
    HIGH_COMPLEXITY_PATTERNS = [
        r"multiple.*files?",
        r"entire.*system",
        r"architecture",
        r"full.*implementation",
        r"complex",
        r"comprehensive",
        r"complete.*solution",
    ]

    LOW_COMPLEXITY_PATTERNS = [
        r"simple",
        r"quick",
        r"just",
        r"only",
        r"basic",
        r"single",
    ]

    def classify(self, request: Any) -> tuple[TaskType, RequestComplexity]:
        """
        Classify a request by type and complexity.

        Args:
            request: The user request (expects .content attribute)

        Returns:
            Tuple of (TaskType, RequestComplexity)
        """
        content = request.content if hasattr(request, 'content') else str(request)
        content_lower = content.lower()
        words = set(content_lower.split())

        # Determine task type
        task_type = self._classify_task_type(content_lower, words)

        # Determine complexity
        complexity = self._classify_complexity(content_lower, content)

        return task_type, complexity

    def _classify_task_type(self, content_lower: str, words: Set[str]) -> TaskType:
        """Classify the task type based on keywords."""
        # Count keyword matches
        code_score = len(words & self.CODE_KEYWORDS)
        reasoning_score = len(words & self.REASONING_KEYWORDS)
        factual_score = len(words & self.FACTUAL_KEYWORDS)
        creative_score = len(words & self.CREATIVE_KEYWORDS)

        # Check for code patterns
        if re.search(r"```|def |class |function |import |from |const |let |var ", content_lower):
            code_score += 5

        # Check for question patterns
        if content_lower.startswith(("what", "who", "when", "where", "how", "why")):
            if content_lower.startswith(("how", "why")):
                reasoning_score += 2
            else:
                factual_score += 2

        # Determine winner
        scores = {
            TaskType.CODE: code_score,
            TaskType.REASONING: reasoning_score,
            TaskType.FACTUAL: factual_score,
            TaskType.CREATIVE: creative_score,
        }

        max_score = max(scores.values())
        if max_score == 0:
            return TaskType.GENERAL

        return max(scores, key=scores.get)

    def _classify_complexity(self, content_lower: str, content: str) -> RequestComplexity:
        """Classify complexity based on patterns and length."""
        # Check for high complexity patterns
        for pattern in self.HIGH_COMPLEXITY_PATTERNS:
            if re.search(pattern, content_lower):
                return RequestComplexity.HIGH

        # Check for low complexity patterns
        for pattern in self.LOW_COMPLEXITY_PATTERNS:
            if re.search(pattern, content_lower):
                return RequestComplexity.LOW

        # Use length as a heuristic
        if len(content) > 500:
            return RequestComplexity.HIGH
        elif len(content) < 100:
            return RequestComplexity.LOW

        return RequestComplexity.MEDIUM


class AdaptiveRouter:
    """
    Routes requests to appropriate windows based on classification.

    Features:
    - Task type classification
    - Complexity assessment
    - Mode selection (fast/balanced/thorough)
    - Window selection based on availability
    """

    def __init__(
        self,
        config: Optional[RoutingConfig] = None,
        classifier: Optional[RequestClassifier] = None,
        available_windows: Optional[List[str]] = None,
    ):
        """
        Initialize the router.

        Args:
            config: Routing configuration
            classifier: Request classifier
            available_windows: List of available window names
        """
        self.config = config or RoutingConfig()
        self.classifier = classifier or RequestClassifier()
        self.available_windows = set(available_windows or [
            "verifier", "coder", "reasoner", "synthesizer"
        ])

    def classify_and_route(self, request: Any) -> RoutingDecision:
        """
        Classify a request and determine routing.

        Args:
            request: The user request

        Returns:
            RoutingDecision with windows, mode, and settings
        """
        # Get user hint if provided
        user_hint = None
        if hasattr(request, 'routing_hint') and request.routing_hint:
            user_hint = request.routing_hint.lower()

        # Classify request
        task_type, complexity = self.classifier.classify(request)

        # Determine mode
        mode = self._determine_mode(task_type, complexity, user_hint)

        # Select windows
        windows = self._select_windows(task_type, mode)

        # Build reasoning
        reasoning = self._build_reasoning(task_type, complexity, mode, windows, user_hint)

        return RoutingDecision(
            mode=mode,
            windows=windows,
            task_type=task_type,
            timeout=mode.timeout,
            debate_rounds=mode.debate_rounds,
            consensus_threshold=mode.consensus_threshold,
            reasoning=reasoning,
        )

    def _determine_mode(
        self,
        task_type: TaskType,
        complexity: RequestComplexity,
        user_hint: Optional[str],
    ) -> RoutingMode:
        """Determine routing mode based on factors."""
        # User hint takes precedence
        if user_hint:
            if user_hint in ("fast", "quick", "simple"):
                return RoutingMode.FAST
            elif user_hint in ("thorough", "careful", "detailed"):
                return RoutingMode.THOROUGH

        # Complexity-based selection
        if complexity == RequestComplexity.HIGH:
            return RoutingMode.THOROUGH
        elif complexity == RequestComplexity.LOW:
            return RoutingMode.FAST

        # Fall back to task type default
        return self.config.default_modes.get(task_type.value, RoutingMode.BALANCED)

    def _select_windows(self, task_type: TaskType, mode: RoutingMode) -> List[str]:
        """Select windows based on task type and mode."""
        # Get required and optional windows for this task type
        required = self.config.required_windows.get(task_type.value, ["verifier"])
        optional = self.config.optional_windows.get(task_type.value, [])

        # Filter to available windows
        required = [w for w in required if w in self.available_windows]
        optional = [w for w in optional if w in self.available_windows]

        # Start with required windows
        windows = list(required)

        # Add optional windows up to mode limit
        for window in optional:
            if len(windows) >= mode.max_windows:
                break
            if window not in windows:
                windows.append(window)

        # Always include synthesizer if available and not already included
        if "synthesizer" in self.available_windows and "synthesizer" not in windows:
            windows.append("synthesizer")

        return windows

    def _build_reasoning(
        self,
        task_type: TaskType,
        complexity: RequestComplexity,
        mode: RoutingMode,
        windows: List[str],
        user_hint: Optional[str],
    ) -> str:
        """Build human-readable reasoning for the routing decision."""
        parts = [
            f"Task type: {task_type.value}",
            f"Complexity: {complexity.value}",
            f"Mode: {mode.name}",
        ]

        if user_hint:
            parts.append(f"User hint: {user_hint}")

        parts.append(f"Selected windows: {', '.join(windows)}")
        parts.append(f"Timeout: {mode.timeout}s")
        parts.append(f"Max debate rounds: {mode.debate_rounds}")

        return " | ".join(parts)

    def update_available_windows(self, windows: List[str]):
        """Update the list of available windows."""
        self.available_windows = set(windows)

    def force_mode(self, mode: RoutingMode):
        """Force a specific mode for all requests (for testing)."""
        self._forced_mode = mode

    def clear_forced_mode(self):
        """Clear forced mode."""
        self._forced_mode = None


class RoutingOverrides:
    """
    Handles routing overrides for specific scenarios.

    Allows operators to force specific routing for:
    - Testing
    - Specific users
    - Specific request patterns
    """

    def __init__(self):
        self._pattern_overrides: List[tuple[str, RoutingDecision]] = []
        self._user_overrides: Dict[str, RoutingMode] = {}

    def add_pattern_override(self, pattern: str, decision: RoutingDecision):
        """Add a pattern-based override."""
        self._pattern_overrides.append((pattern, decision))

    def add_user_override(self, user_id: str, mode: RoutingMode):
        """Add a user-based mode override."""
        self._user_overrides[user_id] = mode

    def check_overrides(self, request: Any) -> Optional[RoutingDecision]:
        """Check if any overrides apply to this request."""
        content = request.content if hasattr(request, 'content') else str(request)
        user_id = request.user_id if hasattr(request, 'user_id') else None

        # Check pattern overrides
        for pattern, decision in self._pattern_overrides:
            if re.search(pattern, content, re.IGNORECASE):
                return decision

        # Check user overrides (return None - let router use the mode)
        # This is handled separately in classify_and_route

        return None

    def get_user_mode(self, user_id: Optional[str]) -> Optional[RoutingMode]:
        """Get mode override for a user."""
        if user_id and user_id in self._user_overrides:
            return self._user_overrides[user_id]
        return None
