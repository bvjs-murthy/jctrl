# Adaptive Traffic Signal Management System (JCTRL)

## 1. Product Overview
The Adaptive Traffic Signal Management System is an intelligent traffic-control system designed to 
dynamically manage traffic signals based on real-time traffic conditions.

The system observes traffic at an intersection, converts those observations into a standardized 
traffic state, uses an intelligence/optimization layer to determine an appropriate signal decision, 
and safely applies that decision through a signal controller.

The system will be validated primarily through a traffic-intersection simulation and will compare 
adaptive control against conventional fixed-time signal control.

### Core loop
```text
Traffic
   ↓
Observe
   ↓
Traffic State
   ↓
Analyze / Predict / Optimize
   ↓
Signal Decision
   ↓
Safe Signal Control
   ↓
Traffic changes
   ↓
Observe again
```

---

## 2. Problem Statement
Conventional traffic signals generally operate using predetermined timing schedules. Such schedules 
may perform poorly when traffic demand varies significantly between directions or changes 
unexpectedly.

The proposed system aims to dynamically allocate signal time according to observed traffic 
conditions, with the objective of reducing unnecessary waiting and improving traffic flow while 
maintaining signal safety and fairness.

---

## 3. Goals
The system should:
1. Observe traffic conditions at an intersection.
2. Represent traffic conditions using a standardized `traffic_state`.
3. Dynamically determine appropriate signal phases and durations.
4. Safely execute signal decisions through a dedicated controller.
5. Adapt to changing traffic conditions rather than relying exclusively on fixed timings.
6. Support emergency-vehicle prioritization.
7. Measure traffic performance using quantitative metrics.
8. Demonstrate improvement against a fixed-time baseline.
9. Support reproducible simulation scenarios.
10. Maintain clear architectural boundaries so individual components can be developed and tested 
independently.

---

## 4. Primary Use Case
A simulated intersection receives traffic from multiple directions.

The system continuously observes the intersection and determines whether the current signal 
allocation should continue or be changed.

For example:
```text
North:  42 vehicles
South:  35 vehicles
East:    8 vehicles
West:   11 vehicles
```

The intelligence layer may determine that North-South traffic requires greater priority.

The resulting decision is passed to the signal controller, which validates the decision against 
safety constraints before applying the corresponding signal transition.

The system then observes the resulting traffic state and repeats the process.

---

## 5. Target System Scope
The initial system consists of the following major components:

### 5.1 Scenario Engine
Generates traffic demand and external events for simulation.

### 5.2 Intersection Simulator
Simulates:
* roads and lanes
* vehicles
* vehicle movement
* queues
* traffic signals
* simulation time
* traffic interactions.

### 5.3 State Estimation Layer
Converts raw observations from the simulation into a standardized `traffic_state`.

### 5.4 Decision Engine
Consumes `traffic_state` and produces a `signal_decision`.

The exact intelligence approach—ML, optimization, reinforcement learning, or a hybrid approach—will 
be determined during technical design.

### 5.5 Signal Controller
Converts decisions into safe executable signal states while enforcing signal constraints.

The decision engine must not bypass this layer.

### 5.6 Data / Training Pipeline
Processes appropriate open-source traffic datasets and/or generated simulation data for training 
and evaluation of the intelligence layer.

### 5.7 Visualization and Evaluation
Provides an interactive representation of the intersection and displays system performance and 
comparison metrics.

---

## 6. Required Simulation Scenarios
The initial evaluation environment shall support five scenarios.

## Scenario 1 — Balanced Traffic
Traffic is approximately balanced across all directions.

Purpose:
* establish normal operation
* verify that the system does not unnecessarily favor one direction.

## Scenario 2 — Heavy North-South Traffic
North-South traffic is substantially heavier than East-West traffic.

Purpose:
* test adaptive prioritization under sustained directional imbalance.

## Scenario 3 — Sudden East-West Surge
Traffic demand on the East-West axis suddenly increases.

