"""
PCO Security Module

Implements Zero Trust security model:
- Provenance tracking for all memories
- Input validation and sanitization
- Permission management
- Rate limiting
- Network allowlisting
- Audit logging
"""

from .provenance import (
    TrustLevel,
    ProvenanceRecord,
    MemoryProvenance,
    ProvenanceTracker,
)

from .zero_trust import (
    SecurityLevel,
    ThreatType,
    SecurityEvent,
    AuditLog,
    InputValidator,
    PermissionManager,
    RateLimiter,
    NetworkAllowlist,
    ZeroTrustGate,
    secure_operation,
)

__all__ = [
    # Provenance
    "TrustLevel",
    "ProvenanceRecord",
    "MemoryProvenance",
    "ProvenanceTracker",
    # Zero Trust
    "SecurityLevel",
    "ThreatType",
    "SecurityEvent",
    "AuditLog",
    "InputValidator",
    "PermissionManager",
    "RateLimiter",
    "NetworkAllowlist",
    "ZeroTrustGate",
    "secure_operation",
]
