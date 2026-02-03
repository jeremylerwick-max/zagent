#!/usr/bin/env python3
"""
PCO Command Line Interface

A simple CLI for testing the Parallel Context Orchestrator.

Usage:
    python cli.py "Write a Python function to sort a list"
    python cli.py --mode thorough "Explain quantum computing"
    python cli.py --interactive
"""

import asyncio
import argparse
import sys
import time
from typing import Optional
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.orchestrator import ParallelOrchestrator, UserRequest, RequestStatus
from core.consensus import WeightedConsensus, TaskType
from core.context_hierarchy import SlidingContextHierarchy
from core.router import AdaptiveRouter, RoutingMode
from windows.base import MockWindow


def create_mock_orchestrator() -> ParallelOrchestrator:
    """Create an orchestrator with mock windows for testing."""
    windows = {
        "verifier": MockWindow(
            name="verifier",
            response="ERRORS_FOUND: None\nWARNINGS: Consider edge cases\nCONFIDENCE: 0.85",
            confidence=0.85,
            delay=0.5,
        ),
        "coder": MockWindow(
            name="coder",
            response="```python\ndef example():\n    return 'Hello World'\n```\nCONFIDENCE: 0.90",
            confidence=0.90,
            delay=0.8,
            task_type=TaskType.CODE,
        ),
        "reasoner": MockWindow(
            name="reasoner",
            response="UNDERSTANDING: The user wants...\nBREAKDOWN: 1. First step...\nCONFIDENCE: 0.80",
            confidence=0.80,
            delay=1.0,
            task_type=TaskType.REASONING,
        ),
        "synthesizer": MockWindow(
            name="synthesizer",
            response="Here is the synthesized response combining all window outputs.",
            confidence=0.95,
            delay=0.3,
        ),
    }

    return ParallelOrchestrator(
        windows=windows,
        router=AdaptiveRouter(available_windows=list(windows.keys())),
        consensus=WeightedConsensus(),
        context_hierarchy=SlidingContextHierarchy(),
    )


async def process_request(
    orchestrator: ParallelOrchestrator,
    content: str,
    mode: Optional[str] = None,
    streaming: bool = False,
) -> None:
    """Process a single request."""
    request = UserRequest.create(
        content=content,
        routing_hint=mode,
    )

    print(f"\n{'='*60}")
    print(f"Request: {content[:100]}{'...' if len(content) > 100 else ''}")
    print(f"{'='*60}\n")

    start_time = time.time()

    if streaming:
        print("Processing (streaming)...\n")
        async for event in orchestrator.process_streaming(request):
            if event.type == "status":
                print(f"  Status: {event.data.get('status')}")
            elif event.type == "routing":
                print(f"  Routing: mode={event.data.get('mode')}, windows={event.data.get('windows')}")
            elif event.type == "window_complete":
                status = "✓" if event.data.get('status') == 'success' else "✗"
                print(f"  {status} {event.data.get('window')} (confidence: {event.data.get('confidence', 0):.2f})")
            elif event.type == "consensus":
                print(f"  Consensus: score={event.data.get('score', 0):.2f}, reached={event.data.get('reached')}")
            elif event.type == "complete":
                print(f"\n{'─'*60}")
                print("Response:")
                print(f"{'─'*60}")
                print(event.data.get('content', ''))
            elif event.type == "error":
                print(f"\n  ERROR: {event.data.get('error')}")
    else:
        print("Processing...\n")
        response = await orchestrator.process(request)

        elapsed = time.time() - start_time

        print(f"{'─'*60}")
        print("Response:")
        print(f"{'─'*60}")
        print(response.content or "(empty response)")

        print(f"\n{'─'*60}")
        print("Metadata:")
        print(f"{'─'*60}")
        print(f"  Status: {response.status.value}")
        print(f"  Windows used: {', '.join(response.metadata.windows_used)}")
        if response.metadata.windows_failed:
            print(f"  Windows failed: {', '.join(response.metadata.windows_failed)}")
        print(f"  Consensus score: {response.metadata.consensus_score:.2f}")
        print(f"  Consensus reached: {response.metadata.consensus_reached}")
        print(f"  Debate rounds: {response.metadata.debate_rounds}")
        print(f"  Routing mode: {response.metadata.routing_mode}")
        print(f"  Latency: {response.metadata.total_latency_ms:.0f}ms")
        if response.error:
            print(f"  Error: {response.error}")

    print(f"\n{'='*60}\n")


async def interactive_mode(orchestrator: ParallelOrchestrator) -> None:
    """Run in interactive mode."""
    print("\n" + "="*60)
    print("PCO Interactive Mode")
    print("="*60)
    print("Commands:")
    print("  /mode <fast|balanced|thorough> - Set routing mode")
    print("  /stats - Show orchestrator stats")
    print("  /health - Check window health")
    print("  /quit - Exit")
    print("="*60 + "\n")

    current_mode = None

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith("/"):
                parts = user_input.split(maxsplit=1)
                cmd = parts[0].lower()

                if cmd == "/quit" or cmd == "/exit":
                    print("Goodbye!")
                    break

                elif cmd == "/mode":
                    if len(parts) > 1:
                        current_mode = parts[1].lower()
                        print(f"Routing mode set to: {current_mode}")
                    else:
                        print(f"Current mode: {current_mode or 'auto'}")

                elif cmd == "/stats":
                    stats = orchestrator.get_stats()
                    print("\nOrchestrator Stats:")
                    print(f"  Total requests: {stats['total_requests']}")
                    print(f"  Active requests: {stats['active_requests']}")
                    print(f"  Windows: {', '.join(stats['windows'])}")
                    print(f"  Context stats: {stats['context_stats']}")
                    print()

                elif cmd == "/health":
                    print("\nChecking health...")
                    health = await orchestrator.health_check()
                    print(f"  Orchestrator: {health['orchestrator']}")
                    for name, status in health['windows'].items():
                        print(f"  {name}: {status}")
                    print()

                else:
                    print(f"Unknown command: {cmd}")

                continue

            # Process as request
            await process_request(orchestrator, user_input, mode=current_mode)

        except KeyboardInterrupt:
            print("\n\nInterrupted. Type /quit to exit.")
        except EOFError:
            print("\nGoodbye!")
            break


async def main():
    parser = argparse.ArgumentParser(
        description="Parallel Context Orchestrator CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s "Write a Python function to parse JSON"
    %(prog)s --mode thorough "Explain the theory of relativity"
    %(prog)s --interactive
    %(prog)s --streaming "What is machine learning?"
        """,
    )

    parser.add_argument(
        "request",
        nargs="?",
        help="Request to process",
    )

    parser.add_argument(
        "--mode", "-m",
        choices=["fast", "balanced", "thorough"],
        help="Routing mode (default: auto)",
    )

    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode",
    )

    parser.add_argument(
        "--streaming", "-s",
        action="store_true",
        help="Use streaming output",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    # Set up logging
    import logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Create orchestrator
    print("Initializing PCO with mock windows...")
    orchestrator = create_mock_orchestrator()

    if args.interactive:
        await interactive_mode(orchestrator)
    elif args.request:
        await process_request(
            orchestrator,
            args.request,
            mode=args.mode,
            streaming=args.streaming,
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
