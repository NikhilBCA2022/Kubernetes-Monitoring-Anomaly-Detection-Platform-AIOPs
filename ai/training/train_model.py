import joblib
import numpy as np
import pandas as pd
from pathlib import Path

from tensorflow.keras.models import Model
from tensorflow.keras.layers import (
    Input,
    LSTM,
    Dense,
    RepeatVector,
    TimeDistributed,
    Dropout
)
from tensorflow.keras.callbacks import EarlyStopping

import matplotlib.pyplot as plt

# =====================================================
# Paths
# =====================================================

DATASET_PATH = Path(
    "./datasets/processed/kubernetes_metrics_processed.csv"
)

MODEL_DIR = Path("./ai/models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODEL_DIR / "lstm_autoencoder.keras"
THRESHOLD_PATH = MODEL_DIR / "threshold.pkl"

# =====================================================
# Configuration
# =====================================================

SEQUENCE_LENGTH = 20
EPOCHS = 20
BATCH_SIZE = 64

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
# Create Sequences
# =====================================================

def create_sequences(data, sequence_length):

    sequences = []

    for i in range(len(data) - sequence_length + 1):

        sequence = data[i:i + sequence_length]

        sequences.append(sequence)

    return np.array(sequences)

# =====================================================
# Load Dataset
# =====================================================

print("=" * 60)
print("Loading Processed Dataset")
print("=" * 60)

df = pd.read_csv(DATASET_PATH)

print("Dataset Shape :", df.shape)

# =====================================================
# Use Only Normal Behaviour
# =====================================================

encoders = joblib.load(
    "aiops-platform/ai/models/encoders.pkl"
)

state_encoder = encoders["state_encoder"]

healthy_label = state_encoder.transform(["Healthy"])[0]
traffic_label = state_encoder.transform(["HighTraffic"])[0]

normal_df = df[
    (df["state"] == healthy_label) |
    (df["state"] == traffic_label)
].copy()

print("Training Rows :", len(normal_df))

# =====================================================
# Create Sequences Per Pod
# =====================================================

X = []

for pod in normal_df["pod_name"].unique():

    pod_df = normal_df[
        normal_df["pod_name"] == pod
    ].copy()

    pod_df = pod_df.sort_values("timestamp")

    values = pod_df[FEATURE_COLUMNS].values

    sequences = create_sequences(
        values,
        SEQUENCE_LENGTH
    )

    if len(sequences) > 0:

        X.extend(sequences)

X = np.array(X)

print("Training Sequences :", X.shape)# =====================================================
# Build LSTM Autoencoder
# =====================================================

print("\n" + "=" * 60)
print("Building LSTM Autoencoder")
print("=" * 60)

timesteps = X.shape[1]
features = X.shape[2]

inputs = Input(shape=(timesteps, features))

# ---------------- Encoder ----------------

x = LSTM(
    64,
    activation="tanh",
    return_sequences=True
)(inputs)

x = Dropout(0.2)(x)

x = LSTM(
    32,
    activation="tanh",
    return_sequences=False
)(x)

# Bottleneck
encoded = RepeatVector(timesteps)(x)

# ---------------- Decoder ----------------

x = LSTM(
    32,
    activation="tanh",
    return_sequences=True
)(encoded)

x = Dropout(0.2)(x)

x = LSTM(
    64,
    activation="tanh",
    return_sequences=True
)(x)

outputs = TimeDistributed(
    Dense(features)
)(x)

model = Model(inputs, outputs)

model.compile(
    optimizer="adam",
    loss="mse"
)

model.summary()

# =====================================================
# Train Model
# =====================================================

print("\n" + "=" * 60)
print("Training Model")
print("=" * 60)

early_stopping = EarlyStopping(
    monitor="val_loss",
    patience=5,
    restore_best_weights=True
)

history = model.fit(

    X,
    X,

    epochs=EPOCHS,

    batch_size=BATCH_SIZE,

    validation_split=0.2,

    shuffle=True,

    callbacks=[early_stopping],

    verbose=1
)

# =====================================================
# Plot Training Loss
# =====================================================

plt.figure(figsize=(8,5))

plt.plot(
    history.history["loss"],
    label="Training Loss"
)

plt.plot(
    history.history["val_loss"],
    label="Validation Loss"
)

plt.xlabel("Epoch")
plt.ylabel("Loss")
plt.title("LSTM Autoencoder Training")

plt.legend()

plt.grid(True)

plt.show()# =====================================================
# Reconstruction Error
# =====================================================

print("\n" + "=" * 60)
print("Calculating Reconstruction Error")
print("=" * 60)

reconstructed = model.predict(X, verbose=0)

reconstruction_error = np.mean(
    np.square(X - reconstructed),
    axis=(1, 2)
)

print(f"Minimum Error : {reconstruction_error.min():.6f}")
print(f"Maximum Error : {reconstruction_error.max():.6f}")
print(f"Average Error : {reconstruction_error.mean():.6f}")

# =====================================================
# Calculate Threshold
# =====================================================

threshold = (
    reconstruction_error.mean()
    + 3 * reconstruction_error.std()
)

print(f"\nAnomaly Threshold : {threshold:.6f}")

# =====================================================
# Save Model
# =====================================================

model.save(MODEL_PATH)

joblib.dump(threshold, THRESHOLD_PATH)

print("\nModel Saved Successfully")
print(MODEL_PATH)

print("\nThreshold Saved Successfully")
print(THRESHOLD_PATH)

# =====================================================
# Training Summary
# =====================================================

print("\n" + "=" * 60)
print("Training Summary")
print("=" * 60)

print(f"Training Sequences : {X.shape[0]:,}")
print(f"Sequence Length    : {SEQUENCE_LENGTH}")
print(f"Features           : {X.shape[2]}")
print(f"Epochs Completed   : {len(history.history['loss'])}")
print(f"Final Training Loss: {history.history['loss'][-1]:.6f}")
print(f"Final Validation Loss: {history.history['val_loss'][-1]:.6f}")

print("=" * 60)
print("LSTM Autoencoder Training Completed Successfully")
print("=" * 60)