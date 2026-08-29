"""JCTRL ML decision model.

Input: TrafficState.to_dict() shaped as N/S/E/W -> vehicle_count,
queue_length, average_wait.
Output: SignalDecision dict: {phase: NS|EW, green_duration: 10..60}.
"""
from pathlib import Path
import joblib
import numpy as np

DIRECTIONS = ("N", "S", "E", "W")
FEATURE_NAMES = [f"{d}_{m}" for d in DIRECTIONS for m in ("vehicle_count", "queue_length", "average_wait")] + ["current_phase_NS"]

class JCTRLModel:
    def __init__(self, classifier, duration_model=None):
        self.classifier = classifier
        self.duration_model = duration_model

    @staticmethod
    def features(traffic_state: dict, current_phase: str = "NS"):
        row = []
        for d in DIRECTIONS:
            m = traffic_state[d]
            row.extend([float(m["vehicle_count"]), float(m["queue_length"]), float(m["average_wait"])])
        row.append(1.0 if current_phase == "NS" else 0.0)
        return np.asarray([row], dtype=float)

    def predict(self, traffic_state: dict, current_phase: str = "NS") -> dict:
        x = self.features(traffic_state, current_phase)
        phase = str(self.classifier.predict(x)[0])
        if self.duration_model is not None:
            duration = float(self.duration_model.predict(x)[0])
        else:
            # Safe fallback if only classifier is loaded.
            duration = 30.0
        duration = max(10, min(60, int(round(duration))))
        return {"phase": phase, "green_duration": duration}

    def save(self, path):
        joblib.dump(self, path)

    @staticmethod
    def load(path):
        return joblib.load(path)


def load_model(path=None):
    path = Path(path or Path(__file__).parent / "artifacts" / "jctrl_model.joblib")
    return JCTRLModel.load(path)
