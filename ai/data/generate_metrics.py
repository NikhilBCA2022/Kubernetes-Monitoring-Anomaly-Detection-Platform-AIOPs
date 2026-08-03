import random
from pathlib import Path

import pandas as pd

# ==========================================================
# Configuration
# ==========================================================

NUM_ROWS = 20000
START_TIME = "2026-01-01 00:00:00"
RANDOM_SEED = 42

random.seed(RANDOM_SEED)

OUTPUT_FILE = Path("./datasets/raw/kubernetes_metrics.csv")

SERVICES = [
    "frontend",
    "backend",
    "auth",
    "payment",
    "notification"
]

PODS_PER_SERVICE = 2

PODS = []

for service in SERVICES:
    for i in range(1, PODS_PER_SERVICE + 1):
        PODS.append(f"{service}-{i}")

INCIDENTS = [
    "CPU Saturation",
    "Memory Leak",
    "Network Failure",
    "Pod Crash",
    "Error Storm"
]

# ==========================================================
# Helper Functions
# ==========================================================

def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


def smooth(value, step, minimum, maximum):
    value += random.uniform(-step, step)
    return round(clamp(value, minimum, maximum), 2)


# ==========================================================
# Initial Metrics For Every Pod
# ==========================================================

pod_metrics = {}

for pod in PODS:

    pod_metrics[pod] = {

        "cpu_usage": random.uniform(35, 45),

        "memory_usage": random.uniform(45, 55),

        "disk_usage": random.uniform(40, 50),

        "network_latency": random.uniform(18, 24),

        "request_rate": random.uniform(220, 280),

        "pod_restarts": 0,

        "error_rate": random.uniform(0, 0.5),

        "response_time": random.uniform(70, 90)
    }


# ==========================================================
# State Engine
# ==========================================================

current_state = "Healthy"

current_incident = "None"

state_duration = random.randint(120, 250)
# ==========================================================
# Update Metrics Based On Cluster State
# ==========================================================

