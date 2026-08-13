import os
import random
import joblib
import numpy as np
import pandas as pd

from pathlib import Path

import tensorflow as tf

from sklearn.preprocessing import MinMaxScaler

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


# ============================================================
# REPRODUCIBILITY
# ============================================================

SEED = 42

random.seed(SEED)
np.random.seed(SEED)
tf.random.set_seed(SEED)


# ============================================================
# PROJECT PATHS
# ============================================================

# train_model.py:
#
# aiops-platform/
#   ai/
#     training/
#       train_model.py
#
# parents[0] = training
# parents[1] = ai
# parents[2] = aiops-platform

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET_PATH = (
    PROJECT_ROOT
    / "datasets"
    / "processed"
    / "kubernetes_metrics_processed.csv"
)

MODEL_DIR = PROJECT_ROOT / "models"

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)

MODEL_PATH = MODEL_DIR / "lstm_autoencoder.keras"
SCALER_PATH = MODEL_DIR / "scaler.pkl"
THRESHOLD_PATH = MODEL_DIR / "threshold.pkl"


# ============================================================
# CONFIGURATION
# ============================================================

SEQUENCE_LENGTH = 20

EPOCHS = 30

BATCH_SIZE = 64

VALIDATION_RATIO = 0.20

THRESHOLD_PERCENTILE = 99.0


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
# CREATE SEQUENCES
# ============================================================

def create_sequences(data, sequence_length):

    sequences = []

    if len(data) < sequence_length:
        return np.empty(
            (0, sequence_length, len(FEATURE_COLUMNS)),
            dtype=np.float32
        )

    for i in range(
        len(data) - sequence_length + 1
    ):

        sequences.append(
            data[
                i:i + sequence_length
            ]
        )

    return np.asarray(
        sequences,
        dtype=np.float32
    )


# ============================================================
# LOAD DATASET
# ============================================================

print()
print("=" * 70)
print("LOADING DATASET")
print("=" * 70)

if not DATASET_PATH.exists():

    raise FileNotFoundError(
        f"\nDataset not found:\n{DATASET_PATH}"
    )

df = pd.read_csv(DATASET_PATH)

print(
    "Dataset Shape:",
    df.shape
)


# ============================================================
# VALIDATE FEATURES
# ============================================================

missing_features = [
    feature
    for feature in FEATURE_COLUMNS
    if feature not in df.columns
]

if missing_features:

    raise ValueError(
        "Missing required features:\n"
        + "\n".join(
            missing_features
        )
    )


# ============================================================
# VALIDATE REQUIRED COLUMNS
# ============================================================

if "pod_name" not in df.columns:

    raise ValueError(
        "Dataset must contain 'pod_name'."
    )

if "timestamp" not in df.columns:

    raise ValueError(
        "Dataset must contain 'timestamp'."
    )


# ============================================================
# CONVERT FEATURES TO NUMERIC
# ============================================================

for feature in FEATURE_COLUMNS:

    df[feature] = pd.to_numeric(
        df[feature],
        errors="coerce"
    )


df = df.dropna(
    subset=FEATURE_COLUMNS
).copy()


# ============================================================
# SORT DATA
# ============================================================

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    errors="coerce"
)

df = df.dropna(
    subset=["timestamp"]
).copy()

df = df.sort_values(
    [
        "pod_name",
        "timestamp"
    ]
).reset_index(drop=True)


# ============================================================
# SELECT NORMAL DATA
# ============================================================

print()
print("=" * 70)
print("SELECTING NORMAL BEHAVIOUR")
print("=" * 70)


normal_df = None


# ------------------------------------------------------------
# Case 1:
# state column contains strings
# ------------------------------------------------------------

if "state" in df.columns:

    state_values = df["state"].dropna()

    if len(state_values) > 0:

        if pd.api.types.is_numeric_dtype(
            state_values
        ):

            # ------------------------------------------------
            # Numeric state.
            #
            # Try the project's encoder.
            # ------------------------------------------------

            encoder_candidates = [
                PROJECT_ROOT
                / "models"
                / "encoders.pkl",

                PROJECT_ROOT
                / "ai"
                / "models"
                / "encoders.pkl"
            ]

            encoder_path = None

            for candidate in encoder_candidates:

                if candidate.exists():

                    encoder_path = candidate
                    break

            if encoder_path:

                try:

                    encoders = joblib.load(
                        encoder_path
                    )

                    state_encoder = encoders[
                        "state_encoder"
                    ]

                    healthy_label = (
                        state_encoder
                        .transform(
                            ["Healthy"]
                        )[0]
                    )

                    traffic_label = (
                        state_encoder
                        .transform(
                            ["HighTraffic"]
                        )[0]
                    )

                    normal_df = df[
                        (df["state"] == healthy_label)
                        |
                        (df["state"] == traffic_label)
                    ].copy()

                except Exception as exc:

                    print(
                        "WARNING: Could not use "
                        f"state encoder: {exc}"
                    )

            else:

                print(
                    "WARNING: encoders.pkl not found."
                )

        else:

            # ------------------------------------------------
            # String state.
            # ------------------------------------------------

            normal_states = [
                "Healthy",
                "HighTraffic"
            ]

            normal_df = df[
                df["state"]
                .astype(str)
                .isin(normal_states)
            ].copy()


