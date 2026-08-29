"""
signal_controller.py

JCTRL - Signal Controller module.

Responsibility (and ONLY responsibility):
    - Accept a SignalDecision from *any* decision producer (baseline
      timer, adaptive model, a human, a test harness -- the controller
      does not know or care which).
    - Turn that decision into a valid, time-accurate SignalState by
      running a simple GREEN -> YELLOW -> (other phase) GREEN state
      machine, enforcing MVP timing constraints.
    - Expose a tick(dt) interface so any external driver can advance
      simulation time and read back the current SignalState.

This module deliberately does NOT:
    - render anything (no Pygame, no drawing)
    - generate vehicles or traffic
    - compute TrafficState / traffic metrics
    - implement ML or any adaptive decision logic
    - know whether a SignalDecision came from a baseline timer or a model

It only consumes the SignalDecision contract and produces the
SignalState contract.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Union

# --------------------------------------------------------------------------
# MVP TIMING CONSTRAINTS
# --------------------------------------------------------------------------

MIN_GREEN = 10       # seconds
MAX_GREEN = 60       # seconds
YELLOW_DURATION = 5  # seconds, fixed regardless of decision source

# Fallback green duration used for a phase before any SignalDecision has
# ever been received for it. Matches the specified baseline behaviour
# (green=30, yellow=5) so a controller with no input yet still behaves
# sensibly.
DEFAULT_GREEN = 30

PHASES = ("NS", "EW")
STATES = ("GREEN", "YELLOW", "RED")


def _clamp_green(seconds: int) -> int:
    """Clamp a requested green duration into the MVP-allowed range."""
    return max(MIN_GREEN, min(MAX_GREEN, int(seconds)))


def _other_phase(phase: str) -> str:
    return "EW" if phase == "NS" else "NS"


# --------------------------------------------------------------------------
# CONTRACTS
# --------------------------------------------------------------------------

@dataclass
class SignalDecision:
    phase: str            # "NS" | "EW"
    green_duration: int

    @staticmethod
    def from_dict(d: dict) -> "SignalDecision":
        return SignalDecision(phase=str(d["phase"]), green_duration=int(d["green_duration"]))

    def to_dict(self) -> dict:
        return {"phase": self.phase, "green_duration": self.green_duration}


@dataclass
class SignalState:
    active_phase: str      # "NS" | "EW"
    state: str             # "GREEN" | "YELLOW" | "RED"
    remaining_time: int

    def to_dict(self) -> dict:
        return {
            "active_phase": self.active_phase,
            "state": self.state,
            "remaining_time": self.remaining_time,
        }


SignalDecisionLike = Union[SignalDecision, dict]


# --------------------------------------------------------------------------
# SIGNAL CONTROLLER
# --------------------------------------------------------------------------

class SignalController:
    """
    A minimal, correct fixed-phase (NS <-> EW) signal state machine.

    State machine per active phase:
        GREEN  (for phase's configured green_duration, clamped to
                 [MIN_GREEN, MAX_GREEN])
          -> YELLOW (fixed YELLOW_DURATION)
             -> other phase becomes active, state = GREEN, and the cycle
                repeats.

    The non-active phase is always implicitly RED -- this matches the
    SignalState contract, which only carries state for the *active*
    phase. `get_state()` / `tick()` return that active-phase state; a
    consumer (e.g. the Intersection Blueprint) treats the other
    direction as RED by construction.

    Applying a new SignalDecision is always SAFE:
      - A decision for the CURRENTLY ACTIVE phase, while it is GREEN,
        adjusts that phase's remaining green time (extend or shorten),
        clamped to [MIN_GREEN, MAX_GREEN]. Because the clamp guarantees
        the *total* green duration is always >= MIN_GREEN, a phase can
        never be cut short of the minimum green guarantee, even if a
        shorter decision arrives after the phase has already been green
        for a while.
      - A decision for the phase that is NOT currently active is queued
        as that phase's next green duration. It takes effect the next
        time that phase becomes active (after the current phase finishes
        its GREEN + YELLOW), never by abruptly interrupting the phase
        that is currently green or yellow.
      - The controller never skips the YELLOW clearance interval and
        never jumps directly between two GREEN states.
    """

    def __init__(self, initial_phase: str = "NS", initial_green: int = DEFAULT_GREEN):
        if initial_phase not in PHASES:
            raise ValueError(f"initial_phase must be one of {PHASES}, got {initial_phase!r}")

        # Per-phase green duration to use whenever that phase becomes
        # active. Starts at the MVP baseline default for both phases.
        self._phase_green: Dict[str, int] = {"NS": DEFAULT_GREEN, "EW": DEFAULT_GREEN}
        self._phase_green[initial_phase] = _clamp_green(initial_green)

        self._active_phase: str = initial_phase
        self._state: str = "GREEN"
        self._remaining: float = float(self._phase_green[initial_phase])

    # ------------------------------------------------------------- input
    def receive_decision(self, decision: SignalDecisionLike) -> None:
        """
        Accept a SignalDecision from any decision producer (baseline or
        model -- indistinguishable to this controller) and apply it
        safely per the rules described in the class docstring.
        """
        d = decision if isinstance(decision, SignalDecision) else SignalDecision.from_dict(decision)

        if d.phase not in PHASES:
            raise ValueError(f"SignalDecision.phase must be one of {PHASES}, got {d.phase!r}")

        clamped = _clamp_green(d.green_duration)

        if d.phase == self._active_phase and self._state == "GREEN":
            # Same phase, currently green: adjust remaining time in place.
            elapsed = self._phase_green[self._active_phase] - self._remaining
            self._phase_green[self._active_phase] = clamped
            self._remaining = max(0.0, clamped - elapsed)
        else:
            # Either a different phase, or the active phase is already in
            # YELLOW (about to hand off) -- queue for next time this
            # phase becomes active rather than interrupting anything.
            self._phase_green[d.phase] = clamped

    # ---------------------------------------------------------------- tick
    def tick(self, dt: float = 1.0) -> SignalState:
        """
        Advance simulation time by dt seconds and return the resulting
        SignalState. Safe to call with a large dt: it will cascade
        through GREEN -> YELLOW -> next GREEN transitions as many times
        as needed rather than producing negative time or skipping a
        YELLOW interval.
        """
        if dt < 0:
            raise ValueError("dt must be >= 0")

        remaining_dt = dt
        # Loop so a single large tick can still pass through multiple
        # phase transitions correctly (never skips YELLOW).
        while remaining_dt > 0:
            if self._remaining > remaining_dt:
                self._remaining -= remaining_dt
                remaining_dt = 0
            else:
                remaining_dt -= self._remaining
                self._advance_phase()

        return self.get_state()

    def _advance_phase(self) -> None:
        """Move to the next state in the GREEN -> YELLOW -> GREEN cycle."""
        if self._state == "GREEN":
            self._state = "YELLOW"
            self._remaining = float(YELLOW_DURATION)
        else:  # was YELLOW -> hand off to the other phase's GREEN
            self._active_phase = _other_phase(self._active_phase)
            self._state = "GREEN"
            self._remaining = float(self._phase_green[self._active_phase])

    # --------------------------------------------------------------- output
    def get_state(self) -> SignalState:
        """Return the current SignalState without advancing time."""
        return SignalState(
            active_phase=self._active_phase,
            state=self._state,
            remaining_time=max(0, int(math.ceil(self._remaining))),
        )

    def reset(self, initial_phase: str = "NS", initial_green: int = DEFAULT_GREEN) -> None:
        """Reset the controller to a fresh initial state."""
        self.__init__(initial_phase=initial_phase, initial_green=initial_green)


# --------------------------------------------------------------------------
# SELF-TEST / INDEPENDENT EXECUTION
# --------------------------------------------------------------------------
# Running this file directly proves the controller works standalone, with
# zero dependency on a real baseline/model decision producer or on the
# Intersection Blueprint. It feeds a couple of hand-written mock
# SignalDecision objects through a short manual tick loop and prints the
# resulting SignalState each second. For a fuller mock example (baseline
# + adaptive-style decision producers), see example.py.

def _self_test_main():
    controller = SignalController(initial_phase="NS", initial_green=30)

    mock_decisions = {
        0: {"phase": "NS", "green_duration": 30},   # baseline-style
        35: {"phase": "EW", "green_duration": 15},  # queued for next EW turn
        50: {"phase": "NS", "green_duration": 100}, # will be clamped to 60
    }

    print("t=0 initial state:", controller.get_state().to_dict())
    for t in range(1, 90):
        if t in mock_decisions:
            controller.receive_decision(mock_decisions[t])
            print(f"t={t} received decision: {mock_decisions[t]}")
        state = controller.tick(1)
        print(f"t={t} state: {state.to_dict()}")


if __name__ == "__main__":
    _self_test_main()