def update_metrics():

    global current_state
    global current_incident
    global state_duration

    # Move to next state when duration ends
    state_duration -= 1

    if state_duration <= 0:

        if current_state == "Healthy":
            current_state = "HighTraffic"
            current_incident = "None"
            state_duration = random.randint(30, 80)

        elif current_state == "HighTraffic":
            current_state = "Incident"
            current_incident = random.choice(INCIDENTS)
            state_duration = random.randint(10, 25)

        elif current_state == "Incident":
            current_state = "Recovery"
            state_duration = random.randint(20, 40)

        elif current_state == "Recovery":
            current_state = "Healthy"
            current_incident = "None"
            state_duration = random.randint(120, 250)

    # ------------------------------------------------------
    # Update Every Pod
    # ------------------------------------------------------

    for pod in PODS:

        m = pod_metrics[pod]

        # ---------------------------
        # HEALTHY
        # ---------------------------

        if current_state == "Healthy":

            m["cpu_usage"] = smooth(m["cpu_usage"], 2, 30, 55)
            m["memory_usage"] = smooth(m["memory_usage"], 1.5, 40, 60)
            m["disk_usage"] = smooth(m["disk_usage"], 0.5, 35, 65)
            m["network_latency"] = smooth(m["network_latency"], 1, 15, 30)
            m["request_rate"] = smooth(m["request_rate"], 10, 180, 350)
            m["response_time"] = smooth(m["response_time"], 3, 50, 120)
            m["error_rate"] = smooth(m["error_rate"], 0.1, 0, 1)
            m["pod_restarts"] = 0

        # ---------------------------
        # HIGH TRAFFIC
        # ---------------------------

        elif current_state == "HighTraffic":

            m["cpu_usage"] = smooth(m["cpu_usage"], 4, 55, 80)
            m["memory_usage"] = smooth(m["memory_usage"], 3, 60, 80)
            m["disk_usage"] = smooth(m["disk_usage"], 1, 45, 70)
            m["network_latency"] = smooth(m["network_latency"], 4, 30, 80)
            m["request_rate"] = smooth(m["request_rate"], 30, 400, 700)
            m["response_time"] = smooth(m["response_time"], 8, 120, 250)
            m["error_rate"] = smooth(m["error_rate"], 0.2, 0, 2)
            m["pod_restarts"] = 0

        # ---------------------------
        # INCIDENT
        # ---------------------------

        elif current_state == "Incident":

            if current_incident == "CPU Saturation":

                m["cpu_usage"] = smooth(m["cpu_usage"], 6, 90, 100)
                m["network_latency"] = smooth(m["network_latency"], 15, 100, 600)
                m["response_time"] = smooth(m["response_time"], 20, 300, 900)

            elif current_incident == "Memory Leak":

                m["memory_usage"] = smooth(m["memory_usage"], 5, 90, 100)
                m["response_time"] = smooth(m["response_time"], 20, 250, 800)

            elif current_incident == "Network Failure":

                m["network_latency"] = smooth(m["network_latency"], 40, 300, 1200)
                m["response_time"] = smooth(m["response_time"], 40, 500, 2000)

            elif current_incident == "Pod Crash":

                m["pod_restarts"] += random.randint(1, 2)
                m["cpu_usage"] = smooth(m["cpu_usage"], 5, 75, 95)
                m["memory_usage"] = smooth(m["memory_usage"], 5, 70, 95)
                m["response_time"] = smooth(m["response_time"], 25, 400, 1200)

            elif current_incident == "Error Storm":

                m["error_rate"] = smooth(m["error_rate"], 2, 10, 40)
                m["response_time"] = smooth(m["response_time"], 30, 300, 1200)
                m["network_latency"] = smooth(m["network_latency"], 20, 100, 700)

        # ---------------------------
        # RECOVERY
        # ---------------------------

        elif current_state == "Recovery":

            m["cpu_usage"] = smooth(m["cpu_usage"], 5, 35, 60)
            m["memory_usage"] = smooth(m["memory_usage"], 4, 45, 65)
            m["disk_usage"] = smooth(m["disk_usage"], 1, 40, 60)
            m["network_latency"] = smooth(m["network_latency"], 10, 20, 60)
            m["request_rate"] = smooth(m["request_rate"], 20, 220, 400)
            m["response_time"] = smooth(m["response_time"], 20, 80, 180)
            m["error_rate"] = smooth(m["error_rate"], 1, 0, 1)
            m["pod_restarts"] = max(0, m["pod_restarts"] - 1)
# ==========================================================
# Generate Dataset
# ==========================================================

def main():

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    timestamps = pd.date_range(
        start=START_TIME,
        periods=NUM_ROWS,
        freq="min"
    )

    records = []

    for timestamp in timestamps:

        # Update cluster state and pod metrics
        update_metrics()

        # Save metrics for every pod
        for pod in PODS:

            m = pod_metrics[pod]

            service = pod.rsplit("-", 1)[0]

            records.append({
                "timestamp": timestamp,
                "service_name": service,
                "pod_name": pod,
                "cpu_usage": round(m["cpu_usage"], 2),
                "memory_usage": round(m["memory_usage"], 2),
                "disk_usage": round(m["disk_usage"], 2),
                "network_latency": round(m["network_latency"], 2),
                "request_rate": round(m["request_rate"]),
                "pod_restarts": m["pod_restarts"],
                "error_rate": round(m["error_rate"], 2),
                "response_time": round(m["response_time"], 2),
                "state": current_state,
                "incident_type": current_incident
            })

    df = pd.DataFrame(records)

    df.to_csv(OUTPUT_FILE, index=False)

    print("=" * 70)
    print(" Kubernetes Metrics Dataset Generated Successfully")
    print("=" * 70)
    print(f"Rows Generated : {len(df):,}")
    print(f"Columns        : {len(df.columns)}")
    print(f"Pods           : {len(PODS)}")
    print(f"Services       : {len(SERVICES)}")
    print(f"Output File    : {OUTPUT_FILE}")
    print("=" * 70)

    print("\nState Distribution")
    print(df["state"].value_counts())

    print("\nIncident Distribution")
    print(df["incident_type"].value_counts())


# ==========================================================
# Entry Point
# ==========================================================

if __name__ == "__main__":
    main()