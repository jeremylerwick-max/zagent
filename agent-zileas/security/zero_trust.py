"""
Zero Trust Security Framework for PCO

Core philosophy: "Never trust, always verify"

No agent trusts another agent's output without verification.
No tool execution without permission checks.
No external data accepted without sanitization.

Security layers:
1. Input validation - sanitize all inputs
2. Permission gates - check before every action
3. Output verification - verify all outputs before synthesis
4. Audit logging - track all actions for forensics
5. Rate limiting - prevent abuse
6. Network isolation - allowlist external connections
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Callable, Any
from enum import Enum
from datetime import datetime, timedelta
import re
import json
from pathlib import Path
from functools import wraps


class SecurityLevel(Enum):
    """Security clearance levels for operations."""
    PUBLIC = 1       # Read-only, non-sensitive operations
    INTERNAL = 2     # Standard window operations
    ELEVATED = 3     # Tool execution, file operations
    CRITICAL = 4     # System modifications, network access


class ThreatType(Enum):
    """Types of security threats to detect."""
    INJECTION = "injection"           # Prompt injection attempts
    EXFILTRATION = "exfiltration"    # Data exfiltration attempts
    PRIVILEGE_ESCALATION = "privilege_escalation"
    RATE_ABUSE = "rate_abuse"
    SSRF = "ssrf"                     # Server-side request forgery
    PATH_TRAVERSAL = "path_traversal"
    SUSPICIOUS_PATTERN = "suspicious_pattern"


@dataclass
class SecurityEvent:
    """A security event for audit logging."""
    timestamp: datetime
    event_type: str
    actor: str
    action: str
    resource: Optional[str]
    threat_type: Optional[ThreatType]
    blocked: bool
    details: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "actor": self.actor,
            "action": self.action,
            "resource": self.resource,
            "threat_type": self.threat_type.value if self.threat_type else None,
            "blocked": self.blocked,
            "details": self.details,
        }


@dataclass
class PermissionGrant:
    """A permission granted to an actor."""
    actor: str
    permission: str
    granted_at: datetime
    expires_at: Optional[datetime]
    granted_by: str
    conditions: Optional[Dict[str, Any]] = None


class AuditLog:
    """Maintains audit log of all security events."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("data/security/audit.jsonl")
        self._events: List[SecurityEvent] = []
        self._load()

    def _load(self):
        """Load recent events from storage."""
        if self.storage_path.exists():
            try:
                for line in self.storage_path.read_text().strip().split("\n")[-1000:]:
                    if line:
                        data = json.loads(line)
                        self._events.append(SecurityEvent(
                            timestamp=datetime.fromisoformat(data["timestamp"]),
                            event_type=data["event_type"],
                            actor=data["actor"],
                            action=data["action"],
                            resource=data.get("resource"),
                            threat_type=ThreatType(data["threat_type"]) if data.get("threat_type") else None,
                            blocked=data["blocked"],
                            details=data.get("details"),
                        ))
            except (json.JSONDecodeError, IOError):
                pass

    def log(self, event: SecurityEvent):
        """Log a security event."""
        self._events.append(event)

        # Append to file
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "a") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

    def get_recent(self, limit: int = 100) -> List[SecurityEvent]:
        """Get recent events."""
        return self._events[-limit:]

    def get_threats(self, since: Optional[datetime] = None) -> List[SecurityEvent]:
        """Get all threat events since a given time."""
        if since is None:
            since = datetime.utcnow() - timedelta(hours=24)

        return [
            e for e in self._events
            if e.threat_type is not None and e.timestamp >= since
        ]


