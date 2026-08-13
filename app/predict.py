import os

import joblib
import numpy as np
import pandas as pd

from pathlib import Path

from tensorflow.keras.models import load_model


# ============================================================
# PROJECT PATH
# ============================================================

# predict.py:
#
# aiops-platform/
#   app/
#     predict.py
#
# parents[0] = app
# parents[1] = aiops-platform

PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]


# ============================================================
# CANONICAL MODEL PATHS
# ============================================================

MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "lstm_autoencoder.keras"
)

SCALER_PATH = (
    PROJECT_ROOT
    / "models"
    / "scaler.pkl"
)

THRESHOLD_PATH = (
    PROJECT_ROOT
    / "models"
    / "threshold.pkl"
)


# ============================================================
# FEATURE ORDER
# ============================================================

FEATURE_COLUMNS = [
    "cpu_usage",
    "memory_usage",
    "disk_usage",
    "network_latency",
    "request_rate",
    "pod_restarts",
    "error_rate",
    "response_time"
]


# ============================================================
# CONFIGURATION
# ============================================================

SEQUENCE_LENGTH = 20


# ============================================================
# VERIFY FILES
# ============================================================

print()
print("=" * 70)
print("AIOPS MODEL LOADING")
print("=" * 70)


if not MODEL_PATH.exists():

    raise FileNotFoundError(
        f"\nModel not found:\n{MODEL_PATH}"
    )


if not SCALER_PATH.exists():

    raise FileNotFoundError(
        f"\nScaler not found:\n{SCALER_PATH}"
    )


if not THRESHOLD_PATH.exists():

    raise FileNotFoundError(
        f"\nThreshold not found:\n{THRESHOLD_PATH}"
    )


# ============================================================
# LOAD MODEL
# ============================================================

print(
    "Loading Model..."
)

model = load_model(
    MODEL_PATH
)


# ============================================================
# LOAD SCALER
# ============================================================

print(
    "Loading Scaler..."
)

scaler = joblib.load(
    SCALER_PATH
)


# ============================================================
# LOAD THRESHOLD
# ============================================================

print(
    "Loading Threshold..."
)

threshold = float(
    joblib.load(
        THRESHOLD_PATH
    )
)


# ============================================================
# VALIDATE SCALER
# ============================================================

if not hasattr(
    scaler,
    "transform"
):

    raise TypeError(
        "Loaded scaler does not provide "
        "a transform() method."
    )


if hasattr(
    scaler,
    "feature_names_in_"
):

    scaler_features = list(
        scaler.feature_names_in_
    )

    if scaler_features != FEATURE_COLUMNS:

        raise ValueError(
            "\nScaler feature order does not match "
            "the application.\n\n"
            f"Scaler:\n{scaler_features}\n\n"
            f"Application:\n{FEATURE_COLUMNS}"
        )


# ============================================================
# MODEL INFORMATION
# ============================================================

print()
print(
    "Model Loaded Successfully"
)

print(
    "ACTIVE THRESHOLD:",
    f"{threshold:.12f}"
)

print(
    "MODEL:",
    MODEL_PATH
)

print(
    "SCALER:",
    SCALER_PATH
)

print(
    "THRESHOLD FILE:",
    THRESHOLD_PATH
)

print(
    "=" * 70
)


# ============================================================
# PREDICTOR
# ============================================================

