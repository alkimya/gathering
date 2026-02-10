"""
Circuit breaker for pipeline node execution.

Implements the CLOSED/OPEN/HALF_OPEN state machine to prevent
repeated calls to failing nodes. Uses monotonic time for reliability.
"""

import time
from dataclasses import dataclass, field
from enum import Enum


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Per-node circuit breaker with configurable threshold and recovery.

    State transitions:
    - CLOSED: Normal operation. Failures increment counter.
    - OPEN: failure_count >= failure_threshold. Calls fail fast.
    - HALF_OPEN: recovery_timeout elapsed since last failure. One trial call allowed.
    - Success in HALF_OPEN -> CLOSED. Failure in HALF_OPEN -> OPEN.
    """

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0

    @property
    def is_open(self) -> bool:
        """Check if circuit is in OPEN state."""
        return self.state == CircuitState.OPEN

    def can_execute(self) -> bool:
        """Determine if a call is allowed through the circuit breaker.

        Returns True for CLOSED and HALF_OPEN states.
        For OPEN state, checks if recovery_timeout has elapsed
        and transitions to HALF_OPEN if so.
        """
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.HALF_OPEN:
            return True

        # State is OPEN -- check if recovery timeout has elapsed
        if self.state == CircuitState.OPEN:
            elapsed = time.monotonic() - self.last_failure_time
            if elapsed >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True

        return False

    def record_success(self) -> None:
        """Record a successful call. Resets circuit to CLOSED."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failed call. May trip circuit to OPEN."""
        self.failure_count += 1
        self.last_failure_time = time.monotonic()

        if self.state == CircuitState.HALF_OPEN:
            # Failure during trial -> back to OPEN
            self.state = CircuitState.OPEN
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
