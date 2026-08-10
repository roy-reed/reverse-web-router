"""Shared exception hierarchy for the rwrouter/2 orchestrator."""


class RwRouterError(Exception):
    """Base class for all reverse-web-router errors."""


class ProtocolError(RwRouterError):
    """Protocol/format violations (wrong version, unknown enums, missing fields)."""


class SchemaValidationError(RwRouterError):
    """A record failed JSON-Schema-style validation."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


class StateTransitionError(RwRouterError):
    """An event is not allowed from the current state."""


class DependencyError(RwRouterError):
    """Dependency gate violations."""


class ClaimConflictError(RwRouterError):
    """The task is already claimed by another worker."""


class DuplicatePaidInvocationError(RwRouterError):
    """A paid worker invocation for this task already exists."""


class BoundaryViolationError(RwRouterError):
    """Changed paths violate the contract boundary."""


class SecurityError(RwRouterError):
    """Unsafe content (credentials, absolute local paths, ...) detected."""

    def __init__(self, findings):
        self.findings = list(findings)
        super().__init__("; ".join(self.findings))


class TranslationError(RwRouterError):
    """rwrouter/1.1 <-> rwrouter/2 translation failures."""


class LiveInvocationBlockedError(RwRouterError):
    """Live provider invocations are disabled in this MVP."""


class MissingCredentialError(RwRouterError):
    """A required runtime credential is absent."""