class AIOpsPredictor:

    def __init__(self):

        self.sequence = []


    # ========================================================
    # ADD METRICS
    # ========================================================

    def add_metrics(
        self,
        metrics
    ):

        # ----------------------------------------------------
        # Validate metrics
        # ----------------------------------------------------

        values = []

        for feature in FEATURE_COLUMNS:

            if feature not in metrics:

                raise KeyError(
                    f"Missing feature: {feature}"
                )

            value = metrics[
                feature
            ]

            try:

                value = float(
                    value
                )

            except (
                TypeError,
                ValueError
            ):

                raise ValueError(
                    f"Invalid numeric value "
                    f"for {feature}: {value}"
                )

            if not np.isfinite(
                value
            ):

                raise ValueError(
                    f"Non-finite value "
                    f"for {feature}: {value}"
                )

            values.append(
                value
            )


        # ----------------------------------------------------
        # DataFrame with EXACT feature names/order.
        #
        # This prevents:
        #
        # X has feature names, but MinMaxScaler...
        #
        # warnings.
        # ----------------------------------------------------

        frame = pd.DataFrame(
            [values],
            columns=FEATURE_COLUMNS
        )


        # ----------------------------------------------------
        # Transform exactly once.
        #
        # The scaler was trained with:
        #
        # MinMaxScaler(
        #     feature_range=(0, 1),
        #     clip=True
        # )
        #
        # Therefore live values outside the training range
        # are clipped instead of creating values like 38.895.
        # ----------------------------------------------------

        scaled = scaler.transform(
            frame
        )[0]


        # ----------------------------------------------------
        # Safety check.
        # ----------------------------------------------------

        if not np.all(
            np.isfinite(scaled)
        ):

            raise ValueError(
                "Scaler produced non-finite values."
            )


        # ----------------------------------------------------
        # Keep the latest observation.
        # ----------------------------------------------------

        self.sequence.append(
            scaled.astype(
                np.float32
            ).tolist()
        )


        # ----------------------------------------------------
        # Keep exactly the latest 20 observations.
        # ----------------------------------------------------

        if len(
            self.sequence
        ) > SEQUENCE_LENGTH:

            self.sequence.pop(0)


    # ========================================================
    # READY
    # ========================================================

    def ready(self):

        return (
            len(self.sequence)
            >= SEQUENCE_LENGTH
        )


    # ========================================================
    # RESET
    # ========================================================

    def reset(self):

        self.sequence.clear()


    # ========================================================
    # PREDICT
    # ========================================================

    def predict(self):

        if not self.ready():

            return {
                "status": "waiting",

                "samples_collected": len(
                    self.sequence
                ),

                "samples_required":
                    SEQUENCE_LENGTH,

                "message": (
                    f"Need "
                    f"{SEQUENCE_LENGTH - len(self.sequence)} "
                    f"more samples."
                )
            }


        # ----------------------------------------------------
        # Sequence shape:
        #
        # (20, 8)
        # ----------------------------------------------------

        X = np.asarray(
            self.sequence,
            dtype=np.float32
        )


        if X.shape != (
            SEQUENCE_LENGTH,
            len(FEATURE_COLUMNS)
        ):

            return {
                "status": "error",
                "message": (
                    "Invalid sequence shape: "
                    f"{X.shape}"
                )
            }


        # ----------------------------------------------------
        # Batch dimension:
        #
        # (1, 20, 8)
        # ----------------------------------------------------

        X = np.expand_dims(
            X,
            axis=0
        )


        # ----------------------------------------------------
        # LSTM reconstruction
        # ----------------------------------------------------

        reconstructed = model.predict(
            X,
            verbose=0
        )


        # ----------------------------------------------------
        # Reconstruction error
        # ----------------------------------------------------

        error = float(
            np.mean(
                np.square(
                    X - reconstructed
                )
            )
        )


        # ----------------------------------------------------
        # Anomaly detection
        # ----------------------------------------------------

        anomaly = (
            error
            > threshold
        )


        return {
            "error": error,
            "threshold": float(
                threshold
            ),
            "anomaly": bool(
                anomaly
            )
        }


    # ========================================================
    # INCIDENT TYPE
    # ========================================================

    def detect_incident(
        self,
        metrics
    ):

        cpu = float(
            metrics["cpu_usage"]
        )

        memory = float(
            metrics["memory_usage"]
        )

        disk = float(
            metrics["disk_usage"]
        )

        latency = float(
            metrics["network_latency"]
        )

        request_rate = float(
            metrics["request_rate"]
        )

        restarts = float(
            metrics["pod_restarts"]
        )

        errors = float(
            metrics["error_rate"]
        )

        response = float(
            metrics["response_time"]
        )


        # ----------------------------------------------------
        # Important:
        #
        # Pod restarts are checked first because a large
        # restart count is a strong Kubernetes incident signal.
        # ----------------------------------------------------

        if restarts >= 3:

            return "Pod Crash"


        if cpu >= 80:

            return "CPU Saturation"


        if memory >= 85:

            return "Memory Pressure"


        if disk >= 85:

            return "Disk Saturation"


        if latency >= 100:

            return "Network Failure"


        if errors >= 5:

            return "Error Storm"


        if response >= 100:

            return "High Response Time"


        if request_rate <= 0:

            return "Traffic Drop"


        return "Unknown"


    # ========================================================
    # FINAL PREDICTION
    # ========================================================

    def predict_metrics(
        self,
        metrics
    ):

        # ----------------------------------------------------
        # Validate all features
        # ----------------------------------------------------

        missing = [
            feature
            for feature in FEATURE_COLUMNS
            if feature not in metrics
        ]


        if missing:

            return {
                "status": "error",
                "message": (
                    "Missing required metrics"
                ),
                "missing_fields": missing
            }


        # ----------------------------------------------------
        # Add observation
        # ----------------------------------------------------

        try:

            self.add_metrics(
                metrics
            )

        except (
            KeyError,
            TypeError,
            ValueError
        ) as exc:

            return {
                "status": "error",
                "message": (
                    f"Invalid metric value: {exc}"
                )
            }


        # ----------------------------------------------------
        # Wait for 20 observations
        # ----------------------------------------------------

        if not self.ready():

            collected = len(
                self.sequence
            )

            return {
                "status": "waiting",

                "samples_collected":
                    collected,

                "samples_required":
                    SEQUENCE_LENGTH,

                "message": (
                    f"Collecting metrics... "
                    f"{collected}/"
                    f"{SEQUENCE_LENGTH}"
                )
            }


        # ----------------------------------------------------
        # Run prediction
        # ----------------------------------------------------

        result = self.predict()


        if (
            result.get(
                "status"
            ) == "error"
        ):

            return result


        # ----------------------------------------------------
        # Common response
        # ----------------------------------------------------

        response = {

            "status": "success",

            "samples_collected":
                len(self.sequence),

            "samples_required":
                SEQUENCE_LENGTH,

            "reconstruction_error":
                float(
                    result["error"]
                ),

            "threshold":
                float(
                    result["threshold"]
                )
        }


        # ----------------------------------------------------
        # ANOMALY
        # ----------------------------------------------------

        if result["anomaly"]:

            response.update({

                "prediction":
                    "Anomaly",

                "incident_type":
                    self.detect_incident(
                        metrics
                    )
            })

            return response


        # ----------------------------------------------------
        # NORMAL
        # ----------------------------------------------------

        response.update({

            "prediction":
                "Normal",

            "incident_type":
                "None"
        })


        return response


