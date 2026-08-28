# Architecture — Adaptive Traffic Signal Management System

## 1. Purpose

This document defines the high-level architecture, component boundaries, data contracts, dependency direction, and runtime behaviour of the Adaptive Traffic Signal Management System.

The architecture is intentionally independent of any specific programming language, ML framework, simulator, or UI technology.

The primary architectural objective is to make each subsystem independently understandable, testable, and replaceable while maintaining a strict separation between:

- traffic input and demand generation;
- simulation;
- traffic-state representation;
- decision making;
- signal execution;
- presentation.

---

## 2. Architectural Vision

The system is a modular, simulation-backed adaptive traffic signal control system.

It operates as a closed-loop control system:

```text
Traffic Input
     ↓
Simulation
     ↓
Observation
     ↓
State Estimation
     ↓
Traffic State
     ↓
Decision
     ↓
Signal Control
     ↓
Updated Signal State
     ↓
Simulation
     ↓
Observe Again
```

The system is not merely an ML model or a traffic visualization. Its purpose is to demonstrate an end-to-end adaptive traffic-control loop.

The current traffic-input implementation is simulation-oriented. In a future real-world deployment, this boundary can be implemented using cameras, sensors, and their processing pipelines.

---

## 3. High-Level Architecture

```text
                         ┌──────────────────┐
                         │    DASHBOARD     │
                         │                  │
                         │ Play / Pause     │
                         │ Stop             │
                         │ Scenario Select  │
                         └────────┬─────────┘
                                  │
                           Command / Config
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │     TRAFFIC INPUT        │
                    │     SCENARIO ENGINE      │
                    │                          │
                    │ Traffic demand generation│
                    │ Scenario logic            │
                    │ Future: cameras/sensors  │
                    └────────────┬─────────────┘
                                 │
                           TrafficEvent
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │   INTERSECTION SIMULATOR │
                    │                          │
                    │ Intersection config      │
                    │ Vehicle state            │
                    │ Movement / physics       │
                    │ Simulation clock         │
                    │ Signal state             │
                    └────────────┬─────────────┘
                                 │
                             Observation
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │    STATE ESTIMATION      │
                    │                          │
                    │ Observation refinement   │
                    │ Feature extraction       │
                    │ TrafficState generation  │
                    └────────────┬─────────────┘
                                 │
                           TrafficState
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │     DECISION ENGINE      │
                    │                          │
                    │ Trained model            │
                    │ Inference                │
                    │ Signal recommendation    │
                    └────────────┬─────────────┘
                                 │
                          SignalDecision
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │    SIGNAL CONTROLLER     │
                    │                          │
                    │ Validate decision        │
                    │ Apply transition         │
                    │ Maintain SignalState     │
                    └────────────┬─────────────┘
                                 │
                             SignalState
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │   INTERSECTION SIMULATOR │
                    │       applies state      │
                    └──────────────────────────┘


              ┌────────────────────────────────────────┐
              │          PRESENTATION LAYER            │
              │                                        │
              │  ┌──────────────┐  ┌───────────────┐  │
              │  │    Pygame    │  │   Dashboard   │  │
              │  │   Renderer   │  │   / Controls  │  │
              │  └──────────────┘  └───────────────┘  │
              │                                        │
              │     Receives system/view state        │
              └────────────────────────────────────────┘
```

The training lifecycle is separate from the runtime control loop:

```text
Open / Generated Data
        ↓
Data Validation
        ↓
Data Processing
        ↓
Feature Engineering
        ↓
Training
        ↓
Validation / Evaluation
        ↓
Model Artifact
        ↓
Decision Engine
```

---

## 4. Architectural Domains

```text
CORE
├── Traffic Input
│   └── Scenario Engine
├── Simulation
│   └── Intersection Simulator
├── Intelligence
│   ├── State Estimation
│   └── Decision Engine
└── Control
    └── Signal Controller

PRESENTATION
├── Dashboard
└── Renderer

LIFECYCLE
└── Training Pipeline
```

---

## 5. Architectural Components

### 5.1 Dashboard

**Responsibility:** Provide user-facing commands and scenario/session controls.

The Dashboard provides:

* Play;
* Pause;
* Stop;
* scenario selection;
* configuration controls where applicable;
* system status;
* metrics;
* AI decision display;
* baseline comparison;
* performance information.

The Dashboard sends commands to the appropriate system boundary rather than directly manipulating internal simulation state.

