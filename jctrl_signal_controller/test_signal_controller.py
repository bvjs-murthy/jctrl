"""
test_signal_controller.py

Unit tests for the Signal Controller module. Run with:

    python -m unittest test_signal_controller.py -v

or simply:

    python test_signal_controller.py
"""

import unittest

from signal_controller import (
    SignalController,
    SignalDecision,
    SignalState,
    MIN_GREEN,
    MAX_GREEN,
    YELLOW_DURATION,
    DEFAULT_GREEN,
)


class TestInitialState(unittest.TestCase):
    def test_default_initial_state(self):
        c = SignalController()
        s = c.get_state()
        self.assertEqual(s.active_phase, "NS")
        self.assertEqual(s.state, "GREEN")
        self.assertEqual(s.remaining_time, DEFAULT_GREEN)

    def test_custom_initial_phase_and_green(self):
        c = SignalController(initial_phase="EW", initial_green=20)
        s = c.get_state()
        self.assertEqual(s.active_phase, "EW")
        self.assertEqual(s.state, "GREEN")
        self.assertEqual(s.remaining_time, 20)

    def test_invalid_initial_phase_raises(self):
        with self.assertRaises(ValueError):
            SignalController(initial_phase="XX")

    def test_initial_green_is_clamped(self):
        c_low = SignalController(initial_phase="NS", initial_green=1)
        self.assertEqual(c_low.get_state().remaining_time, MIN_GREEN)
        c_high = SignalController(initial_phase="NS", initial_green=999)
        self.assertEqual(c_high.get_state().remaining_time, MAX_GREEN)


class TestPhaseTransitions(unittest.TestCase):
    def test_green_counts_down(self):
        c = SignalController(initial_phase="NS", initial_green=10)
        s = c.tick(1)
        self.assertEqual(s, SignalState("NS", "GREEN", 9))

    def test_green_to_yellow_transition(self):
        c = SignalController(initial_phase="NS", initial_green=10)
        for _ in range(9):
            c.tick(1)
        s = c.tick(1)  # 10th second -> green exhausted, becomes yellow
        self.assertEqual(s.active_phase, "NS")
        self.assertEqual(s.state, "YELLOW")
        self.assertEqual(s.remaining_time, YELLOW_DURATION)

    def test_yellow_to_next_phase_green(self):
        c = SignalController(initial_phase="NS", initial_green=10)
        for _ in range(10 + YELLOW_DURATION):
            s = c.tick(1)
        self.assertEqual(s.active_phase, "EW")
        self.assertEqual(s.state, "GREEN")
        self.assertEqual(s.remaining_time, DEFAULT_GREEN)  # no EW decision given yet

    def test_full_cycle_returns_to_original_phase(self):
        c = SignalController(initial_phase="NS", initial_green=10)
        total_first_cycle = MIN_GREEN + YELLOW_DURATION  # NS green(10) + yellow(5)
        total_second_cycle = DEFAULT_GREEN + YELLOW_DURATION  # EW green(30, default) + yellow(5)
        for _ in range(total_first_cycle + total_second_cycle):
            s = c.tick(1)
        self.assertEqual(s.active_phase, "NS")
        self.assertEqual(s.state, "GREEN")

    def test_never_skips_yellow_even_with_large_dt(self):
        c = SignalController(initial_phase="NS", initial_green=10)
        # one huge tick spanning green(10) + yellow(5) + a bit into next green
        s = c.tick(17)
        self.assertEqual(s.active_phase, "EW")
        self.assertEqual(s.state, "GREEN")
        self.assertEqual(s.remaining_time, DEFAULT_GREEN - 2)

    def test_remaining_time_never_negative(self):
        c = SignalController(initial_phase="NS", initial_green=10)
        s = c.tick(1000)
        self.assertGreaterEqual(s.remaining_time, 0)

    def test_alternates_ns_ew_ns_ew(self):
        c = SignalController(initial_phase="NS", initial_green=10)
        phases_seen = []
        for _ in range(3):
            # advance through one full green+yellow for whichever phase is active
            remaining = c.get_state().remaining_time
            for _ in range(remaining + YELLOW_DURATION):
                s = c.tick(1)
            phases_seen.append(s.active_phase)
        self.assertEqual(phases_seen, ["EW", "NS", "EW"])


