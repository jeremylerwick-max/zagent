"""
Super Context Synthesizer for PCO

The synthesizer is Scout's brain - it takes outputs from all parallel
windows and produces the final, verified response.

Key responsibilities:
- Identify consensus points
- Resolve conflicts using weighted scores
- Combine best elements from each window
- Produce clean, user-facing response
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import logging

from .consensus import WindowOutput, ConsensusResult, TaskType

logger = logging.getLogger(__name__)


@dataclass
class SynthesisResult:
    """Result of synthesis operation."""
    content: str
    sources_used: List[str]  # Which windows contributed
    conflicts_resolved: int
    synthesis_method: str  # "consensus", "winner_take_all", "merge"


class Synthesizer:
    """
    Synthesizes outputs from parallel windows into a unified response.

    Strategies:
    1. Consensus: When all windows agree, use shared content
    2. Winner-take-all: Use highest confidence output
    3. Merge: Combine elements from multiple outputs
    """

    SYNTHESIS_PROMPT = """You are the Super Context Synthesizer. You receive outputs from multiple
specialized AI models and must produce the final, verified response.

## Your Inputs

**Verifier Output** (Mistral - error checking):
{verifier_output}

**Coder Output** (Qwen - code generation):
{coder_output}

**Reasoner Output** (DeepSeek - step-by-step analysis):
{reasoner_output}

## Consensus Information

Decision Score: {decision_score}
Consensus Reached: {consensus_reached}
Dissenting Windows: {dissenting_windows}

## Your Task

1. Identify consensus: Where do all models agree?
2. Identify conflicts: Where do models disagree?
3. For conflicts, prefer outputs from windows with higher confidence
4. Produce the FINAL response that:
   - Uses the best code from Coder (if applicable)
   - Incorporates corrections from Verifier
   - Follows reasoning structure from Reasoner
   - Is accurate, complete, and verified

## Output Format

