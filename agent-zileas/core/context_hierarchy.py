"""
Sliding Hierarchy Context Manager for PCO

Manages Scout's 10M token context window with intelligent tiering:
- Hot (2M tokens): Current task + recent turns
- Warm (5M tokens): Session history + relevant memories
- Cold (3M tokens): Archived but retrievable on demand

Context flows: Hot → Warm → Cold as relevance decreases
Retrieved context flows: Cold → Warm → Hot based on query relevance
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path


class ContextTier(Enum):
    HOT = "hot"      # Immediate context - always in active window
    WARM = "warm"    # Session context - loaded on relevance
    COLD = "cold"    # Archived - retrieved only when queried


@dataclass
class ContextChunk:
    """A chunk of context with metadata for hierarchy management."""
    id: str
    content: str
    token_count: int
    tier: ContextTier
    created_at: datetime
    last_accessed: datetime
    relevance_score: float  # 0-1, updated dynamically
    source: str  # "user", "window:verifier", "memory", etc.
    provenance: Optional[str] = None  # Hash of origin for trust verification

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "token_count": self.token_count,
            "tier": self.tier.value,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "relevance_score": self.relevance_score,
            "source": self.source,
            "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ContextChunk":
        return cls(
            id=data["id"],
            content=data["content"],
            token_count=data["token_count"],
            tier=ContextTier(data["tier"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            relevance_score=data["relevance_score"],
            source=data["source"],
            provenance=data.get("provenance"),
        )


@dataclass
class TierConfig:
    """Configuration for a context tier."""
    max_tokens: int
    decay_rate: float  # How fast relevance decays (0-1 per hour)
    promotion_threshold: float  # Relevance score to promote to higher tier
    demotion_threshold: float  # Relevance score to demote to lower tier


class SlidingContextHierarchy:
    """
    Manages the 10M token context window with intelligent tiering.

    Key behaviors:
    1. New context enters HOT tier
    2. Context decays based on time and access patterns
    3. Context is demoted when it falls below threshold
    4. Queries can promote context back to higher tiers
    5. Cold context is persisted to disk for retrieval
    """

    DEFAULT_CONFIG = {
        ContextTier.HOT: TierConfig(
            max_tokens=2_000_000,  # 2M
            decay_rate=0.1,
            promotion_threshold=0.8,  # N/A for HOT
            demotion_threshold=0.3,
        ),
        ContextTier.WARM: TierConfig(
            max_tokens=5_000_000,  # 5M
            decay_rate=0.05,
            promotion_threshold=0.7,
            demotion_threshold=0.2,
        ),
        ContextTier.COLD: TierConfig(
            max_tokens=3_000_000,  # 3M
            decay_rate=0.01,
            promotion_threshold=0.5,
            demotion_threshold=0.0,  # Can't demote below COLD
        ),
    }

    def __init__(
        self,
        config: Optional[Dict[ContextTier, TierConfig]] = None,
        cold_storage_path: Optional[Path] = None,
    ):
        self.config = config or self.DEFAULT_CONFIG
        self.cold_storage_path = cold_storage_path or Path("data/cold_context")

        # In-memory storage for HOT and WARM
        self._tiers: Dict[ContextTier, List[ContextChunk]] = {
            ContextTier.HOT: [],
            ContextTier.WARM: [],
            ContextTier.COLD: [],  # References only, content on disk
        }

        self._load_cold_index()

    def _load_cold_index(self):
        """Load index of cold context (metadata only, not content)."""
        index_path = self.cold_storage_path / "index.json"
        if index_path.exists():
            try:
                index_data = json.loads(index_path.read_text())
                self._tiers[ContextTier.COLD] = [
                    ContextChunk.from_dict(c) for c in index_data
                ]
            except (json.JSONDecodeError, IOError):
                pass

    def _save_cold_index(self):
        """Save cold context index."""
        self.cold_storage_path.mkdir(parents=True, exist_ok=True)
        index_path = self.cold_storage_path / "index.json"
        index_data = [c.to_dict() for c in self._tiers[ContextTier.COLD]]
        index_path.write_text(json.dumps(index_data, indent=2))

    def _generate_id(self, content: str) -> str:
        """Generate unique ID for content."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _estimate_tokens(self, content: str) -> int:
        """Rough token estimation (4 chars per token)."""
        return len(content) // 4

    def _calculate_provenance(self, content: str, source: str) -> str:
        """Generate provenance hash for trust verification."""
        data = f"{content}:{source}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]

    def _get_tier_tokens(self, tier: ContextTier) -> int:
        """Get total tokens in a tier."""
        return sum(c.token_count for c in self._tiers[tier])

    def add_context(
        self,
        content: str,
        source: str,
        initial_relevance: float = 1.0,
    ) -> ContextChunk:
        """
        Add new context to the HOT tier.

        Args:
            content: The context content
            source: Origin identifier (e.g., "user", "window:coder")
            initial_relevance: Starting relevance score (default 1.0)

        Returns:
            The created ContextChunk
        """
        chunk = ContextChunk(
            id=self._generate_id(content),
            content=content,
            token_count=self._estimate_tokens(content),
            tier=ContextTier.HOT,
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            relevance_score=initial_relevance,
            source=source,
            provenance=self._calculate_provenance(content, source),
        )

        # Add to HOT tier
        self._tiers[ContextTier.HOT].append(chunk)

        # Enforce tier limits
        self._enforce_tier_limits()

        return chunk

    def access_context(self, chunk_id: str) -> Optional[ContextChunk]:
        """
        Access a context chunk, boosting its relevance.

        Returns the chunk if found, promoting it if necessary.
        """
        for tier in ContextTier:
            for chunk in self._tiers[tier]:
                if chunk.id == chunk_id:
                    chunk.last_accessed = datetime.utcnow()
                    chunk.relevance_score = min(1.0, chunk.relevance_score + 0.2)

                    # Check for promotion
                    if tier != ContextTier.HOT:
                        self._maybe_promote(chunk, tier)

                    return chunk

        return None

    def query_relevant(
        self,
        query: str,
        max_tokens: int = 500_000,
        min_relevance: float = 0.3,
    ) -> List[ContextChunk]:
        """
        Query for relevant context across all tiers.

        This is a simplified relevance search - in production,
        this would use embeddings/vector search.

        Returns chunks sorted by relevance, up to max_tokens.
        """
        all_chunks = []

        # Collect from all tiers
        for tier in ContextTier:
            for chunk in self._tiers[tier]:
                if chunk.relevance_score >= min_relevance:
                    # Simple keyword relevance boost
                    query_words = set(query.lower().split())
                    chunk_words = set(chunk.content.lower().split()[:100])
                    overlap = len(query_words & chunk_words)
                    boost = min(0.3, overlap * 0.05)
                    chunk.relevance_score = min(1.0, chunk.relevance_score + boost)
                    all_chunks.append(chunk)

        # Sort by relevance
        all_chunks.sort(key=lambda c: c.relevance_score, reverse=True)

        # Collect up to max_tokens
        result = []
        total_tokens = 0
        for chunk in all_chunks:
            if total_tokens + chunk.token_count <= max_tokens:
                result.append(chunk)
                total_tokens += chunk.token_count
                # Mark as accessed
                chunk.last_accessed = datetime.utcnow()

        return result

    def _maybe_promote(self, chunk: ContextChunk, current_tier: ContextTier):
        """Promote chunk to higher tier if relevance is high enough."""
        if current_tier == ContextTier.HOT:
            return  # Already at highest

        target_tier = {
            ContextTier.COLD: ContextTier.WARM,
            ContextTier.WARM: ContextTier.HOT,
        }[current_tier]

        threshold = self.config[target_tier].promotion_threshold
        if chunk.relevance_score >= threshold:
            # Remove from current tier
            self._tiers[current_tier].remove(chunk)

            # Load content if from cold storage
            if current_tier == ContextTier.COLD:
                self._load_cold_content(chunk)

            # Add to target tier
            chunk.tier = target_tier
            self._tiers[target_tier].append(chunk)

            # Enforce limits
            self._enforce_tier_limits()

    def _enforce_tier_limits(self):
        """Ensure each tier stays within token limits by demoting excess."""
        for tier in [ContextTier.HOT, ContextTier.WARM]:
            config = self.config[tier]
            while self._get_tier_tokens(tier) > config.max_tokens:
                # Find lowest relevance chunk to demote
                chunks = self._tiers[tier]
                if not chunks:
                    break

                lowest = min(chunks, key=lambda c: c.relevance_score)
                self._demote_chunk(lowest, tier)

    def _demote_chunk(self, chunk: ContextChunk, from_tier: ContextTier):
        """Demote a chunk to the next lower tier."""
        self._tiers[from_tier].remove(chunk)

        if from_tier == ContextTier.HOT:
            chunk.tier = ContextTier.WARM
            self._tiers[ContextTier.WARM].append(chunk)
        elif from_tier == ContextTier.WARM:
            chunk.tier = ContextTier.COLD
            self._save_cold_content(chunk)
            self._tiers[ContextTier.COLD].append(chunk)
            self._save_cold_index()

    def _save_cold_content(self, chunk: ContextChunk):
        """Save chunk content to cold storage."""
        self.cold_storage_path.mkdir(parents=True, exist_ok=True)
        content_path = self.cold_storage_path / f"{chunk.id}.txt"
        content_path.write_text(chunk.content)

    def _load_cold_content(self, chunk: ContextChunk):
        """Load chunk content from cold storage."""
        content_path = self.cold_storage_path / f"{chunk.id}.txt"
        if content_path.exists():
            chunk.content = content_path.read_text()

    def apply_decay(self):
        """
        Apply time-based relevance decay to all chunks.

        Should be called periodically (e.g., every minute).
        """
        now = datetime.utcnow()

        for tier in ContextTier:
            config = self.config[tier]
            for chunk in self._tiers[tier]:
                # Calculate hours since last access
                hours = (now - chunk.last_accessed).total_seconds() / 3600
                decay = config.decay_rate * hours

                chunk.relevance_score = max(0.0, chunk.relevance_score - decay)

                # Check for demotion
                if (tier != ContextTier.COLD and
                    chunk.relevance_score < config.demotion_threshold):
                    self._demote_chunk(chunk, tier)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about context hierarchy."""
        return {
            "hot": {
                "chunks": len(self._tiers[ContextTier.HOT]),
                "tokens": self._get_tier_tokens(ContextTier.HOT),
                "max_tokens": self.config[ContextTier.HOT].max_tokens,
            },
            "warm": {
                "chunks": len(self._tiers[ContextTier.WARM]),
                "tokens": self._get_tier_tokens(ContextTier.WARM),
                "max_tokens": self.config[ContextTier.WARM].max_tokens,
            },
            "cold": {
                "chunks": len(self._tiers[ContextTier.COLD]),
                "tokens": self._get_tier_tokens(ContextTier.COLD),
                "max_tokens": self.config[ContextTier.COLD].max_tokens,
            },
            "total_tokens": sum(
                self._get_tier_tokens(t) for t in ContextTier
            ),
        }

    def build_context_window(
        self,
        query: Optional[str] = None,
        include_warm: bool = True,
        max_tokens: int = 2_000_000,
    ) -> str:
        """
        Build the active context window for Scout.

        Args:
            query: Optional query to boost relevant context
            include_warm: Whether to include WARM tier context
            max_tokens: Maximum tokens to include

        Returns:
            Combined context string ready for Scout
        """
        chunks = []
        total_tokens = 0

        # Always include all HOT context
        for chunk in sorted(
            self._tiers[ContextTier.HOT],
            key=lambda c: c.created_at,
            reverse=True
        ):
            if total_tokens + chunk.token_count <= max_tokens:
                chunks.append(chunk)
                total_tokens += chunk.token_count

        # Optionally include WARM context by relevance
        if include_warm and query:
            warm_relevant = sorted(
                self._tiers[ContextTier.WARM],
                key=lambda c: c.relevance_score,
                reverse=True
            )
            for chunk in warm_relevant:
                if total_tokens + chunk.token_count <= max_tokens:
                    chunks.append(chunk)
                    total_tokens += chunk.token_count

        # Sort by creation time for coherent context
        chunks.sort(key=lambda c: c.created_at)

        # Build context string with source markers
        context_parts = []
        for chunk in chunks:
            context_parts.append(f"[{chunk.source} @ {chunk.created_at.isoformat()}]\n{chunk.content}")

        return "\n\n---\n\n".join(context_parts)
