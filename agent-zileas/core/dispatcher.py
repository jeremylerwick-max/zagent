"""
Parallel Dispatcher for PCO

Handles dispatching requests to multiple windows in parallel.
Manages timeouts, retries, and failure handling.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Awaitable
from enum import Enum
from datetime import datetime
import logging

from .consensus import WindowOutput, TaskType

logger = logging.getLogger(__name__)


class DispatchStatus(Enum):
    """Status of a dispatch operation."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    TIMEOUT = "timeout"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WindowTask:
    """Represents a task dispatched to a window."""
    window_name: str
    task: asyncio.Task
    start_time: float
    status: DispatchStatus = DispatchStatus.PENDING
    result: Optional[WindowOutput] = None
    error: Optional[str] = None
    latency_ms: Optional[float] = None


@dataclass
class DispatchResult:
    """Result of dispatching to all windows."""
    tasks: List[WindowTask]
    total_latency_ms: float
    all_complete: bool

    @property
    def successful_tasks(self) -> List[WindowTask]:
        return [t for t in self.tasks if t.status == DispatchStatus.COMPLETE]

    @property
    def failed_tasks(self) -> List[WindowTask]:
        return [t for t in self.tasks if t.status in (
            DispatchStatus.TIMEOUT, DispatchStatus.FAILED, DispatchStatus.CANCELLED
        )]

    @property
    def outputs(self) -> List[WindowOutput]:
        return [t.result for t in self.successful_tasks if t.result]