# ------------------------------------------------------------
# Fallback:
# if no usable state filtering was possible
# ------------------------------------------------------------

if normal_df is None or len(normal_df) == 0:

    print(
        "WARNING: Normal-state filtering "
        "could not be applied."
    )

    print(
        "Using the complete dataset."
    )

    normal_df = df.copy()


print(
    "Normal Training Rows:",
    len(normal_df)
)


if len(normal_df) == 0:

    raise ValueError(
        "No training data available."
    )


# ============================================================
# BUILD RAW TRAINING / VALIDATION DATA
# ============================================================

print()
print("=" * 70)
print("BUILDING TRAINING AND VALIDATION DATA")
print("=" * 70)


train_frames = []
validation_frames = []

train_sequence_count = 0
validation_sequence_count = 0


for pod in normal_df["pod_name"].unique():

    pod_df = normal_df[
        normal_df["pod_name"] == pod
    ].copy()

    pod_df = pod_df.sort_values(
        "timestamp"
    )

    values = pod_df[
        FEATURE_COLUMNS
    ].values.astype(
        np.float32
    )

    if len(values) < SEQUENCE_LENGTH:

        continue

    split_index = int(
        len(values)
        * (1.0 - VALIDATION_RATIO)
    )

    # Ensure both sections can form sequences.
    if split_index < SEQUENCE_LENGTH:
        continue

    if (
        len(values) - split_index
        < SEQUENCE_LENGTH
    ):
        continue

    train_values = values[
        :split_index
    ]

    validation_values = values[
        split_index:
    ]

    train_frames.append(
        pd.DataFrame(
            train_values,
            columns=FEATURE_COLUMNS
        )
    )

    validation_frames.append(
        pd.DataFrame(
            validation_values,
            columns=FEATURE_COLUMNS
        )
    )


if not train_frames:

    raise ValueError(
        "Could not create training data."
    )


if not validation_frames:

    raise ValueError(
        "Could not create validation data."
    )


raw_train_df = pd.concat(
    train_frames,
    ignore_index=True
)

raw_validation_df = pd.concat(
    validation_frames,
    ignore_index=True
)


# ============================================================
# FIT SCALER
# ============================================================

print()
print("=" * 70)
print("FITTING SCALER")
print("=" * 70)


scaler = MinMaxScaler(
    feature_range=(0, 1),
    clip=True
)


# IMPORTANT:
# Fit using a DataFrame so sklearn stores
# feature_names_in_ and inference can use
# the exact same feature names.

scaler.fit(
    raw_train_df[
        FEATURE_COLUMNS
    ]
)


# ============================================================
# TRANSFORM DATA
# ============================================================

scaled_train = scaler.transform(
    raw_train_df[
        FEATURE_COLUMNS
    ]
)

scaled_validation = scaler.transform(
    raw_validation_df[
        FEATURE_COLUMNS
    ]
)


print(
    "Scaler fitted on:",
    len(raw_train_df),
    "rows"
)

print()
print(
    "Scaler Feature Order:"
)

print(
    list(
        scaler.feature_names_in_
    )
)


print()
print(
    "Training Data Range After Scaling:"
)

print(
    "MIN:",
    np.min(
        scaled_train,
        axis=0
    )
)

print(
    "MAX:",
    np.max(
        scaled_train,
        axis=0
    )
)


# ============================================================
# CREATE SEQUENCES
# ============================================================

X_train = create_sequences(
    scaled_train,
    SEQUENCE_LENGTH
)

X_validation = create_sequences(
    scaled_validation,
    SEQUENCE_LENGTH
)


print()
print(
    "Training Sequences:",
    X_train.shape
)

print(
    "Validation Sequences:",
    X_validation.shape
)


if len(X_train) == 0:

    raise ValueError(
        "No training sequences created."
    )

if len(X_validation) == 0:

    raise ValueError(
        "No validation sequences created."
    )


# ============================================================
# BUILD LSTM AUTOENCODER
# ============================================================

print()
print("=" * 70)
print("BUILDING LSTM AUTOENCODER")
print("=" * 70)


timesteps = X_train.shape[1]

features = X_train.shape[2]


inputs = Input(
    shape=(
        timesteps,
        features
    )
)


# ------------------------------------------------------------
# Encoder
# ------------------------------------------------------------

x = LSTM(
    64,
    activation="tanh",
    return_sequences=True
)(inputs)

x = Dropout(
    0.20
)(x)

x = LSTM(
    32,
    activation="tanh",
    return_sequences=False
)(x)