# ============================================================
# GLOBAL PREDICTOR
# ============================================================

predictor = AIOpsPredictor()


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("PREDICTOR TEST")
    print("=" * 70)

    test_metrics = {

        "cpu_usage":
            0.07,

        "memory_usage":
            25.93,

        "disk_usage":
            31.09,

        "network_latency":
            0.27,

        "request_rate":
            3.94,

        "pod_restarts":
            21,

        "error_rate":
            0.0,

        "response_time":
            0.32
    }


    print()
    print(
        "Raw metrics:"
    )

    for key, value in test_metrics.items():

        print(
            f"{key:20s}: {value}"
        )


    print()
    print(
        "Scaled test observation:"
    )

    test_frame = pd.DataFrame(
        [test_metrics],
        columns=FEATURE_COLUMNS
    )

    scaled_test = scaler.transform(
        test_frame
    )

    for name, value in zip(
        FEATURE_COLUMNS,
        scaled_test[0]
    ):

        print(
            f"{name:20s}: {value:.6f}"
        )


    print()
    print(
        "Running 20 observations..."
    )


    for _ in range(
        SEQUENCE_LENGTH
    ):

        result = predictor.predict_metrics(
            test_metrics
        )


    print()
    print(
        "RESULT:"
    )

    print(
        result
    )

    print()
    print("=" * 70)