Purpose:
* test whether the system reacts to rapid changes rather than relying on historical assumptions.

## Scenario 4 — Rush Hour
Traffic demand changes according to a high-volume rush-hour pattern.

Purpose:
* evaluate performance under sustained high traffic volume.

## Scenario 5 — Emergency Vehicle
An emergency vehicle approaches the intersection from one direction.

Purpose:
* test priority handling while maintaining safe signal transitions.

---

## 7. Functional Requirements

### FR-01 — Traffic Generation
The system shall generate configurable traffic for different directions and vehicle types.

### FR-02 — Traffic Observation
The system shall obtain relevant traffic information from the simulated intersection.

### FR-03 — Traffic State
The system shall represent current traffic conditions using a standardized `traffic_state`.

Potential state information includes:
* vehicle count
* queue length
* waiting time
* average speed
* arrival rate
* lane occupancy
* current signal state
* timestamp.

The final schema will be defined in the architecture/design documentation.

### FR-04 — Signal Decision
The intelligence layer shall consume `traffic_state` and produce a standardized `signal_decision`.

A decision may include:
* selected phase
* green duration
* priority
* confidence/score where applicable.

### FR-05 — Safe Signal Execution
The signal controller shall validate and safely execute signal decisions.

It shall enforce constraints such as:
* minimum green time
* maximum green time
* yellow intervals
* clearance intervals
* incompatible signal phases.

### FR-06 — Adaptation
The system shall be capable of changing signal allocation in response to changing traffic 
conditions.

### FR-07 — Emergency Priority
The system shall support prioritization of emergency vehicles while maintaining safe signal 
transitions.

### FR-08 — Baseline Comparison
The system shall support comparison between adaptive control and a fixed-time baseline.

### FR-09 — Metrics
The system shall collect relevant performance metrics for each simulation run.

### FR-10 — Scenario Reproducibility
Simulation scenarios should support deterministic/reproducible runs where practical, including 
configurable random seeds.

---

## 8. Performance Metrics
The system should evaluate traffic management using measurable metrics rather than visual 
appearance alone.

Primary metrics:
* Average waiting time
* Total waiting time
* Average queue length
* Maximum queue length
* Vehicle throughput
* Number of stops

Additional metrics may include:
* emergency vehicle delay
* signal switching frequency
* fairness between directions
* estimated fuel/emission-related measures.

The final set of metrics will be finalized during system design.

---

## 9. Baseline
The primary baseline will be a conventional fixed-time traffic signal configuration.

The same traffic scenario should be executable using:
```text
Scenario
   ├── Fixed-Time Controller
   └── Adaptive Controller
```

This allows meaningful comparison under identical traffic conditions.

The project should report relative improvement rather than relying solely on absolute measurements.

---

## 10. Non-Functional Requirements

### NFR-01 — Modularity
Major components shall have clearly defined responsibilities and interfaces.

### NFR-02 — Independent Development
Components should be independently implementable and testable wherever possible.

### NFR-03 — Safety
The intelligence layer shall not directly manipulate signal states. All decisions must pass through 
the signal controller.

### NFR-04 — Reproducibility
Training and simulation experiments should be reproducible where practical.

### NFR-05 — Extensibility
The system should allow future replacement of:
* the traffic simulator
* the intelligence model
* the dataset
* the visualization layer
* the signal-control strategy.

without requiring a complete architectural rewrite.

### NFR-06 — Testability
Core components should expose interfaces that allow unit and integration testing without requiring 
the complete system to run.

---

## 11. Out of Scope for Initial Version
The initial version will not attempt to provide:
* direct control of real-world traffic signals
* deployment to physical intersections
* complete city-wide traffic optimization
* perfect modelling of real-world driver behaviour
* comprehensive pedestrian/cyclist modelling unless required by the selected scenario
* hardware-specific camera deployment
* guaranteed real-world traffic improvements.

The project is initially a simulation-backed intelligent traffic-control prototype.

---

