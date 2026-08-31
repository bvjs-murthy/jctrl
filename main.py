from jctrl_scenario_engine import ScenarioEngine
from jctrl_scenario_engine.scenarios import get_scenario
from jctrl_intersection_blueprint.intersection_blueprint import (
    IntersectionBlueprint,
    VehicleState,
    SignalState,
)
from jctrl_signal_controller.signal_controller import (
    SignalController,
    SignalDecision,
)
from jctrl_model.model import load_model


def main():
    # --------------------------------------------------
    # INITIALIZE MODULES
    # --------------------------------------------------

    scenario = get_scenario("balanced")
    engine = ScenarioEngine(scenario, seed=42)

    intersection = IntersectionBlueprint()

    controller = SignalController(
        initial_phase="NS",
        initial_green=30,
    )

    model = load_model()

    dt = 1.0

    # --------------------------------------------------
    # SIMULATION LOOP
    # --------------------------------------------------

    for step in range(600):

        # 1. Get current signal state
        signal_state = controller.get_state()

        # 2. Convert signal state -> right of way
        if (
            signal_state.active_phase == "NS"
            and signal_state.state == "GREEN"
        ):
            right_of_way = {"N", "S"}

        elif (
            signal_state.active_phase == "EW"
            and signal_state.state == "GREEN"
        ):
            right_of_way = {"E", "W"}

        else:
            right_of_way = set()

        # 3. Generate / advance vehicles
        vehicles = engine.tick(
            dt,
            right_of_way=right_of_way,
        )

        vehicles = [
            VehicleState.from_dict(v)
            for v in vehicles
        ]

        # 4. Send vehicles to intersection
        intersection.update_vehicles(vehicles) # type: ignore

        # 5. Send current signal to intersection
        intersection.update_signal(
            SignalState(
                active_phase=signal_state.active_phase,
                state=signal_state.state,
                remaining_time=signal_state.remaining_time,
            )
        )

        # 6. Update waiting-time bookkeeping
        intersection.tick(dt)

        # 7. Extract traffic state
        traffic_state = intersection.get_traffic_state()

        # 8. Ask ML model for recommendation
        decision_dict = model.predict(
            traffic_state.to_dict(),
            current_phase=signal_state.active_phase,
        )

        decision = SignalDecision.from_dict(decision_dict)

        # 9. Give ML decision to Signal Controller
        controller.receive_decision(decision)

        # 10. Advance signal controller
        controller.tick(dt)

        # --------------------------------------------------
        # DEBUG OUTPUT
        # --------------------------------------------------

        if step % 10 == 0:
            print(
                f"[{step:03d}] "
                f"Signal={signal_state.active_phase}/{signal_state.state} "
                f"Decision={decision.phase}/{decision.green_duration}s "
                f"N={traffic_state.N.vehicle_count} "
                f"S={traffic_state.S.vehicle_count} "
                f"E={traffic_state.E.vehicle_count} "
                f"W={traffic_state.W.vehicle_count}"
            )


if __name__ == "__main__":
    main()