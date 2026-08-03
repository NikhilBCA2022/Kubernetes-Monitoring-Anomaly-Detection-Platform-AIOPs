import joblib
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import LabelEncoder, MinMaxScaler

# =====================================================
# Paths
# =====================================================

RAW_DATA = Path("./datasets/raw/kubernetes_metrics.csv")
PROCESSED_DATA = Path("./datasets/processed/kubernetes_metrics_processed.csv")

MODEL_DIR = Path("./ai/models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

SCALER_PATH = MODEL_DIR / "scaler.pkl"
ENCODER_PATH = MODEL_DIR / "encoders.pkl"

# =====================================================
# Main
# =====================================================

def main():

    print("=" * 60)
    print("Loading Dataset...")
    print("=" * 60)

    df = pd.read_csv(RAW_DATA)

    print(f"Original Shape : {df.shape}")

    # =====================================================
    # Remove Duplicates
    # =====================================================

    duplicates = df.duplicated().sum()

    if duplicates > 0:
        df = df.drop_duplicates()

    print(f"Duplicates Removed : {duplicates}")

    # =====================================================
    # Missing Values
    # =====================================================

    print("\nMissing Values Before Cleaning\n")
    print(df.isnull().sum())

    # incident_type should be None for healthy rows
    df["incident_type"] = df["incident_type"].fillna("None")

    numeric_columns = [
        "cpu_usage",
        "memory_usage",
        "disk_usage",
        "network_latency",
        "request_rate",
        "pod_restarts",
        "error_rate",
        "response_time"
    ]

    # Forward-fill only numeric columns if needed
    df[numeric_columns] = df[numeric_columns].ffill()

    print("\nMissing Values After Cleaning\n")
    print(df.isnull().sum())

    # =====================================================
    # Encode Categorical Columns
    # =====================================================

    service_encoder = LabelEncoder()
    pod_encoder = LabelEncoder()
    state_encoder = LabelEncoder()
    incident_encoder = LabelEncoder()

    df["service_name"] = service_encoder.fit_transform(df["service_name"])
    df["pod_name"] = pod_encoder.fit_transform(df["pod_name"])
    df["state"] = state_encoder.fit_transform(df["state"])
    df["incident_type"] = incident_encoder.fit_transform(df["incident_type"])

    # Save encoders
    encoders = {
        "service_encoder": service_encoder,
        "pod_encoder": pod_encoder,
        "state_encoder": state_encoder,
        "incident_encoder": incident_encoder,
    }

    joblib.dump(encoders, ENCODER_PATH)

    # =====================================================
    # Scale Features
    # =====================================================

    feature_columns = [
        "cpu_usage",
        "memory_usage",
        "disk_usage",
        "network_latency",
        "request_rate",
        "pod_restarts",
        "error_rate",
        "response_time"
    ]

    scaler = MinMaxScaler()

    df[feature_columns] = scaler.fit_transform(df[feature_columns])

    joblib.dump(scaler, SCALER_PATH)

    # =====================================================
    # Save Processed Dataset
    # =====================================================

    PROCESSED_DATA.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(PROCESSED_DATA, index=False)

    print("\nProcessed Shape :", df.shape)

    print(f"\nProcessed Dataset Saved : {PROCESSED_DATA}")
    print(f"Scaler Saved            : {SCALER_PATH}")
    print(f"Encoders Saved          : {ENCODER_PATH}")

    print("=" * 60)
    print("Preprocessing Completed Successfully")
    print("=" * 60)


if __name__ == "__main__":
    main()