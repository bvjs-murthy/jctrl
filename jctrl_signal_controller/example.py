"""
example.py

Standalone example proving the Signal Controller works entirely on its
own, driven only by mock SignalDecision producers. Two mocks are
provided to demonstrate the key requirement: the controller behaves
identically regardless of *which* producer it's fed by, because it only
ever sees the SignalDecision contract.

    - BaselineDecisionProvider : fixed-time producer, matches the MVP
                                 baseline spec (green=30s, alternates
                                 NS/EW every cycle).
    - MockModelDecisionProvider: stands in for a future adaptive model.
                                 Produces varying green durations
                                 (including out-of-range values) to show
                                 the controller clamps them safely.

Neither producer talks to the controller's internals -- they only ever
hand it plain dicts matching the SignalDecision contract via
`controller.receive_decision(...)`.

Run:
    python example.py
"""

import random

from signal_controller import SignalController, MIN_GREEN, MAX_GREEN


class BaselineDecisionProvider:
    """Fixed-time baseline: always requests 30s green, alternating
    NS/EW each time it's asked. This is what a simple non-adaptive
    'Model/Baseline' box in the JCTRL pipeline would look like -- it is
    NOT part of the Signal Controller module itself."""

    def __init__(self, start_phase="NS"):
        self._next_phase = start_phase

    def next_decision(self) -> dict:
        decision = {"phase": self._next_phase, "green_duration": 30}
        self._next_phase = "EW" if self._next_phase == "NS" else "NS"
        return decision


class MockModelDecisionProvider:
    """Stands in for a future adaptive model. Produces plausible but
    varying green durations -- including some intentionally out of the
    [MIN_GREEN, MAX_GREEN] range -- to prove the controller enforces
    its own timing constraints regardless of what it's handed."""

    def __init__(self, start_phase="NS", seed=42):
        self._next_phase = start_phase
        self._rng = random.Random(seed)

    def next_decision(self) -> dict:
        # occasionally request something out of range on purpose
        duration = self._rng.choice([8, 15, 22, 45, 60, 75, 10])
        decision = {"phase": self._next_phase, "green_duration": duration}
        self._next_phase = "EW" if self._next_phase == "NS" else "NS"
        return decision


def run_with_provider(provider, label, seconds=180):
    print(f"\n--- Running controller with {label} ---")
    controller = SignalController(initial_phase="NS", initial_green=30)

    last_phase = None
    last_state = None
    t = 0
    # Feed one decision per phase turn: whenever the controller is about
    # to start a fresh GREEN for a phase that hasn't been given a
    # decision yet for its *next* cycle, ask the provider for one. To
    # keep this example simple we just push a new decision once at the
    # start of every YELLOW (i.e. "for whichever phase goes next").
    controller.receive_decision(provider.next_decision())

    while t < seconds:
        state = controller.tick(1)
        t += 1

        if state.state == "YELLOW" and last_state != "YELLOW":
            # queue the decision for the next phase while current one
            # finishes its yellow clearance -- this is exactly the
            # "safe" application described in signal_controller.py
            controller.receive_decision(provider.next_decision())

        if (state.active_phase, state.state) != (last_phase, last_state):
            print(f"t={t:4d}  {state.to_dict()}")
            last_phase, last_state = state.active_phase, state.state


def main():
    run_with_provider(BaselineDecisionProvider(), "BaselineDecisionProvider (green=30 fixed)")
    run_with_provider(MockModelDecisionProvider(), "MockModelDecisionProvider (varying, some out-of-range)")
    print(f"\nController-enforced range for all decisions: [{MIN_GREEN}, {MAX_GREEN}] seconds")


if __name__ == "__main__":
    main()