class InputValidator:
    """
    Validates and sanitizes all inputs before processing.

    Detects:
    - Prompt injection attempts
    - Path traversal attacks
    - SSRF attempts
    - Malicious patterns
    """

    # Patterns that indicate prompt injection attempts
    INJECTION_PATTERNS = [
        r"ignore (previous|all|above) instructions",
        r"you are now",
        r"new instructions:",
        r"system prompt:",
        r"<\|.*\|>",  # Common injection delimiters
        r"ADMIN MODE",
        r"developer mode",
        r"jailbreak",
        r"DAN mode",
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"/etc/passwd",
        r"/etc/shadow",
        r"~/.ssh",
        r"C:\\Windows\\",
    ]

    # SSRF patterns (internal networks)
    SSRF_PATTERNS = [
        r"127\.0\.0\.\d+",
        r"localhost",
        r"0\.0\.0\.0",
        r"169\.254\.\d+\.\d+",  # Link-local
        r"10\.\d+\.\d+\.\d+",    # Private
        r"172\.(1[6-9]|2\d|3[01])\.\d+\.\d+",  # Private
        r"192\.168\.\d+\.\d+",  # Private
    ]

    def __init__(self):
        self._injection_re = [re.compile(p, re.IGNORECASE) for p in self.INJECTION_PATTERNS]
        self._path_traversal_re = [re.compile(p) for p in self.PATH_TRAVERSAL_PATTERNS]
        self._ssrf_re = [re.compile(p) for p in self.SSRF_PATTERNS]

    def validate(self, input_text: str, context: str = "general") -> tuple[bool, Optional[ThreatType], Optional[str]]:
        """
        Validate input text for security threats.

        Args:
            input_text: The text to validate
            context: Context for validation (e.g., "url", "path", "general")

        Returns:
            Tuple of (is_safe, threat_type, details)
        """
        # Check for prompt injection
        for pattern in self._injection_re:
            if pattern.search(input_text):
                return (False, ThreatType.INJECTION, f"Matched injection pattern: {pattern.pattern}")

        # Check for path traversal (if path context)
        if context in ("path", "file"):
            for pattern in self._path_traversal_re:
                if pattern.search(input_text):
                    return (False, ThreatType.PATH_TRAVERSAL, f"Path traversal detected: {pattern.pattern}")

        # Check for SSRF (if URL context)
        if context in ("url", "network"):
            for pattern in self._ssrf_re:
                if pattern.search(input_text):
                    return (False, ThreatType.SSRF, f"SSRF attempt detected: {pattern.pattern}")

        return (True, None, None)

    def sanitize(self, input_text: str) -> str:
        """
        Sanitize input by removing potentially dangerous content.

        Note: This is a last resort - prefer rejection over sanitization.
        """
        sanitized = input_text

        # Remove null bytes
        sanitized = sanitized.replace("\x00", "")

        # Normalize unicode
        import unicodedata
        sanitized = unicodedata.normalize("NFKC", sanitized)

        # Remove control characters (except newlines/tabs)
        sanitized = "".join(
            c for c in sanitized
            if c in "\n\t" or not unicodedata.category(c).startswith("C")
        )

        return sanitized


