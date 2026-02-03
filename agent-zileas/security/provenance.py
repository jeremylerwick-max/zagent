"""
Memory Provenance Tagging System for PCO

Prevents memory poisoning attacks by tracking the origin and chain
of custody for every piece of information in the system.

Each memory has:
- Origin: Where it came from (user, window, tool, external)
- Trust level: How much we trust this source
- Chain: History of modifications
- Signature: Cryptographic hash for integrity verification
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
import hashlib
import json
from pathlib import Path


class TrustLevel(Enum):
    """Trust levels for different sources."""
    USER = 100       # Direct user input - highest trust
    VERIFIED = 90    # Output verified by multiple windows
    SINGLE_WINDOW = 70  # Output from one window, unverified
    TOOL_OUTPUT = 60    # Results from tool execution
    EXTERNAL = 40       # External data (web, API)
    UNTRUSTED = 20      # Unknown or suspicious origin
    POISONED = 0        # Detected as compromised


@dataclass
class ProvenanceRecord:
    """A single record in the provenance chain."""
    timestamp: datetime
    actor: str  # Who/what made this change
    action: str  # What was done ("created", "modified", "verified")
    details: Optional[str] = None


@dataclass
class MemoryProvenance:
    """
    Complete provenance information for a memory entry.

    This is attached to every piece of information that enters
    the system and is updated as information flows through windows.
    """
    id: str
    origin_source: str  # Original source identifier
    origin_trust: TrustLevel
    created_at: datetime
    signature: str  # SHA-256 hash of original content
    chain: List[ProvenanceRecord] = field(default_factory=list)
    current_trust: Optional[TrustLevel] = None  # May change from origin
    is_verified: bool = False
    verification_count: int = 0
    verifiers: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.current_trust is None:
            self.current_trust = self.origin_trust

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "origin_source": self.origin_source,
            "origin_trust": self.origin_trust.name,
            "current_trust": self.current_trust.name,
            "created_at": self.created_at.isoformat(),
            "signature": self.signature,
            "chain": [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "actor": r.actor,
                    "action": r.action,
                    "details": r.details,
                }
                for r in self.chain
            ],
            "is_verified": self.is_verified,
            "verification_count": self.verification_count,
            "verifiers": self.verifiers,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryProvenance":
        return cls(
            id=data["id"],
            origin_source=data["origin_source"],
            origin_trust=TrustLevel[data["origin_trust"]],
            current_trust=TrustLevel[data["current_trust"]],
            created_at=datetime.fromisoformat(data["created_at"]),
            signature=data["signature"],
            chain=[
                ProvenanceRecord(
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    actor=r["actor"],
                    action=r["action"],
                    details=r.get("details"),
                )
                for r in data["chain"]
            ],
            is_verified=data.get("is_verified", False),
            verification_count=data.get("verification_count", 0),
            verifiers=data.get("verifiers", []),
        )


class ProvenanceTracker:
    """
    Tracks provenance for all memories in the system.

    Key responsibilities:
    1. Create provenance records for new content
    2. Track modifications through the chain
    3. Verify integrity using signatures
    4. Detect potential poisoning attempts
    5. Provide trust scores for synthesis decisions
    """

    # Sources and their default trust levels
    SOURCE_TRUST_MAP = {
        "user": TrustLevel.USER,
        "window:verifier": TrustLevel.SINGLE_WINDOW,
        "window:coder": TrustLevel.SINGLE_WINDOW,
        "window:reasoner": TrustLevel.SINGLE_WINDOW,
        "window:synthesizer": TrustLevel.VERIFIED,
        "tool:exec": TrustLevel.TOOL_OUTPUT,
        "tool:read": TrustLevel.TOOL_OUTPUT,
        "tool:web_search": TrustLevel.EXTERNAL,
        "tool:web_fetch": TrustLevel.EXTERNAL,
        "memory:pgvector": TrustLevel.TOOL_OUTPUT,
        "external": TrustLevel.EXTERNAL,
    }

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("data/provenance")
        self._provenance: Dict[str, MemoryProvenance] = {}
        self._load()

    def _load(self):
        """Load provenance records from storage."""
        if self.storage_path.exists():
            index_path = self.storage_path / "index.json"
            if index_path.exists():
                try:
                    data = json.loads(index_path.read_text())
                    self._provenance = {
                        k: MemoryProvenance.from_dict(v)
                        for k, v in data.items()
                    }
                except (json.JSONDecodeError, IOError):
                    pass

    def _save(self):
        """Persist provenance records."""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        index_path = self.storage_path / "index.json"
        data = {k: v.to_dict() for k, v in self._provenance.items()}
        index_path.write_text(json.dumps(data, indent=2))

    def _generate_signature(self, content: str) -> str:
        """Generate integrity signature for content."""
        return hashlib.sha256(content.encode()).hexdigest()

    def _generate_id(self, content: str, source: str) -> str:
        """Generate unique ID for a memory entry."""
        data = f"{content}:{source}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def create_provenance(
        self,
        content: str,
        source: str,
        trust_override: Optional[TrustLevel] = None,
    ) -> MemoryProvenance:
        """
        Create provenance record for new content.

        Args:
            content: The content being tracked
            source: Source identifier (e.g., "user", "window:coder")
            trust_override: Optional override for default trust level

        Returns:
            The created MemoryProvenance
        """
        # Determine trust level
        if trust_override:
            trust = trust_override
        elif source in self.SOURCE_TRUST_MAP:
            trust = self.SOURCE_TRUST_MAP[source]
        else:
            trust = TrustLevel.UNTRUSTED

        provenance = MemoryProvenance(
            id=self._generate_id(content, source),
            origin_source=source,
            origin_trust=trust,
            created_at=datetime.utcnow(),
            signature=self._generate_signature(content),
            chain=[
                ProvenanceRecord(
                    timestamp=datetime.utcnow(),
                    actor=source,
                    action="created",
                )
            ],
        )

        self._provenance[provenance.id] = provenance
        self._save()

        return provenance

    def record_modification(
        self,
        provenance_id: str,
        actor: str,
        new_content: str,
        details: Optional[str] = None,
    ) -> Optional[MemoryProvenance]:
        """
        Record a modification to existing content.

        Args:
            provenance_id: ID of the provenance record
            actor: Who made the modification
            new_content: The modified content (for new signature)
            details: Optional details about the modification

        Returns:
            Updated MemoryProvenance or None if not found
        """
        provenance = self._provenance.get(provenance_id)
        if not provenance:
            return None

        # Add to chain
        provenance.chain.append(
            ProvenanceRecord(
                timestamp=datetime.utcnow(),
                actor=actor,
                action="modified",
                details=details,
            )
        )

        # Update signature
        provenance.signature = self._generate_signature(new_content)

        # Modifications by lower-trust sources reduce trust
        actor_trust = self.SOURCE_TRUST_MAP.get(actor, TrustLevel.UNTRUSTED)
        if actor_trust.value < provenance.current_trust.value:
            provenance.current_trust = actor_trust

        self._save()
        return provenance

    def record_verification(
        self,
        provenance_id: str,
        verifier: str,
        passed: bool,
    ) -> Optional[MemoryProvenance]:
        """
        Record that content was verified by a window.

        Verification by multiple windows increases trust.

        Args:
            provenance_id: ID of the provenance record
            verifier: Window that performed verification
            passed: Whether verification passed

        Returns:
            Updated MemoryProvenance or None if not found
        """
        provenance = self._provenance.get(provenance_id)
        if not provenance:
            return None

        provenance.chain.append(
            ProvenanceRecord(
                timestamp=datetime.utcnow(),
                actor=verifier,
                action="verified" if passed else "verification_failed",
            )
        )

        if passed:
            provenance.verification_count += 1
            if verifier not in provenance.verifiers:
                provenance.verifiers.append(verifier)

            # Multiple verifications increase trust
            if provenance.verification_count >= 2:
                provenance.is_verified = True
                provenance.current_trust = TrustLevel.VERIFIED
        else:
            # Failed verification reduces trust
            if provenance.current_trust.value > TrustLevel.UNTRUSTED.value:
                # Demote one level
                trust_levels = list(TrustLevel)
                current_idx = trust_levels.index(provenance.current_trust)
                if current_idx > 0:
                    provenance.current_trust = trust_levels[current_idx - 1]

        self._save()
        return provenance

    def verify_integrity(self, provenance_id: str, content: str) -> bool:
        """
        Verify content integrity against stored signature.

        Returns True if content matches original signature.
        """
        provenance = self._provenance.get(provenance_id)
        if not provenance:
            return False

        return self._generate_signature(content) == provenance.signature

    def mark_poisoned(
        self,
        provenance_id: str,
        reason: str,
    ) -> Optional[MemoryProvenance]:
        """
        Mark content as potentially poisoned.

        This should be called when suspicious activity is detected.
        """
        provenance = self._provenance.get(provenance_id)
        if not provenance:
            return None

        provenance.chain.append(
            ProvenanceRecord(
                timestamp=datetime.utcnow(),
                actor="system:security",
                action="marked_poisoned",
                details=reason,
            )
        )

        provenance.current_trust = TrustLevel.POISONED

        self._save()
        return provenance

    def get_trust_score(self, provenance_id: str) -> float:
        """
        Get normalized trust score (0-1) for content.

        Used by consensus algorithm to weight outputs.
        """
        provenance = self._provenance.get(provenance_id)
        if not provenance:
            return 0.0

        return provenance.current_trust.value / 100.0

    def get_provenance(self, provenance_id: str) -> Optional[MemoryProvenance]:
        """Get provenance record by ID."""
        return self._provenance.get(provenance_id)

    def get_by_source(self, source: str) -> List[MemoryProvenance]:
        """Get all provenance records from a specific source."""
        return [
            p for p in self._provenance.values()
            if p.origin_source == source
        ]

    def get_untrusted(self) -> List[MemoryProvenance]:
        """Get all records with low trust for review."""
        return [
            p for p in self._provenance.values()
            if p.current_trust.value < TrustLevel.TOOL_OUTPUT.value
        ]

    def get_chain_summary(self, provenance_id: str) -> Optional[str]:
        """Get human-readable summary of provenance chain."""
        provenance = self._provenance.get(provenance_id)
        if not provenance:
            return None

        lines = [
            f"Origin: {provenance.origin_source} (Trust: {provenance.origin_trust.name})",
            f"Current Trust: {provenance.current_trust.name}",
            f"Verified: {provenance.is_verified} ({provenance.verification_count} verifications)",
            "",
            "Chain of Custody:",
        ]

        for record in provenance.chain:
            details = f" - {record.details}" if record.details else ""
            lines.append(
                f"  [{record.timestamp.isoformat()}] {record.actor}: {record.action}{details}"
            )

        return "\n".join(lines)
