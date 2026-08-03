import joblib
import numpy as np
from pathlib import Path
from tensorflow.keras.models import load_model

# =====================================================
# Paths
# =====================================================

MODEL_DIR = Path("ai/models")

MODEL_PATH = MODEL_DIR / "lstm_autoencoder.keras"
SCALER_PATH = MODEL_DIR / "scaler.pkl"
THRESHOLD_PATH = MODEL_DIR / "threshold.pkl"

# =====================================================
# Load Resources
# =====================================================

print("Loading Model...")

model = load_model(MODEL_PATH)

print("Loading Scaler...")

scaler = joblib.load(SCALER_PATH)

print("Loading Threshold...")

threshold = joblib.load(THRESHOLD_PATH)

print("Model Loaded Successfully")

# =====================================================
# Feature Order
# =====================================================

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

# =====================================================
# Prediction Class
# =====================================================

class AIOpsPredictor:

    def __init__(self):

        self.sequence = []

    def add_metrics(self, metrics):

        values = np.array([
            metrics["cpu_usage"],
            metrics["memory_usage"],
            metrics["disk_usage"],
            metrics["network_latency"],
            metrics["request_rate"],
            metrics["pod_restarts"],
            metrics["error_rate"],
            metrics["response_time"]
        ])

        values = scaler.transform([values])[0]

        self.sequence.append(values)

        if len(self.sequence) > 20:
            self.sequence.pop(0)

    def ready(self):

        return len(self.sequence) == 20

    def predict(self):

        if not self.ready():

            return {
                "status": "waiting",
                "message": f"Need {20-len(self.sequence)} more samples."
            }

        X = np.array(self.sequence)

        X = np.expand_dims(X, axis=0)

        reconstructed = model.predict(
            X,
            verbose=0
        )

        error = np.mean(
            np.square(X - reconstructed)
        )

        anomaly = error > threshold

        return {
            "error": float(error),
            "threshold": float(threshold),
            "anomaly": bool(anomaly)
        }# =====================================================
# Incident Type Detection
# =====================================================

    def detect_incident(self, metrics):

        if metrics["cpu_usage"] > 90:
            return "CPU Saturation"

        elif metrics["memory_usage"] > 90:
            return "Memory Leak"

        elif metrics["network_latency"] > 300:
            return "Network Failure"

        elif metrics["pod_restarts"] >= 3:
            return "Pod Crash"

        elif metrics["error_rate"] > 10:
            return "Error Storm"

        else:
            return "Unknown"

# =====================================================
# Final Prediction
# =====================================================

    def predict_metrics(self, metrics):

        # Add current metrics
        self.add_metrics(metrics)

        # Wait until we have 20 samples
        if not self.ready():

            return {
                "status": "waiting",
                "samples_collected": len(self.sequence),
                "samples_required": 20,
                "message": "Collecting metrics..."
            }

        # LSTM Prediction
        result = self.predict()

        if result["anomaly"]:

            incident = self.detect_incident(metrics)

            return {
                "status": "success",
                "prediction": "Anomaly",
                "incident_type": incident,
                "reconstruction_error": result["error"],
                "threshold": result["threshold"]
            }

        return {
            "status": "success",
            "prediction": "Normal",
            "incident_type": "None",
            "reconstruction_error": result["error"],
            "threshold": result["threshold"]
        }

# =====================================================
# Predictor Object
# =====================================================

predictor = AIOpsPredictor()