class PermissionManager:
    """
    Manages permissions for actors (windows, tools, users).

    Implements principle of least privilege.
    """

    # Default permissions by actor type
    DEFAULT_PERMISSIONS = {
        "window:verifier": {"read", "analyze"},
        "window:coder": {"read", "analyze", "generate_code"},
        "window:reasoner": {"read", "analyze"},
        "window:synthesizer": {"read", "analyze", "synthesize", "write_output"},
        "tool:read": {"read_file"},
        "tool:write": {"write_file"},
        "tool:exec": {"execute_command"},
        "tool:web_search": {"external_network"},
        "tool:web_fetch": {"external_network"},
        "user": {"all"},  # Users have all permissions
    }

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("data/security/permissions.json")
        self._grants: Dict[str, List[PermissionGrant]] = {}
        self._load()

    def _load(self):
        """Load permission grants from storage."""
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text())
                for actor, grants in data.items():
                    self._grants[actor] = [
                        PermissionGrant(
                            actor=g["actor"],
                            permission=g["permission"],
                            granted_at=datetime.fromisoformat(g["granted_at"]),
                            expires_at=datetime.fromisoformat(g["expires_at"]) if g.get("expires_at") else None,
                            granted_by=g["granted_by"],
                            conditions=g.get("conditions"),
                        )
                        for g in grants
                    ]
            except (json.JSONDecodeError, IOError):
                pass

    def _save(self):
        """Persist permission grants."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            actor: [
                {
                    "actor": g.actor,
                    "permission": g.permission,
                    "granted_at": g.granted_at.isoformat(),
                    "expires_at": g.expires_at.isoformat() if g.expires_at else None,
                    "granted_by": g.granted_by,
                    "conditions": g.conditions,
                }
                for g in grants
            ]
            for actor, grants in self._grants.items()
        }
        self.storage_path.write_text(json.dumps(data, indent=2))

    def has_permission(self, actor: str, permission: str) -> bool:
        """
        Check if an actor has a specific permission.

        Checks both default and granted permissions.
        """
        # Check default permissions
        for prefix, perms in self.DEFAULT_PERMISSIONS.items():
            if actor.startswith(prefix) or actor == prefix:
                if "all" in perms or permission in perms:
                    return True

        # Check granted permissions
        now = datetime.utcnow()
        for grant in self._grants.get(actor, []):
            if grant.permission == permission:
                if grant.expires_at is None or grant.expires_at > now:
                    return True

        return False

    def grant(
        self,
        actor: str,
        permission: str,
        granted_by: str,
        duration: Optional[timedelta] = None,
        conditions: Optional[Dict[str, Any]] = None,
    ) -> PermissionGrant:
        """
        Grant a permission to an actor.

        Args:
            actor: The actor receiving the permission
            permission: The permission being granted
            granted_by: Who is granting the permission
            duration: How long the grant lasts (None = permanent)
            conditions: Optional conditions for the grant

        Returns:
            The created PermissionGrant
        """
        grant = PermissionGrant(
            actor=actor,
            permission=permission,
            granted_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + duration if duration else None,
            granted_by=granted_by,
            conditions=conditions,
        )

        if actor not in self._grants:
            self._grants[actor] = []
        self._grants[actor].append(grant)

        self._save()
        return grant

    def revoke(self, actor: str, permission: str) -> bool:
        """Revoke a permission from an actor."""
        if actor not in self._grants:
            return False

        original_len = len(self._grants[actor])
        self._grants[actor] = [
            g for g in self._grants[actor]
            if g.permission != permission
        ]

        if len(self._grants[actor]) < original_len:
            self._save()
            return True
        return False

    def get_permissions(self, actor: str) -> Set[str]:
        """Get all active permissions for an actor."""
        permissions = set()

        # Default permissions
        for prefix, perms in self.DEFAULT_PERMISSIONS.items():
            if actor.startswith(prefix) or actor == prefix:
                permissions.update(perms)

        # Granted permissions
        now = datetime.utcnow()
        for grant in self._grants.get(actor, []):
            if grant.expires_at is None or grant.expires_at > now:
                permissions.add(grant.permission)

        return permissions


class RateLimiter:
    """
    Rate limiting to prevent abuse.

    Tracks requests per actor and enforces limits.
    """

    DEFAULT_LIMITS = {
        "window": (100, 60),    # 100 requests per 60 seconds
        "tool:exec": (10, 60),  # 10 exec calls per 60 seconds
        "tool:web": (30, 60),   # 30 web requests per 60 seconds
        "user": (200, 60),      # 200 user requests per 60 seconds
    }

    def __init__(self):
        self._requests: Dict[str, List[datetime]] = {}

    def _get_limit(self, actor: str) -> tuple[int, int]:
        """Get (max_requests, window_seconds) for an actor."""
        for prefix, limit in self.DEFAULT_LIMITS.items():
            if actor.startswith(prefix):
                return limit
        return (50, 60)  # Default fallback

    def check(self, actor: str) -> tuple[bool, Optional[str]]:
        """
        Check if actor is within rate limits.

        Returns (allowed, error_message).
        """
        max_requests, window_seconds = self._get_limit(actor)
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)

        # Clean old requests
        if actor in self._requests:
            self._requests[actor] = [
                t for t in self._requests[actor]
                if t >= window_start
            ]

        # Check limit
        request_count = len(self._requests.get(actor, []))
        if request_count >= max_requests:
            return (False, f"Rate limit exceeded: {request_count}/{max_requests} in {window_seconds}s")

        return (True, None)

    def record(self, actor: str):
        """Record a request from an actor."""
        if actor not in self._requests:
            self._requests[actor] = []
        self._requests[actor].append(datetime.utcnow())


class NetworkAllowlist:
    """
    Controls which external hosts can be accessed.

    Prevents SSRF and data exfiltration.
    """

    DEFAULT_ALLOWED = {
        "api.openai.com",
        "api.anthropic.com",
        "ollama.local",
        "localhost:11434",  # Local Ollama
    }

    DEFAULT_BLOCKED = {
        "169.254.169.254",  # AWS metadata
        "metadata.google.internal",
        "metadata.azure.com",
    }

    def __init__(self, allowed: Optional[Set[str]] = None, blocked: Optional[Set[str]] = None):
        self._allowed = allowed or self.DEFAULT_ALLOWED.copy()
        self._blocked = blocked or self.DEFAULT_BLOCKED.copy()

    def is_allowed(self, host: str) -> tuple[bool, Optional[str]]:
        """
        Check if a host is allowed for external access.

        Returns (allowed, reason).
        """
        # Normalize host
        host = host.lower().strip()

        # Check blocked list first
        if host in self._blocked:
            return (False, f"Host {host} is explicitly blocked")

        # Check for internal IP patterns
        internal_patterns = [
            r"^127\.",
            r"^10\.",
            r"^172\.(1[6-9]|2\d|3[01])\.",
            r"^192\.168\.",
            r"^0\.",
            r"^169\.254\.",
        ]

        for pattern in internal_patterns:
            if re.match(pattern, host):
                return (False, f"Internal IP address not allowed: {host}")

        # Check allowed list
        if host in self._allowed:
            return (True, None)

        # By default, allow external hosts (can be made stricter)
        return (True, None)

    def add_allowed(self, host: str):
        """Add a host to the allowlist."""
        self._allowed.add(host.lower().strip())

    def add_blocked(self, host: str):
        """Add a host to the blocklist."""
        self._blocked.add(host.lower().strip())


class ZeroTrustGate:
    """
    Main security gate that combines all security checks.

    Every operation passes through this gate.
    """

    def __init__(
        self,
        audit_log: Optional[AuditLog] = None,
        validator: Optional[InputValidator] = None,
        permissions: Optional[PermissionManager] = None,
        rate_limiter: Optional[RateLimiter] = None,
        network_allowlist: Optional[NetworkAllowlist] = None,
    ):
        self.audit = audit_log or AuditLog()
        self.validator = validator or InputValidator()
        self.permissions = permissions or PermissionManager()
        self.rate_limiter = rate_limiter or RateLimiter()
        self.network = network_allowlist or NetworkAllowlist()

    def check_request(
        self,
        actor: str,
        action: str,
        resource: Optional[str] = None,
        input_text: Optional[str] = None,
        context: str = "general",
    ) -> tuple[bool, Optional[str]]:
        """
        Perform all security checks for a request.

        Args:
            actor: Who is making the request
            action: What action is being requested
            resource: Optional resource being accessed
            input_text: Optional input text to validate
            context: Context for validation

        Returns:
            (allowed, reason) tuple
        """
        # 1. Rate limiting
        allowed, reason = self.rate_limiter.check(actor)
        if not allowed:
            self._log_event(actor, action, resource, ThreatType.RATE_ABUSE, True, reason)
            return (False, reason)

        # 2. Permission check
        if not self.permissions.has_permission(actor, action):
            reason = f"Permission denied: {actor} cannot perform {action}"
            self._log_event(actor, action, resource, ThreatType.PRIVILEGE_ESCALATION, True, reason)
            return (False, reason)

        # 3. Input validation
        if input_text:
            is_safe, threat, details = self.validator.validate(input_text, context)
            if not is_safe:
                self._log_event(actor, action, resource, threat, True, details)
                return (False, f"Input validation failed: {details}")

        # 4. Network check (if applicable)
        if resource and context in ("url", "network"):
            import urllib.parse
            try:
                parsed = urllib.parse.urlparse(resource)
                host = parsed.netloc or parsed.path.split("/")[0]
                allowed, reason = self.network.is_allowed(host)
                if not allowed:
                    self._log_event(actor, action, resource, ThreatType.SSRF, True, reason)
                    return (False, reason)
            except Exception:
                pass

        # Record the request
        self.rate_limiter.record(actor)

        # Log successful access
        self._log_event(actor, action, resource, None, False, "Allowed")

        return (True, None)

    def _log_event(
        self,
        actor: str,
        action: str,
        resource: Optional[str],
        threat: Optional[ThreatType],
        blocked: bool,
        details: Optional[str],
    ):
        """Log a security event."""
        event = SecurityEvent(
            timestamp=datetime.utcnow(),
            event_type="access_check",
            actor=actor,
            action=action,
            resource=resource,
            threat_type=threat,
            blocked=blocked,
            details=details,
        )
        self.audit.log(event)


def secure_operation(permission: str, context: str = "general"):
    """
    Decorator to secure a function with Zero Trust checks.

    Usage:
        @secure_operation("execute_command", context="path")
        async def run_command(self, command: str):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Get actor from self (assumes class has actor attribute)
            actor = getattr(self, "actor", "unknown")

            # Get input text from first string argument
            input_text = None
            for arg in args:
                if isinstance(arg, str):
                    input_text = arg
                    break

            # Get resource from kwargs or second argument
            resource = kwargs.get("resource") or (args[1] if len(args) > 1 else None)

            # Check with gate
            gate = getattr(self, "security_gate", None) or ZeroTrustGate()
            allowed, reason = gate.check_request(
                actor=actor,
                action=permission,
                resource=resource,
                input_text=input_text,
                context=context,
            )

            if not allowed:
                raise PermissionError(reason)

            return await func(self, *args, **kwargs)

        return wrapper
    return decorator