Conceptually:

```text
Dashboard
    │
    └── Command / Configuration
              ↓
       Traffic Input / Simulation
```

The Dashboard may also consume a consolidated system/view state for presentation.

**Does not own:**

* vehicle movement;
* traffic generation logic;
* ML inference;
* signal-control logic;
* simulator internals.

---

### 5.2 Traffic Input / Scenario Engine

**Responsibility:** Represent the source of traffic entering or changing within the intersection environment.

The current implementation is the Scenario Engine. It generates traffic events according to the selected scenario and commands.

It determines:

* vehicle arrivals;
* vehicle types;
* origin and destination;
* lane assignment;
* arrival timing;
* traffic volume/distributions;
* traffic surges;
* emergency vehicle events;
* scenario configuration;
* reproducibility/random seeds.

**Input:**

```text
Command / Configuration
Scenario configuration
Current relevant system state
```

**Output:**

```text
TrafficEvent
```

Conceptual structure:

```text
TrafficEvent
├── event_id
├── timestamp
├── event_type
├── vehicle_id
├── vehicle_type
├── origin
├── destination
├── lane
└── metadata
```

The exact schema belongs in `design.md`.

**Does not own:**

* vehicle movement after introduction;
* vehicle physics;
* final vehicle positions;
* signal execution;
* ML reasoning;
* rendering.

### Future deployment boundary

The Scenario Engine is an implementation of the Traffic Input boundary for the simulation environment.

In a future real-world deployment, this boundary can instead be implemented through:

```text
Cameras
Sensors
   ↓
Detection / Processing
   ↓
Traffic Input
```

The downstream architecture should not need to change merely because the source of traffic information changes.

---

### 5.3 Intersection Simulator

**Responsibility:** Maintain and evolve the simulated intersection and its physical state.

The Simulator owns:

* intersection configuration;
* lanes and geometry;
* vehicles;
* vehicle positions;
* vehicle velocities;
* movement;
* traffic/vehicle physics;
* simulation clock;
* signal state as applied to the simulated intersection;
* simulation lifecycle.

The Simulator consumes traffic events and determines how those vehicles behave inside the intersection.

```text
TrafficEvent
      ↓
Intersection Simulator
      ↓
Vehicle placement
      ↓
Movement / Physics
      ↓
Updated simulated world
```

**Input:**

```text
TrafficEvent
SignalState
Simulation configuration
```

**Output:**

```text
Observation
IntersectionState
```

The exact schemas belong in `design.md`.

### Intersection configuration

For the current simulation, intersection configuration may use default values.

The architecture allows these values to later be configured from:

* cameras;
* sensors;
* manual measurements;
* deployment-specific configuration.

The Simulator should own the representation of the intersection configuration, while the source of that configuration can change independently.

### Critical boundary

The Scenario Engine describes **what traffic enters or changes**.

The Simulator determines **what happens to that traffic**.

The Scenario Engine must not calculate the complete physical trajectory of every vehicle.

---

### 5.4 State Estimation Layer

**Responsibility:** Convert raw observations from the simulated environment into a structured traffic representation suitable for the Decision Engine.

The State Estimation Layer answers:

> What is the current state of traffic from the information available to the system?

It owns:

* observation refinement;
* aggregation;
* feature extraction;
* queue estimation;
* waiting-time estimation;
* arrival-rate calculation;
* lane/direction-level state;
* conversion of `Observation` into `TrafficState`.

**Input:**

```text
Observation
```

**Output:**

```text
TrafficState
```

Conceptual structure:

```text
TrafficState
├── timestamp
├── intersection_id
├── current_signal_state
├── north
│   ├── vehicle_count
│   ├── queue_length
│   ├── average_speed
│   ├── average_wait
│   └── arrival_rate
├── south
├── east
└── west
```

The exact state schema must be finalized in `design.md`.

### Critical boundary

The Decision Engine depends on `TrafficState`, not on Simulator-specific internal structures.

This allows the observation source to evolve independently.

---

### 5.5 Decision Engine

**Responsibility:** Determine the recommended signal response from the current traffic state.

The Decision Engine is the intelligence layer.

It is trained beforehand as required and performs inference during runtime.

It owns:

* model loading;
* feature preparation;
* model inference;
* prediction;
* decision policy;
* optimization where applicable;
* decision scoring/confidence;
* intelligence-specific fallback where applicable.

**Input:**

