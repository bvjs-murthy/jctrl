# JCTRL — Signal Controller module

Independent, self-contained module implementing **only** the "Signal
Controller" box in the JCTRL pipeline:

```
Model / Baseline → SignalDecision → [Signal Controller] → SignalState → Intersection Blueprint
```

It turns a `SignalDecision` (from *any* producer — the controller can't
tell and doesn't try to) into a valid, time-accurate `SignalState` over
simulation time, via a simple GREEN → YELLOW → (other phase) GREEN state
machine.

## Project structure

```
jctrl_signal_controller/
├── signal_controller.py        # the module itself (contracts + state machine)
├── example.py                  # standalone example: mock baseline + mock model producers
├── test_signal_controller.py   # unit tests for transitions, clamping, safe decisions
├── requirements.txt            # empty — pure Python standard library
└── README.md
```

## Install & run

No external dependencies — pure standard library.

```bash
# Option A: the module's own built-in self-test (a few hand-written mock decisions)
python signal_controller.py

# Option B: fuller standalone example (mock baseline + mock model producers)
python example.py

# Tests
python -m unittest test_signal_controller.py -v
# or
python test_signal_controller.py
```

## Public API (`signal_controller.py`)

### Constants
```python
MIN_GREEN = 10        # seconds
MAX_GREEN = 60        # seconds
YELLOW_DURATION = 5   # seconds, fixed
DEFAULT_GREEN = 30     # fallback for a phase with no decision yet (matches baseline spec)
```

### Data contracts
- `SignalDecision(phase, green_duration)` — dataclass matching the spec. `SignalDecision.from_dict(d)` / `.to_dict()`.
- `SignalState(active_phase, state, remaining_time)` — dataclass matching the spec. `.to_dict()` gives the exact JSON shape.

### `SignalController`
- `SignalController(initial_phase="NS", initial_green=30)` — construct. `initial_green` is clamped to `[MIN_GREEN, MAX_GREEN]`.
- `receive_decision(decision: dict | SignalDecision)` — accept a decision from any producer and apply it **safely**:
  - Decision for the **currently active, GREEN** phase → adjusts that phase's remaining green time in place (extend or shorten), clamped to `[MIN_GREEN, MAX_GREEN]`. The clamp guarantees total green served is always ≥ `MIN_GREEN`, so a phase can never be cut short of the minimum-green guarantee.
  - Decision for the **other phase** (or the active phase while it's already YELLOW) → queued as that phase's green duration for the next time it becomes active. The current GREEN/YELLOW in progress is never interrupted.
- `tick(dt=1.0) -> SignalState` — advance simulation time by `dt` seconds and return the resulting state. Handles large `dt` correctly by cascading through as many transitions as needed (never skips the YELLOW clearance interval).
- `get_state() -> SignalState` — return the current state without advancing time.
- `reset(initial_phase="NS", initial_green=30)` — reset to a fresh initial state.

The controller never renders, never generates vehicles/traffic, never computes `TrafficState`, and never inspects *where* a `SignalDecision` came from.

## Standalone example (`example.py`)

Two mock decision producers, both emitting nothing but plain
`SignalDecision`-shaped dicts:

- `BaselineDecisionProvider` — fixed-time, `green_duration=30` every turn, alternating `NS`/`EW`. Matches the MVP baseline spec (`green=30`, `yellow=5`).
- `MockModelDecisionProvider` — stands in for a future adaptive model; emits varying durations, including some deliberately out of `[10, 60]`, to prove the controller enforces its own limits regardless of the source.

Running it shows both producers driving the *same* `SignalController`
class through `receive_decision()` / `tick()`, with identical handling —
proving the controller doesn't know or care which one it's talking to.
Sample output:

```
--- Running controller with BaselineDecisionProvider (green=30 fixed) ---
t=   1  {'active_phase': 'NS', 'state': 'GREEN', 'remaining_time': 29}
t=  30  {'active_phase': 'NS', 'state': 'YELLOW', 'remaining_time': 5}
t=  35  {'active_phase': 'EW', 'state': 'GREEN', 'remaining_time': 30}
...

--- Running controller with MockModelDecisionProvider (varying, some out-of-range) ---
t=   1  {'active_phase': 'NS', 'state': 'GREEN', 'remaining_time': 59}   # 75s request clamped to 60
t=  60  {'active_phase': 'NS', 'state': 'YELLOW', 'remaining_time': 5}
t=  65  {'active_phase': 'EW', 'state': 'GREEN', 'remaining_time': 10}   # 8s request clamped to 10
...
```

## Tests (`test_signal_controller.py`)

22 unit tests covering:
- Initial state (default / custom / invalid phase / clamped initial green)
- Phase transitions: GREEN countdown, GREEN→YELLOW, YELLOW→next-phase GREEN, full NS→EW→NS cycle, alternation over multiple cycles
- Large-`dt` ticks never skip the YELLOW interval; `remaining_time` never goes negative
- Safe decision application: min/max clamping, mid-green extension/shortening, min-green guarantee preserved even when a shorter decision arrives late, opposite-phase decisions queued (not applied mid-green), decisions ignored mid-yellow until the next phase begins
- Baseline-style decision stream produces the exact expected `SignalState` sequence (`green=30`, `yellow=5`)
- `reset()` behaviour

All pass: `Ran 22 tests in 0.005s — OK`.

## Integration instructions

1. **Upstream (Model / Baseline)**: whatever produces decisions —a
   fixed-time baseline, an adaptive model, or a test harness—just needs
   to call:
   ```python
   controller.receive_decision({"phase": "NS", "green_duration": 30})
   ```
   at whatever cadence makes sense for that producer (e.g. once per
   phase, or continuously with the latest recommendation). The
   controller does not require a decision every tick; if none arrives,
   it keeps running the current/queued timing.

2. **Simulation loop**: whatever owns the tick — a Pygame loop, a
   headless simulation driver, etc. — calls:
   ```python
   signal_state = controller.tick(dt_seconds)
   ```
   once per simulation step, and passes `signal_state.to_dict()`
   downstream.

3. **Downstream (Intersection Blueprint)**: feed the result straight
   into the Blueprint's `update_signal()`:
   ```python
   blueprint.update_signal(controller.get_state().to_dict())
   ```
   The shapes already match exactly — no adapter needed.

4. **No cross-module coupling required**: the Signal Controller has no
   import of, or dependency on, the Intersection Blueprint, a Scenario
   Engine, or any ML code. It can be developed, tested, and swapped
   independently of all of them, exactly like the Blueprint module.