## 12. High-Level Data Flow
```text
                 Scenario Configuration
                          │
                          ▼
                  ┌───────────────┐
                  │Scenario Engine│
                  └───────┬───────┘
                          │
                    Traffic Events
                          │
                          ▼
                ┌─────────────────────┐
                │Intersection Simulator│
                └──────────┬──────────┘
                           │
                    Raw Observation
                           │
                           ▼
                ┌─────────────────────┐
                │  State Estimation   │
                └──────────┬──────────┘
                           │
                     traffic_state
                           │
                           ▼
                ┌─────────────────────┐
                │   Decision Engine   │
                └──────────┬──────────┘
                           │
                    signal_decision
                           │
                           ▼
                ┌─────────────────────┐
                │  Signal Controller │
                └──────────┬──────────┘
                           │
                      signal_state
                           │
                           ▼
                ┌─────────────────────┐
                │Intersection Simulator│
                └─────────────────────┘
                           │
                           └──── feedback ────→
```

Training exists as a separate supporting pipeline:
```text
Open / Generated Data
        ↓
Data Processing
        ↓
Feature Engineering
        ↓
Training
        ↓
Model Evaluation
        ↓
Model Artifact
        ↓
Decision Engine
```

---

## 13. Success Criteria
The prototype will be considered successful if:
1. All five required scenarios can be executed.
2. The system can continuously observe simulated traffic.
3. A standardized traffic state can be produced.
4. The intelligence layer can produce valid signal decisions.
5. The signal controller safely executes those decisions.
6. The system can recover from invalid/unavailable intelligence decisions using a defined fallback 
strategy.
7. Adaptive control can be quantitatively compared with fixed-time control.
8. The system demonstrates measurable improvement in one or more primary traffic metrics under 
relevant scenarios.
9. The complete pipeline can run repeatedly without manual intervention.
10. Individual architectural components can be tested independently.

---

## 14. Architectural Principles
The project shall follow these principles:

### Observe → Decide → Act
The system is structured as a continuous feedback loop.

### Separation of Concerns
A component should own a specific responsibility and should not directly manipulate another 
component's internal state.

### Contract-Based Integration
Components communicate through explicitly defined data contracts such as:
```text
traffic_state
signal_decision
signal_state
traffic_event
```

### Intelligence Does Not Equal Control
The intelligence layer recommends decisions.

The signal controller is responsible for safe execution.

### Simulation Independence
The intelligence layer should not depend on simulator-specific internals.

### Baseline First
Adaptive performance must be evaluated against a defined baseline.

### Architecture Before Implementation
Changes that cross architectural boundaries must be documented and reviewed before being integrated.

---

## 15. Future Extensions
Potential future extensions include:
* real camera/video input
* real-world traffic datasets
* multi-intersection coordination
* pedestrian-aware control
* public transport priority
* vehicle-to-infrastructure communication
* predictive traffic modelling
* city-scale traffic optimization.

These are not requirements for the initial prototype.

---

## 16. Open Technical Decisions
The following decisions are intentionally left open for the architecture/design phase:
* Which simulator technology will be used?
* Which open datasets are suitable?
* Which ML/optimization approach should be used?
* Should prediction and optimization be separate or combined?
* What exact features constitute `traffic_state`?
* What exact structure constitutes `signal_decision`?
* What decision interval should be used?
* What objective/reward function should be optimized?
* Which performance metrics are mandatory?
* What fallback strategy should be used when the intelligence layer fails?
* Which technologies should be used for the visualization layer?

These decisions should be made **after defining the system contracts**, rather than allowing 
available tools or datasets to dictate the architecture.

---

## 17. Product Vision
The final prototype should demonstrate a complete closed-loop intelligent traffic-control system:

> **Observe traffic → understand traffic → make an informed decision → safely control the 
intersection → measure the result → adapt again.**

The objective is not merely to demonstrate vehicle detection or an ML model, but to demonstrate a 
complete, measurable and modular traffic-management system.

---