```text
TrafficState
Model Artifact
```

Potential additional inputs:

```text
Historical state
Prediction horizon
Policy configuration
```

**Output:**

```text
SignalDecision
```

Conceptual structure:

```text
SignalDecision
├── timestamp
├── recommended_phase
├── recommended_duration
├── priority
├── score/confidence
└── metadata
```

### Critical boundary

The Decision Engine produces a **recommendation**, not an executable signal state.

It must never directly change the actual signal state.

The model can be retrained or replaced based on the required features and output without changing the surrounding control architecture, provided the `TrafficState` and `SignalDecision` contracts remain compatible.

---

### 5.6 Signal Controller

**Responsibility:** Validate and execute signal decisions while maintaining a valid signal state.

The Signal Controller answers:

> Can this recommendation be applied now, and if so, how should it be applied safely?

It owns:

* signal phases;
* phase transitions;
* minimum green time;
* maximum green time;
* yellow intervals;
* clearance intervals;
* conflicting-phase prevention;
* signal-state validation;
* emergency priority execution;
* fallback control;
* actual `SignalState`.

**Input:**

```text
SignalDecision
Current SignalState
Controller configuration
```

**Output:**

```text
SignalState
```

Conceptually:

```text
Decision Engine
      ↓
SignalDecision
      ↓
Signal Controller
      ↓
Validated transition
      ↓
SignalState
```

### Critical boundary

The Controller is the final authority over the executable signal state.

For example:

```text
Decision:
NORTH_SOUTH GREEN
60 seconds
```

does not mean that the Simulator immediately switches to North-South green.

If the current state is:

```text
EAST_WEST GREEN
```

the Controller is responsible for the valid transition:

```text
E-W GREEN
     ↓
E-W YELLOW
     ↓
CLEARANCE
     ↓
N-S GREEN
```

The resulting `SignalState` is then applied to the Simulator.

---

### 5.7 Renderer

**Responsibility:** Visually represent the current state of the simulated intersection.

Pygame is the intended renderer for the simulation visualization.

The Renderer displays:

* intersection geometry;
* lanes;
* vehicles;
* vehicle positions;
* traffic signals;
* relevant simulation state.

The Renderer consumes system/view state and does not own simulation logic.

```text
Simulation State
      ↓
Pygame Renderer
      ↓
Visual Representation
```

### Critical boundary

Pygame rendering must not directly manipulate Simulator internals.

Invalid:

```text
Pygame
   ↓
simulator.vehicles[12].speed = ...
```

Valid:

```text
Pygame
   ↓
Command / UI Action
   ↓
Appropriate system component
```

The simulation must remain executable without the Renderer.

---

## 6. Presentation Architecture

The presentation layer consists of:

```text
Presentation
├── Dashboard
└── Renderer
```

The two presentation components may be implemented as one application or separate applications/windows.

For example:

```text
┌─────────────────────────────────────────────┐
│                  DASHBOARD                  │
│                                             │
│  ┌─────────────────────┐  ┌──────────────┐ │
│  │                     │  │ Scenario     │ │
│  │   PYGAME RENDERER   │  │ [Rush Hour]  │ │
│  │                     │  │              │ │
│  │   🚗  🚗   🚦       │  │ [Play]       │ │
│  │                     │  │ [Pause]      │ │
│  └─────────────────────┘  │ [Stop]       │ │
│                           │              │ │
│                           │ AI Decision  │ │
│                           │ Metrics      │ │
│                           │ Baseline     │ │
│                           └──────────────┘ │
└─────────────────────────────────────────────┘
```

Alternatively, the Pygame Renderer and Dashboard can be separate processes:

```text
Intersection Simulator
       │
       ├────────→ Pygame Renderer
       │
       └────────→ Dashboard
```

Communication may use an appropriate IPC/API mechanism.

The architecture does not require Pygame and the Dashboard to be embedded into the same GUI framework.

---

## 7. System/View State

The presentation layer may require information originating from multiple components.

Rather than allowing the Dashboard to reach into individual module internals, a consolidated view representation should be provided.

Conceptual structure:

```text
DashboardState
├── simulation_status
├── selected_scenario
├── intersection_state
├── signal_state
├── traffic_metrics
├── current_decision
├── controller_status
├── baseline_metrics
└── adaptive_metrics
```

This prevents presentation code from becoming tightly coupled to the internals of:

* Simulator;
* Decision Engine;
* Signal Controller;
* Metrics/evaluation logic.