class TestDecisionApplication(unittest.TestCase):
    def test_decision_clamped_to_min_green(self):
        c = SignalController(initial_phase="NS", initial_green=30)
        c.receive_decision({"phase": "NS", "green_duration": 2})
        # elapsed=0, so new remaining should be clamped duration (MIN_GREEN)
        self.assertEqual(c.get_state().remaining_time, MIN_GREEN)

    def test_decision_clamped_to_max_green(self):
        c = SignalController(initial_phase="NS", initial_green=30)
        c.receive_decision({"phase": "NS", "green_duration": 500})
        self.assertEqual(c.get_state().remaining_time, MAX_GREEN)

    def test_same_phase_decision_extends_green_midway(self):
        c = SignalController(initial_phase="NS", initial_green=30)
        for _ in range(10):
            c.tick(1)  # elapsed 10s, remaining should be 20
        self.assertEqual(c.get_state().remaining_time, 20)
        c.receive_decision({"phase": "NS", "green_duration": 40})  # extend total to 40
        # elapsed=10, new duration=40 -> remaining = 30
        self.assertEqual(c.get_state().remaining_time, 30)

    def test_same_phase_decision_never_violates_min_green_already_served(self):
        c = SignalController(initial_phase="NS", initial_green=30)
        for _ in range(25):
            c.tick(1)  # elapsed 25s (> MIN_GREEN already)
        c.receive_decision({"phase": "NS", "green_duration": 10})  # try to shrink below elapsed
        # duration clamped to 10, elapsed=25 -> remaining should floor at 0,
        # immediately triggering yellow on next tick (total green served = 25 >= MIN_GREEN)
        self.assertEqual(c.get_state().remaining_time, 0)
        s = c.tick(1)
        self.assertEqual(s.state, "YELLOW")

    def test_opposite_phase_decision_does_not_interrupt_current_green(self):
        c = SignalController(initial_phase="NS", initial_green=30)
        c.tick(5)  # NS green, 25s remaining
        c.receive_decision({"phase": "EW", "green_duration": 45})
        s = c.get_state()
        self.assertEqual(s.active_phase, "NS")
        self.assertEqual(s.state, "GREEN")
        self.assertEqual(s.remaining_time, 25)  # unaffected

    def test_opposite_phase_decision_takes_effect_after_yellow(self):
        c = SignalController(initial_phase="NS", initial_green=10)
        c.receive_decision({"phase": "EW", "green_duration": 45})
        for _ in range(10 + YELLOW_DURATION):
            s = c.tick(1)
        self.assertEqual(s.active_phase, "EW")
        self.assertEqual(s.state, "GREEN")
        self.assertEqual(s.remaining_time, 45)

    def test_decision_during_yellow_is_queued_not_applied_immediately(self):
        c = SignalController(initial_phase="NS", initial_green=10)
        for _ in range(10):
            c.tick(1)  # now in YELLOW
        self.assertEqual(c.get_state().state, "YELLOW")
        c.receive_decision({"phase": "NS", "green_duration": 50})
        s = c.get_state()
        self.assertEqual(s.state, "YELLOW")  # not touched mid-yellow
        self.assertEqual(s.remaining_time, YELLOW_DURATION - 0)

    def test_invalid_phase_in_decision_raises(self):
        c = SignalController()
        with self.assertRaises(ValueError):
            c.receive_decision({"phase": "NE", "green_duration": 20})

    def test_accepts_signal_decision_dataclass_and_dict_equivalently(self):
        c1 = SignalController(initial_phase="NS", initial_green=30)
        c2 = SignalController(initial_phase="NS", initial_green=30)
        c1.receive_decision(SignalDecision(phase="NS", green_duration=15))
        c2.receive_decision({"phase": "NS", "green_duration": 15})
        self.assertEqual(c1.get_state(), c2.get_state())


class TestBaselineBehaviour(unittest.TestCase):
    """Verifies a baseline-style decision stream (green=30, yellow=5,
    alternating NS/EW) produces exactly the expected SignalState sequence,
    proving the controller treats it the same as any other producer."""

    def test_baseline_style_full_cycle_timing(self):
        c = SignalController(initial_phase="NS", initial_green=30)
        c.receive_decision({"phase": "EW", "green_duration": 30})

        # NS green for 30s
        for _ in range(29):
            s = c.tick(1)
            self.assertEqual((s.active_phase, s.state), ("NS", "GREEN"))
        s = c.tick(1)
        self.assertEqual((s.active_phase, s.state, s.remaining_time), ("NS", "YELLOW", 5))

        # yellow for 5s
        for _ in range(4):
            s = c.tick(1)
            self.assertEqual((s.active_phase, s.state), ("NS", "YELLOW"))
        s = c.tick(1)
        self.assertEqual((s.active_phase, s.state, s.remaining_time), ("EW", "GREEN", 30))


class TestResettable(unittest.TestCase):
    def test_reset_restores_initial_state(self):
        c = SignalController(initial_phase="NS", initial_green=10)
        c.tick(50)
        c.reset(initial_phase="EW", initial_green=15)
        s = c.get_state()
        self.assertEqual(s.active_phase, "EW")
        self.assertEqual(s.state, "GREEN")
        self.assertEqual(s.remaining_time, 15)


if __name__ == "__main__":
    unittest.main(verbosity=2)