# ------------------------------------------------------------
# Bottleneck
# ------------------------------------------------------------

x = RepeatVector(
    timesteps
)(x)


# ------------------------------------------------------------
# Decoder
# ------------------------------------------------------------

x = LSTM(
    32,
    activation="tanh",
    return_sequences=True
)(x)

x = Dropout(
    0.20
)(x)

x = LSTM(
    64,
    activation="tanh",
    return_sequences=True
)(x)


outputs = TimeDistributed(
    Dense(features)
)(x)


model = Model(
    inputs,
    outputs
)


model.compile(
    optimizer="adam",
    loss="mse"
)


model.summary()


# ============================================================
# TRAIN
# ============================================================

print()
print("=" * 70)
print("TRAINING MODEL")
print("=" * 70)


early_stopping = EarlyStopping(
    monitor="val_loss",
    patience=5,
    restore_best_weights=True
)


history = model.fit(

    X_train,

    X_train,

    validation_data=(
        X_validation,
        X_validation
    ),

    epochs=EPOCHS,

    batch_size=BATCH_SIZE,

    shuffle=True,

    callbacks=[
        early_stopping
    ],

    verbose=1
)


# ============================================================
# VALIDATION RECONSTRUCTION ERROR
# ============================================================

print()
print("=" * 70)
print("CALCULATING VALIDATION RECONSTRUCTION ERROR")
print("=" * 70)


reconstructed = model.predict(
    X_validation,
    verbose=0
)


validation_errors = np.mean(
    np.square(
        X_validation
        - reconstructed
    ),
    axis=(1, 2)
)


minimum_error = float(
    validation_errors.min()
)

maximum_error = float(
    validation_errors.max()
)

average_error = float(
    validation_errors.mean()
)

median_error = float(
    np.median(validation_errors)
)

std_error = float(
    validation_errors.std()
)


print(
    f"Minimum Error : {minimum_error:.8f}"
)

print(
    f"Maximum Error : {maximum_error:.8f}"
)

print(
    f"Average Error : {average_error:.8f}"
)

print(
    f"Median Error  : {median_error:.8f}"
)

print(
    f"Std Error     : {std_error:.8f}"
)


# ============================================================
# CALCULATE THRESHOLD
# ============================================================

threshold = float(
    np.percentile(
        validation_errors,
        THRESHOLD_PERCENTILE
    )
)


three_sigma = float(
    average_error
    + 3.0 * std_error
)


print()
print(
    f"Threshold Percentile: "
    f"{THRESHOLD_PERCENTILE:.1f}%"
)

print(
    f"Percentile Threshold: "
    f"{threshold:.8f}"
)

print(
    f"3-Sigma Threshold: "
    f"{three_sigma:.8f}"
)


# ============================================================
# SAVE MODEL
# ============================================================

print()
print("=" * 70)
print("SAVING MODEL ARTIFACTS")
print("=" * 70)


model.save(
    MODEL_PATH
)


joblib.dump(
    scaler,
    SCALER_PATH
)


joblib.dump(
    threshold,
    THRESHOLD_PATH
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
    "THRESHOLD:",
    THRESHOLD_PATH
)


# ============================================================
# VERIFY SAVED FILES
# ============================================================

print()
print("=" * 70)
print("VERIFYING SAVED ARTIFACTS")
print("=" * 70)


if not MODEL_PATH.exists():
    raise RuntimeError(
        "Model was not saved."
    )

if not SCALER_PATH.exists():
    raise RuntimeError(
        "Scaler was not saved."
    )

if not THRESHOLD_PATH.exists():
    raise RuntimeError(
        "Threshold was not saved."
    )


print(
    "Model size:",
    MODEL_PATH.stat().st_size,
    "bytes"
)

print(
    "Scaler size:",
    SCALER_PATH.stat().st_size,
    "bytes"
)

print(
    "Threshold size:",
    THRESHOLD_PATH.stat().st_size,
    "bytes"
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print()
print("=" * 70)
print("TRAINING SUMMARY")
print("=" * 70)

print(
    f"Training Sequences   : "
    f"{len(X_train):,}"
)

print(
    f"Validation Sequences : "
    f"{len(X_validation):,}"
)

print(
    f"Sequence Length      : "
    f"{SEQUENCE_LENGTH}"
)

print(
    f"Features              : "
    f"{features}"
)

print(
    f"Epochs Completed      : "
    f"{len(history.history['loss'])}"
)

print(
    f"Final Training Loss   : "
    f"{history.history['loss'][-1]:.8f}"
)

print(
    f"Final Validation Loss : "
    f"{history.history['val_loss'][-1]:.8f}"
)

print(
    f"Threshold             : "
    f"{threshold:.8f}"
)

print()
print("=" * 70)
print("LSTM AUTOENCODER TRAINING COMPLETED SUCCESSFULLY")
print("=" * 70)