The exact mechanism for producing and transporting `DashboardState` belongs in `design.md`.

---

## 8. Core Data Contracts

The following contracts form the primary integration boundaries.

### 8.1 `Command`

**Produced by:** Dashboard

**Consumed by:** Traffic Input / Simulation control boundary

**Purpose:** Represent user/session actions such as:

```text
START
PAUSE
STOP
SELECT_SCENARIO
```

The exact command schema belongs in `design.md`.

---

### 8.2 `TrafficEvent`

**Produced by:** Traffic Input / Scenario Engine

**Consumed by:** Intersection Simulator

**Purpose:** Describe traffic demand or an external event entering/changing within the simulated environment.

---

### 8.3 `Observation`

**Produced by:** Intersection Simulator

**Consumed by:** State Estimation Layer

**Purpose:** Describe observable information about the simulated intersection.

---

### 8.4 `TrafficState`

**Produced by:** State Estimation Layer

**Consumed by:** Decision Engine

**Purpose:** Provide a standardized representation of current traffic conditions.

The Decision Engine must not depend on simulator-specific structures.

---

### 8.5 `SignalDecision`

**Produced by:** Decision Engine

**Consumed by:** Signal Controller

**Purpose:** Represent the intelligence layer's recommended signal action.

A `SignalDecision` is a recommendation, not an executable signal state.

---

### 8.6 `SignalState`

**Produced/managed by:** Signal Controller

**Consumed by:** Intersection Simulator and Presentation Layer

**Purpose:** Represent the actual signal state being applied to the simulated intersection.

---

### 8.7 `IntersectionState`

**Produced by:** Intersection Simulator

**Consumed by:** Presentation Layer and other explicitly defined consumers

**Purpose:** Represent the current simulated physical state of the intersection.

---

### 8.8 `DashboardState`

**Produced by:** Presentation/data aggregation boundary

**Consumed by:** Dashboard

**Purpose:** Provide the Dashboard with the information required for controls, visualization, metrics, decisions, and comparisons without exposing internal component structures.

---

## 9. Dependency Direction

The core runtime dependency chain is:

```text
Traffic Input
      ↓
Intersection Simulator
      ↓
State Estimation
      ↓
Decision Engine
      ↓
Signal Controller
      ↓
Intersection Simulator
```

The presentation layer observes system state:

```text
Intersection State ─────┐
Signal State ───────────┤
Traffic Metrics ────────┤
Decision ───────────────┤
Comparison ─────────────┤
                        ↓
                Presentation Layer
                  ┌─────┴─────┐
                  ↓           ↓
               Renderer    Dashboard
```

Dashboard commands enter through explicit control boundaries:

```text
Dashboard
    ↓
Command
    ↓
Traffic Input / Simulation Control
```

The training lifecycle feeds the Decision Engine:

```text
Training Pipeline
       ↓
Model Artifact
       ↓
Decision Engine
```

---

## 10. Dependency Rules

### Rule 1 — No component may directly manipulate another component's internal state

For example:

```text
DecisionEngine
    ↓
simulator.vehicles[12].something = ...
```

is architecturally invalid.

Communication must occur through defined contracts.

---

### Rule 2 — Components communicate through contracts

The primary integration objects are:

```text
Command
TrafficEvent
Observation
TrafficState
SignalDecision
SignalState
IntersectionState
DashboardState
```

Components should not reach into another component's implementation merely because its classes or data structures are accessible.

---

### Rule 3 — Downstream components cannot bypass boundaries

Examples:

* Dashboard cannot directly manipulate Simulator internals.
* Renderer cannot directly manipulate Simulator internals.
* Decision Engine cannot directly manipulate Simulator internals.
* Scenario Engine cannot directly execute signals.
* State Estimation cannot directly execute signal changes.

---

### Rule 4 — Intelligence cannot bypass the Signal Controller

Invalid:

```text
Decision Engine ───────→ Simulator
```

Valid:

```text
Decision Engine
      ↓
SignalDecision
      ↓
Signal Controller
      ↓
SignalState
      ↓
Simulator
```

---

### Rule 5 — Signal changes are state/control information, not traffic events

A signal transition must not be represented as a `TrafficEvent` merely to route it through the Scenario Engine.

The Controller produces the authoritative `SignalState`.

The Scenario Engine may use the current signal state as contextual information when determining future traffic behaviour, but it does not own signal execution.

---

