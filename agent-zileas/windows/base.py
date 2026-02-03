"""
Base Window Interface for PCO

All specialized windows (Verifier, Coder, Reasoner, Synthesizer)
inherit from this base class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import logging

# Import from core
import sys
sys.path.insert(0, '..')
from core.consensus import WindowOutput, TaskType

logger = logging.getLogger(__name__)


@dataclass
class WindowConfig:
    """Configuration for a window."""
    name: str
    model_name: str
    provider: str = "ollama"
    temperature: float = 0.5
    max_tokens: int = 4096
    timeout: float = 60.0
    system_prompt: Optional[str] = None


@dataclass
class ProcessingMetrics:
    """Metrics for a single processing operation."""
    start_time: datetime
    end_time: Optional[datetime] = None
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: Optional[float] = None


class BaseWindow(ABC):
    """
    Abstract base class for all PCO windows.

    Each window represents a specialized AI model with a specific role:
    - Verifier: Error detection and fact-checking
    - Coder: Code generation
    - Reasoner: Step-by-step analysis
    - Synthesizer: Output combination

    Subclasses must implement:
    - process(): Main processing logic
    - get_system_prompt(): Window-specific system prompt
    """

    def __init__(self, config: WindowConfig, model: Optional[Any] = None):
        """
        Initialize the window.

        Args:
            config: Window configuration
            model: LLM model instance (optional, for testing)
        """
        self.config = config
        self.model = model
        self.name = config.name

        # Metrics tracking
        self._request_count = 0
        self._total_latency_ms = 0.0
        self._error_count = 0

    @abstractmethod
    async def process(self, request: Any) -> WindowOutput:
        """
        Process a user request.

        Args:
            request: The user request to process

        Returns:
            WindowOutput with content and confidence
        """
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this window.

        Returns:
            System prompt string
        """
        pass

    async def debate(
        self,
        request: Any,
        other_outputs: List[WindowOutput],
        debate_prompt: str,
    ) -> WindowOutput:
        """
        Participate in a debate round.

        Default implementation: re-process with other outputs as context.
        Subclasses can override for specialized debate behavior.

        Args:
            request: Original user request
            other_outputs: Outputs from other windows
            debate_prompt: The debate context

        Returns:
            Revised WindowOutput
        """
        # Default: call process with debate context
        return await self.process(request)

    async def ping(self) -> bool:
        """
        Health check for the window.

        Returns:
            True if healthy, raises exception otherwise
        """
        if self.model and hasattr(self.model, 'ping'):
            return await self.model.ping()
        return True

    def get_metrics(self) -> Dict[str, Any]:
        """Get window metrics."""
        avg_latency = (
            self._total_latency_ms / self._request_count
            if self._request_count > 0 else 0
        )
        return {
            "name": self.name,
            "request_count": self._request_count,
            "error_count": self._error_count,
            "average_latency_ms": avg_latency,
            "error_rate": (
                self._error_count / self._request_count
                if self._request_count > 0 else 0
            ),
        }

    async def _call_model(
        self,
        system: str,
        user: str,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Call the underlying model.

        Args:
            system: System prompt
            user: User message
            temperature: Optional temperature override

        Returns:
            Model response string
        """
        if not self.model:
            raise RuntimeError(f"No model configured for window {self.name}")

        return await self.model.generate(
            system=system,
            user=user,
            temperature=temperature or self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

    def _parse_confidence(self, content: str) -> float:
        """
        Extract confidence score from model output.

        Looks for patterns like:
        - CONFIDENCE: 0.85
        - Confidence: 8/10
        - [confidence: high]
        """
        import re

        # Pattern 1: CONFIDENCE: 0.XX
        match = re.search(r'confidence[:\s]+([0-9.]+)', content, re.IGNORECASE)
        if match:
            try:
                value = float(match.group(1))
                if value <= 1.0:
                    return value
                elif value <= 10:
                    return value / 10.0
            except ValueError:
                pass

        # Pattern 2: X/10
        match = re.search(r'(\d+)\s*/\s*10', content)
        if match:
            try:
                return int(match.group(1)) / 10.0
            except ValueError:
                pass

        # Pattern 3: high/medium/low
        if re.search(r'\bhigh\b', content, re.IGNORECASE):
            return 0.85
        elif re.search(r'\bmedium\b', content, re.IGNORECASE):
            return 0.65
        elif re.search(r'\blow\b', content, re.IGNORECASE):
            return 0.45

        # Default
        return 0.7


class MockWindow(BaseWindow):
    """
    Mock window for testing.

    Returns predefined responses for testing the orchestrator.
    """

    def __init__(
        self,
        name: str,
        response: str = "Mock response",
        confidence: float = 0.8,
        delay: float = 0.1,
        task_type: TaskType = TaskType.GENERAL,
    ):
        config = WindowConfig(name=name, model_name="mock")
        super().__init__(config, model=None)
        self._response = response
        self._confidence = confidence
        self._delay = delay
        self._task_type = task_type

    async def process(self, request: Any) -> WindowOutput:
        # Simulate processing time
        await asyncio.sleep(self._delay)

        self._request_count += 1

        return WindowOutput(
            window_name=self.name,
            content=self._response,
            confidence=self._confidence,
            task_type=self._task_type,
        )

    def get_system_prompt(self) -> str:
        return f"Mock system prompt for {self.name}"


class OllamaWindow(BaseWindow):
    """
    Window implementation using Ollama as the backend.

    Connects to a local Ollama instance to run models.
    """

    def __init__(self, config: WindowConfig, base_url: str = "http://localhost:11434"):
        super().__init__(config, model=None)
        self.base_url = base_url
        self._session = None

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession()

    async def _call_ollama(self, system: str, user: str) -> str:
        """Call Ollama API."""
        await self._ensure_session()

        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.config.model_name,
            "prompt": user,
            "system": system,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            }
        }

        try:
            async with self._session.post(url, json=payload, timeout=self.config.timeout) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Ollama returned {resp.status}")
                data = await resp.json()
                return data.get("response", "")
        except asyncio.TimeoutError:
            raise TimeoutError(f"Ollama request timed out after {self.config.timeout}s")

    async def process(self, request: Any) -> WindowOutput:
        """Process request through Ollama."""
        import time
        start = time.time()
        self._request_count += 1

        try:
            content = request.content if hasattr(request, 'content') else str(request)

            response = await self._call_ollama(
                system=self.get_system_prompt(),
                user=content,
            )

            latency = (time.time() - start) * 1000
            self._total_latency_ms += latency

            confidence = self._parse_confidence(response)

            return WindowOutput(
                window_name=self.name,
                content=response,
                confidence=confidence,
                task_type=self._get_task_type(),
            )

        except Exception as e:
            self._error_count += 1
            logger.error(f"Window {self.name} error: {e}")
            return WindowOutput(
                window_name=self.name,
                content="",
                confidence=0.0,
                task_type=self._get_task_type(),
            )

    def get_system_prompt(self) -> str:
        """Override in subclasses."""
        return self.config.system_prompt or "You are a helpful assistant."

    def _get_task_type(self) -> TaskType:
        """Get task type for this window."""
        return TaskType.GENERAL

    async def ping(self) -> bool:
        """Check if Ollama is available."""
        await self._ensure_session()
        try:
            async with self._session.get(f"{self.base_url}/api/tags", timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    async def close(self):
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None