Produce only the final user-facing response. Do not mention the
synthesis process or the other models. Write as if you are directly
responding to the user."""

    def __init__(self, model: Optional[Any] = None):
        """
        Initialize the synthesizer.

        Args:
            model: The LLM to use for synthesis (e.g., Scout)
        """
        self.model = model

    async def synthesize(
        self,
        request: Any,
        outputs: List[WindowOutput],
        consensus: ConsensusResult,
        context: Optional[str] = None,
    ) -> str:
        """
        Synthesize outputs into a final response.

        Args:
            request: The original user request
            outputs: List of outputs from parallel windows
            consensus: Result of consensus calculation
            context: Optional additional context

        Returns:
            Final synthesized response string
        """
        # If we have a model, use LLM synthesis
        if self.model:
            return await self._llm_synthesize(request, outputs, consensus, context)

        # Otherwise, use rule-based synthesis
        return self._rule_based_synthesize(outputs, consensus)

    async def _llm_synthesize(
        self,
        request: Any,
        outputs: List[WindowOutput],
        consensus: ConsensusResult,
        context: Optional[str],
    ) -> str:
        """Use LLM (Scout) to synthesize outputs."""
        # Build output dict by window name
        output_dict = {o.window_name: o.content for o in outputs}

        prompt = self.SYNTHESIS_PROMPT.format(
            verifier_output=output_dict.get("verifier", "N/A"),
            coder_output=output_dict.get("coder", "N/A"),
            reasoner_output=output_dict.get("reasoner", "N/A"),
            decision_score=f"{consensus.decision_score:.2f}",
            consensus_reached=consensus.consensus_reached,
            dissenting_windows=", ".join(consensus.dissenting_windows) or "None",
        )

        # Include context if provided
        if context:
            prompt = f"## Relevant Context\n{context}\n\n{prompt}"

        # Get user request content
        user_content = request.content if hasattr(request, 'content') else str(request)

        try:
            response = await self.model.generate(
                system=prompt,
                user=user_content,
            )
            return response
        except Exception as e:
            logger.error(f"LLM synthesis failed: {e}")
            # Fall back to rule-based
            return self._rule_based_synthesize(outputs, consensus)

    def _rule_based_synthesize(
        self,
        outputs: List[WindowOutput],
        consensus: ConsensusResult,
    ) -> str:
        """
        Rule-based synthesis when no LLM is available.

        Uses simple strategies based on consensus result.
        """
        if not outputs:
            return "I apologize, but I was unable to generate a response."

        # If strong consensus, use winner
        if consensus.consensus_reached:
            return consensus.winning_content

        # If we have coder output for code tasks, prefer it
        coder_output = next((o for o in outputs if o.window_name == "coder"), None)
        if coder_output and coder_output.confidence >= 0.7:
            # Enhance with verifier corrections if available
            verifier_output = next((o for o in outputs if o.window_name == "verifier"), None)
            if verifier_output and verifier_output.errors_found:
                return self._merge_code_with_corrections(coder_output, verifier_output)
            return coder_output.content

        # Default: use highest confidence
        return max(outputs, key=lambda o: o.confidence).content

    def _merge_code_with_corrections(
        self,
        coder_output: WindowOutput,
        verifier_output: WindowOutput,
    ) -> str:
        """Merge coder output with verifier corrections."""
        # Simple merge: append corrections as comments
        code = coder_output.content

        if verifier_output.errors_found:
            corrections = "\n".join([f"# Note: {e}" for e in verifier_output.errors_found[:3]])
            code = f"{corrections}\n\n{code}"

        return code


class SynthesisStrategies:
    """
    Collection of synthesis strategies for different scenarios.
    """

    @staticmethod
    def code_synthesis(outputs: List[WindowOutput], consensus: ConsensusResult) -> str:
        """
        Strategy for synthesizing code outputs.

        Prioritizes:
        1. Working code from coder
        2. Error fixes from verifier
        3. Design considerations from reasoner
        """
        result_parts = []

        # Get outputs by type
        coder = next((o for o in outputs if o.window_name == "coder"), None)
        verifier = next((o for o in outputs if o.window_name == "verifier"), None)
        reasoner = next((o for o in outputs if o.window_name == "reasoner"), None)

        # Add reasoning context if available
        if reasoner and reasoner.reasoning:
            result_parts.append(f"## Approach\n{reasoner.reasoning}\n")

        # Add main code
        if coder:
            result_parts.append(coder.content)

        # Add verifier notes
        if verifier and verifier.errors_found:
            notes = "\n".join([f"- {e}" for e in verifier.errors_found])
            result_parts.append(f"\n## Notes\n{notes}")

        return "\n".join(result_parts) if result_parts else consensus.winning_content

    @staticmethod
    def reasoning_synthesis(outputs: List[WindowOutput], consensus: ConsensusResult) -> str:
        """
        Strategy for synthesizing reasoning outputs.

        Builds a coherent reasoning chain from all windows.
        """
        result_parts = []

        # Get reasoner output as primary
        reasoner = next((o for o in outputs if o.window_name == "reasoner"), None)
        if reasoner:
            result_parts.append(reasoner.content)

        # Add verifier validation
        verifier = next((o for o in outputs if o.window_name == "verifier"), None)
        if verifier and verifier.confidence > 0.5:
            if verifier.errors_found:
                result_parts.append("\n**Considerations:**")
                for error in verifier.errors_found[:3]:
                    result_parts.append(f"- {error}")

        return "\n".join(result_parts) if result_parts else consensus.winning_content

    @staticmethod
    def factual_synthesis(outputs: List[WindowOutput], consensus: ConsensusResult) -> str:
        """
        Strategy for synthesizing factual outputs.

        Prioritizes verified information.
        """
        # For factual queries, prefer verifier output if high confidence
        verifier = next((o for o in outputs if o.window_name == "verifier"), None)
        if verifier and verifier.confidence >= 0.8:
            return verifier.content

        # Otherwise use consensus winner
        return consensus.winning_content


class StreamingSynthesizer:
    """
    Synthesizer that supports streaming output.

    Yields chunks of the response as they're generated.
    """

    def __init__(self, model: Optional[Any] = None):
        self.model = model

    async def synthesize_streaming(
        self,
        request: Any,
        outputs: List[WindowOutput],
        consensus: ConsensusResult,
        context: Optional[str] = None,
    ):
        """
        Synthesize with streaming output.

        Yields:
            String chunks of the response
        """
        if not self.model or not hasattr(self.model, 'generate_streaming'):
            # Non-streaming fallback
            result = Synthesizer()._rule_based_synthesize(outputs, consensus)
            yield result
            return

        # Build prompt
        output_dict = {o.window_name: o.content for o in outputs}
        prompt = Synthesizer.SYNTHESIS_PROMPT.format(
            verifier_output=output_dict.get("verifier", "N/A"),
            coder_output=output_dict.get("coder", "N/A"),
            reasoner_output=output_dict.get("reasoner", "N/A"),
            decision_score=f"{consensus.decision_score:.2f}",
            consensus_reached=consensus.consensus_reached,
            dissenting_windows=", ".join(consensus.dissenting_windows) or "None",
        )

        user_content = request.content if hasattr(request, 'content') else str(request)

        try:
            async for chunk in self.model.generate_streaming(
                system=prompt,
                user=user_content,
            ):
                yield chunk
        except Exception as e:
            logger.error(f"Streaming synthesis failed: {e}")
            yield Synthesizer()._rule_based_synthesize(outputs, consensus)