### Rule 6 — Simulator must be controller-agnostic

The same simulator and traffic scenario should support different control strategies:

```text
Simulator
   ↓
Fixed-Time Controller
```

and:

```text
Simulator
   ↓
Adaptive Controller
```

This is necessary for meaningful evaluation.

---

### Rule 7 — Presentation does not own business logic

Dashboard and Renderer may request actions through explicit commands, but they must not implement:

* vehicle physics;
* traffic generation;
* ML inference;
* signal-transition rules.

---

### Rule 8 — Training is separate from runtime

Training pipelines must not become a runtime dependency for every simulation step.

A trained model artifact is loaded by the Decision Engine.

---

### Rule 9 — Stable contracts are more important than implementations

An implementation may change internally as long as it preserves the contract expected by neighbouring components.

---

## 11. Runtime Control Loop

At each simulation/control interval:

```text
1. Dashboard sends commands/configuration as required.
2. Scenario Engine interprets the active scenario and generates TrafficEvents.
3. Simulator consumes applicable TrafficEvents.
4. Simulator advances the simulated world using its movement/physics model.
5. Simulator produces an Observation and current IntersectionState.
6. State Estimation refines the Observation into TrafficState.
7. Decision Engine consumes TrafficState and produces SignalDecision.
8. Signal Controller validates the SignalDecision against the current SignalState.
9. Controller performs the required signal transition.
10. Controller produces the updated SignalState.
11. Simulator applies the updated SignalState.
12. The changed simulation state is exposed to the presentation layer.
13. Metrics and baseline/adaptive comparisons are updated.
14. The cycle repeats.
```

The exact simulation timestep and decision interval are design decisions and must not be assumed to be identical.

---

## 12. Signal-Control Safety and Fallback

The system must not assume that the intelligence layer always produces a valid recommendation.

Possible failure conditions include:

* invalid decision;
* missing model;
* model inference failure;
* impossible phase;
* duration outside permitted limits;
* stale decision;
* unavailable Decision Engine.

The Signal Controller must provide a safe fallback strategy.

The exact fallback policy will be defined in `design.md`.

A malformed or unavailable AI decision must never directly result in an invalid signal state.

---

## 13. Evaluation Architecture

Every scenario should be executable under at least two control strategies:

```text
                   Scenario
                      │
              ┌───────┴────────┐
              ↓                ↓
        Fixed-Time          Adaptive
         Controller          System
              │                │
              ↓                ↓
           Metrics           Metrics
              └───────┬────────┘
                      ↓
                  Comparison
```

The same traffic demand and initial conditions should be used where reproducibility permits.

Primary evaluation metrics include:

* average waiting time;
* total waiting time;
* average queue length;
* maximum queue length;
* throughput;
* number of stops.

Additional metrics may include:

* emergency vehicle delay;
* fairness;
* signal switching frequency;
* estimated fuel/emission measures.

---

## 14. Required Simulation Scenarios

The architecture must support:

### Scenario 1 — Balanced Traffic

Traffic is approximately balanced across directions.

### Scenario 2 — Heavy North-South Traffic

North-South demand is significantly greater than East-West demand.

### Scenario 3 — Sudden East-West Surge

East-West demand increases sharply during the simulation.

### Scenario 4 — Rush Hour

Traffic demand follows a sustained high-volume pattern.

### Scenario 5 — Emergency Vehicle

An emergency vehicle approaches the intersection and requires priority handling.

Scenarios are configurations of the Traffic Input / Scenario Engine, not separate implementations of the entire system.

---

## 15. Independent Testability

Each major component should be independently testable.

Examples:

```text
Dashboard
→ Given a command
→ produces the expected Command

Scenario Engine
→ Given scenario configuration + commands
→ produces expected TrafficEvents

Simulator
→ Given TrafficEvents + SignalState
→ produces expected simulation behaviour and Observation

State Estimator
→ Given Observation
→ produces expected TrafficState

Decision Engine
→ Given TrafficState
→ produces a valid SignalDecision

Signal Controller
→ Given SignalDecision + current SignalState
→ produces a valid SignalState

Renderer
→ Given IntersectionState
→ renders the expected representation
```

Components may use mocks, fixtures, or recorded contract data when their dependencies are unavailable.

This allows multiple contributors to develop in parallel without requiring the entire system to be operational.

---

## 16. Replaceability

The following replacements should be possible without redesigning the entire system:

### Traffic Input