class Dispatcher:
    """
    Dispatches requests to parallel windows.

    Features:
    - Parallel execution with asyncio.gather
    - Per-window timeout handling
    - Graceful failure handling
    - Progress tracking
    - Cancellation support
    """

    def __init__(
        self,
        windows: Dict[str, Any],
        default_timeout: float = 60.0,
        max_retries: int = 1,
    ):
        """
        Initialize the dispatcher.

        Args:
            windows: Dict of window_name -> Window instance
            default_timeout: Default timeout per window in seconds
            max_retries: Maximum retries for failed windows
        """
        self.windows = windows
        self.default_timeout = default_timeout
        self.max_retries = max_retries

        # Track active dispatches
        self._active_dispatches: Dict[str, List[WindowTask]] = {}

    async def dispatch(
        self,
        request: Any,  # UserRequest
        windows: List[str],
        timeout: Optional[float] = None,
        on_progress: Optional[Callable[[str, DispatchStatus], Awaitable[None]]] = None,
    ) -> DispatchResult:
        """
        Dispatch a request to multiple windows in parallel.

        Args:
            request: The user request to process
            windows: List of window names to dispatch to
            timeout: Timeout per window (uses default if not specified)
            on_progress: Optional callback for progress updates

        Returns:
            DispatchResult with all task results
        """
        timeout = timeout or self.default_timeout
        start_time = time.time()
        dispatch_id = request.id if hasattr(request, 'id') else str(id(request))

        # Create tasks for each window
        tasks: List[WindowTask] = []

        for window_name in windows:
            if window_name not in self.windows:
                logger.warning(f"Window '{window_name}' not found, skipping")
                continue

            window = self.windows[window_name]

            # Create the async task
            task = asyncio.create_task(
                self._execute_window(
                    window=window,
                    window_name=window_name,
                    request=request,
                    timeout=timeout,
                )
            )

            window_task = WindowTask(
                window_name=window_name,
                task=task,
                start_time=time.time(),
                status=DispatchStatus.RUNNING,
            )
            tasks.append(window_task)

        # Track this dispatch
        self._active_dispatches[dispatch_id] = tasks

        try:
            # Wait for all tasks with overall timeout
            overall_timeout = timeout * 1.5  # Allow some buffer
            done, pending = await asyncio.wait(
                [t.task for t in tasks],
                timeout=overall_timeout,
                return_when=asyncio.ALL_COMPLETED,
            )

            # Process results
            for window_task in tasks:
                if window_task.task in done:
                    try:
                        result = window_task.task.result()
                        window_task.result = result
                        window_task.status = DispatchStatus.COMPLETE
                        window_task.latency_ms = (time.time() - window_task.start_time) * 1000
                    except asyncio.TimeoutError:
                        window_task.status = DispatchStatus.TIMEOUT
                        window_task.error = f"Timeout after {timeout}s"
                    except Exception as e:
                        window_task.status = DispatchStatus.FAILED
                        window_task.error = str(e)
                        logger.error(f"Window {window_task.window_name} failed: {e}")
                else:
                    # Task still pending - cancel it
                    window_task.task.cancel()
                    window_task.status = DispatchStatus.TIMEOUT
                    window_task.error = f"Overall timeout after {overall_timeout}s"

                # Progress callback
                if on_progress:
                    try:
                        await on_progress(window_task.window_name, window_task.status)
                    except Exception as e:
                        logger.warning(f"Progress callback failed: {e}")

            total_latency = (time.time() - start_time) * 1000

            return DispatchResult(
                tasks=tasks,
                total_latency_ms=total_latency,
                all_complete=all(t.status == DispatchStatus.COMPLETE for t in tasks),
            )

        finally:
            # Cleanup
            del self._active_dispatches[dispatch_id]

    async def dispatch_sequential(
        self,
        request: Any,
        windows: List[str],
        timeout: Optional[float] = None,
        stop_on_failure: bool = False,
    ) -> DispatchResult:
        """
        Dispatch to windows sequentially (for dependent operations).

        Args:
            request: The user request
            windows: List of window names in execution order
            timeout: Timeout per window
            stop_on_failure: Stop if any window fails

        Returns:
            DispatchResult with all task results
        """
        timeout = timeout or self.default_timeout
        start_time = time.time()
        tasks: List[WindowTask] = []

        for window_name in windows:
            if window_name not in self.windows:
                continue

            window = self.windows[window_name]
            task_start = time.time()

            try:
                result = await asyncio.wait_for(
                    window.process(request),
                    timeout=timeout,
                )

                window_task = WindowTask(
                    window_name=window_name,
                    task=asyncio.create_task(asyncio.sleep(0)),  # Dummy
                    start_time=task_start,
                    status=DispatchStatus.COMPLETE,
                    result=result,
                    latency_ms=(time.time() - task_start) * 1000,
                )
                tasks.append(window_task)

            except asyncio.TimeoutError:
                window_task = WindowTask(
                    window_name=window_name,
                    task=asyncio.create_task(asyncio.sleep(0)),
                    start_time=task_start,
                    status=DispatchStatus.TIMEOUT,
                    error=f"Timeout after {timeout}s",
                )
                tasks.append(window_task)

                if stop_on_failure:
                    break

            except Exception as e:
                window_task = WindowTask(
                    window_name=window_name,
                    task=asyncio.create_task(asyncio.sleep(0)),
                    start_time=task_start,
                    status=DispatchStatus.FAILED,
                    error=str(e),
                )
                tasks.append(window_task)

                if stop_on_failure:
                    break

        return DispatchResult(
            tasks=tasks,
            total_latency_ms=(time.time() - start_time) * 1000,
            all_complete=all(t.status == DispatchStatus.COMPLETE for t in tasks),
        )

    async def _execute_window(
        self,
        window: Any,
        window_name: str,
        request: Any,
        timeout: float,
    ) -> WindowOutput:
        """
        Execute a single window with timeout and error handling.

        Returns WindowOutput even on failure (with confidence=0).
        """
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                window.process(request),
                timeout=timeout,
            )

            # Ensure we have a valid WindowOutput
            if isinstance(result, WindowOutput):
                return result
            elif isinstance(result, dict):
                return WindowOutput(
                    window_name=window_name,
                    content=result.get("content", str(result)),
                    confidence=result.get("confidence", 0.5),
                    task_type=TaskType(result.get("task_type", "general")),
                )
            else:
                return WindowOutput(
                    window_name=window_name,
                    content=str(result),
                    confidence=0.5,
                    task_type=TaskType.GENERAL,
                )

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

    async def cancel_dispatch(self, dispatch_id: str) -> bool:
        """
        Cancel an active dispatch.

        Args:
            dispatch_id: The dispatch to cancel (usually request.id)

        Returns:
            True if cancelled, False if not found
        """
        if dispatch_id not in self._active_dispatches:
            return False

        tasks = self._active_dispatches[dispatch_id]
        for window_task in tasks:
            if not window_task.task.done():
                window_task.task.cancel()
                window_task.status = DispatchStatus.CANCELLED

        return True

    def get_active_dispatches(self) -> Dict[str, List[str]]:
        """Get currently active dispatches and their windows."""
        return {
            dispatch_id: [t.window_name for t in tasks]
            for dispatch_id, tasks in self._active_dispatches.items()
        }


class BatchDispatcher:
    """
    Handles batch dispatching for multiple requests.

    Useful for scenarios like processing multiple files
    or running the same request through different configurations.
    """

    def __init__(self, dispatcher: Dispatcher, max_concurrent: int = 5):
        """
        Initialize batch dispatcher.

        Args:
            dispatcher: The underlying dispatcher
            max_concurrent: Maximum concurrent dispatches
        """
        self.dispatcher = dispatcher
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def dispatch_batch(
        self,
        requests: List[Any],
        windows: List[str],
        timeout: Optional[float] = None,
    ) -> List[DispatchResult]:
        """
        Dispatch multiple requests in parallel with concurrency control.

        Args:
            requests: List of requests to process
            windows: Windows to use for each request
            timeout: Timeout per request

        Returns:
            List of DispatchResult for each request
        """
        async def dispatch_one(request):
            async with self._semaphore:
                return await self.dispatcher.dispatch(request, windows, timeout)

        results = await asyncio.gather(
            *[dispatch_one(req) for req in requests],
            return_exceptions=True,
        )

        # Convert exceptions to failed results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(DispatchResult(
                    tasks=[],
                    total_latency_ms=0,
                    all_complete=False,
                ))
            else:
                processed_results.append(result)

        return processed_results