```text
Scenario Engine
        ↓
future:
Camera / Sensors / Processing
```

### Decision Algorithm

```text
Rule-Based
     ↓
ML
     ↓
Optimization
     ↓
Reinforcement Learning
     ↓
Hybrid
```

### Renderer

```text
Pygame
   ↓
another renderer/UI
```

### Simulator

A different simulator implementation may replace the current simulator as long as it preserves the required contracts.

The stable contracts between components are therefore more important than the current implementation technology.

---

## 17. Training and Model Lifecycle

Training is not a runtime architectural component.

It is a development/lifecycle process that produces a model artifact consumed by the Decision Engine.

```text
Dataset
   ↓
Data Validation
   ↓
Data Processing
   ↓
Feature Engineering
   ↓
Training
   ↓
Validation
   ↓
Evaluation
   ↓
Model Artifact
   ↓
Decision Engine
```

Training data may come from:

* open-source datasets;
* generated simulation data;
* a combination of both.

The exact dataset, features, model, and output representation are intentionally left open until the decision problem and required `TrafficState` are finalized.

Runtime inference belongs to the Decision Engine.

---

## 18. Out of Scope for Architecture v1

The following decisions are intentionally deferred to detailed design:

* specific ML algorithm;
* specific ML framework;
* specific dataset;
* specific simulator implementation;
* specific frontend/UI framework;
* IPC/API technology;
* database choice;
* exact `TrafficEvent` schema;
* exact `Observation` schema;
* exact `TrafficState` schema;
* exact `SignalDecision` schema;
* exact `SignalState` schema;
* exact `IntersectionState` schema;
* exact `DashboardState` schema;
* exact controller state machine;
* exact optimization/reward function;
* exact simulation timestep;
* exact decision interval;
* physical traffic-signal deployment.

`arch.md` defines **what talks to what and who owns what**.

`design.md` defines **how those responsibilities are implemented**.

---

## 19. Architectural Principles

### Observe → Represent → Decide → Control → Observe

The system is fundamentally a feedback-control loop.

### Commands ≠ Events ≠ State

User commands, traffic events, and system state are different concepts and should not be conflated.

### Separation of Responsibility

Each component owns one clearly defined responsibility.

### Recommendation ≠ Execution

The intelligence layer recommends. The Signal Controller validates and executes.

### Demand ≠ Movement

The Traffic Input / Scenario Engine describes traffic entering or changing. The Simulator determines how that traffic physically behaves.

### State ≠ Raw Observation

The State Estimation Layer creates the representation consumed by intelligence.

### Simulation ≠ Presentation

The Simulator maintains the simulated world. The Renderer visualizes it.

### Training ≠ Runtime

Training creates a model artifact. Runtime inference belongs to the Decision Engine.

### Presentation ≠ Business Logic

Dashboard and Renderer interact with the system through explicit commands and view-state contracts rather than internal implementation details.

### Contracts Before Implementations

Integration boundaries must be defined before independent implementations are built.

### Replaceability

No component should unnecessarily expose implementation details to another component.

---

## 20. Architectural Decision Summary

The system is composed of:

```text
CORE
├── Traffic Input
│   └── Scenario Engine
├── Simulation
│   └── Intersection Simulator
├── Intelligence
│   ├── State Estimation
│   └── Decision Engine
└── Control
    └── Signal Controller

PRESENTATION
├── Dashboard
└── Pygame Renderer

LIFECYCLE
└── Training Pipeline
```

The central runtime contract chain is:

```text
Command
    ↓
TrafficEvent
    ↓
Observation
    ↓
TrafficState
    ↓
SignalDecision
    ↓
SignalState
    ↓
IntersectionState
```

The primary control loop is:

```text
Traffic Input
      ↓
Simulation
      ↓
State Estimation
      ↓
Decision Engine
      ↓
Signal Controller
      ↓
Simulation
```

The presentation layer observes the resulting system state:

```text
System State
     ↓
┌────┴────┐
↓         ↓
Renderer  Dashboard
```

This contract structure is the primary integration spine of the project.

Any implementation that crosses these boundaries must preserve the defined responsibilities and interfaces unless an explicit architectural change is proposed and reviewed.

**One thing I especially want us to preserve:** the distinction between `Command`, `TrafficEvent`, `Observation`, `TrafficState`, `SignalDecision`, and `SignalState`. That's the part that will make the implementation difficult to screw up accidentally.
