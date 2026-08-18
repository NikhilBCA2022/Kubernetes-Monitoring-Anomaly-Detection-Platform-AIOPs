# AIOps Kubernetes Monitoring Platform

An end-to-end AIOps platform that uses an **LSTM Autoencoder** deep learning model to detect anomalies in Kubernetes cluster metrics in real time. The platform is deployable on **Azure (AKS)** with full infrastructure-as-code, a live Prometheus metrics pipeline, and an observability stack via the kube-prometheus-stack Helm chart.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Project Structure](#project-structure)
- [ML Model](#ml-model)
- [API Reference](#api-reference)
- [Infrastructure](#infrastructure)
  - [Azure (Bicep)](#azure-bicep)
  - [AWS (Terraform + Ansible)](#aws-terraform--ansible)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Monitoring Stack](#monitoring-stack)
- [CI/CD Pipeline](#cicd-pipeline)
- [Getting Started](#getting-started)
- [Tech Stack](#tech-stack)

---

## Overview

This platform continuously monitors Kubernetes pod metrics (CPU, memory, network, etc.), feeds them into a trained LSTM Autoencoder, and classifies each data point as **Normal** or **Anomaly**. When an anomaly is detected, the system also identifies the incident type (e.g., CPU Saturation, Memory Leak, Pod Crash).

The production API integrates directly with a live Prometheus instance to collect real-time metrics from the cluster via PromQL queries, in addition to accepting manual metric submissions.

---

## Architecture

```
Kubernetes Cluster
       │
       ▼
  Prometheus (kube-prometheus-stack)
       │
       ▼
  Flask REST API  ──►  LSTM Autoencoder  ──►  Anomaly / Normal
       │                                            │
       ▼                                            ▼
  Web Dashboard (/predict)               Incident Classification
  Live API (/api/predict-live)     (CPU Saturation / Memory Leak /
                                    Network Failure / Pod Crash /
                                    Error Storm)
```

**Infrastructure layers:**

```
Azure
─────────────────────
AKS  ◄─── ACR (nikhilaiopsacr2026.azurecr.io)
 │
Key Vault
 │
Log Analytics
 │
Azure Monitor
 │
VNet / NSGs
 │
Storage Account

AWS (scaffold — Terraform files present, not yet populated)
─────────────────────
EKS / ECR / VPC / IAM / CloudWatch
```

---

## Features

- **Real-time anomaly detection** using LSTM Autoencoder on 8 Kubernetes metrics
- **Incident type classification** — identifies the root cause category automatically
- **Live Prometheus integration** — collects metrics directly from a running Prometheus instance via PromQL
- **Web dashboard** — browser-based prediction UI served via Flask templates
- **REST API** with Flask + Gunicorn, containerised with Docker
- **Azure infrastructure** provisioned via Bicep (AKS, ACR, Key Vault, VNet, Monitoring, VM, Storage)
- **AWS infrastructure** — Terraform scaffold present (files created, not yet populated)
- **Ansible** playbooks scaffold for post-provisioning configuration
- **Kubernetes manifests** for AKS deployment (namespace, deployment, service, configmap, ingress, ServiceMonitor)
- **Observability** with kube-prometheus-stack Helm chart (Prometheus, Grafana, Alertmanager, node-exporter, kube-state-metrics)
- **ServiceMonitor** for automatic Prometheus scraping of the AIOps API at `/metrics`
- **CI/CD pipeline** via GitHub Actions — lint, Docker build/push to ACR, rolling deploy to AKS with automatic rollback

---

## Project Structure

```
aiops-platform/
│
├── ai/                             # ML pipeline
│   ├── data/
│   │   └── generate_metrics.py     # Synthetic Kubernetes metrics generator
│   ├── training/
│   │   ├── train_model.py          # LSTM Autoencoder training script
│   │   └── preprocess.py           # Data preprocessing & feature engineering
│   ├── inference/
│   │   ├── predict.py              # Inference logic (shared with app/)
│   │   └── app.py                  # Minimal inference-only Flask app
│   └── models/                     # Trained model artifacts (gitignored)
│       ├── lstm_autoencoder.keras
│       ├── scaler.pkl
│       └── encoders.pkl
│
├── app/                            # Production API
│   ├── app.py                      # Flask application (all routes)
│   ├── predict.py                  # AIOpsPredictor class
│   ├── prometheus_collector.py     # Live PromQL metric collector
│   ├── collect_metrics.py          # Metric collection helpers
│   ├── metrics_normalizer.py       # Feature normalisation utilities
│   ├── test.py                     # Quick local test script
│   ├── requirements.txt            # Python dependencies
│   ├── Dockerfile                  # App container image (python:3.11-slim)
│   ├── templates/                  # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── health.html
│   │   ├── info.html
│   │   └── predict.html            # Interactive prediction dashboard
│   ├── static/
│   │   └── style.css               # Application styles
│   └── models/                     # Runtime model artifacts (gitignored)
│       ├── lstm_autoencoder.keras
│       ├── scaler.pkl
│       └── threshold.pkl
│
├── models/                         # Root-level model artifacts
│   ├── lstm_autoencoder.keras
│   ├── scaler.pkl
│   └── threshold.pkl
│
├── datasets/
│   ├── raw/
│   │   └── kubernetes_metrics.csv          # Raw generated metrics (~19 MB)
│   └── processed/
│       ├── kubernetes_metrics_processed.csv  # Preprocessed dataset (~34 MB)
│       └── prometheus_metrics.csv            # Live-collected Prometheus data
│
├── infra/
│   ├── azure/                      # Azure Bicep IaC
│   │   ├── main.bicep              # Orchestrator — deploys all modules
│   │   ├── network.bicep           # VNet, subnets, NSGs
│   │   ├── aks.bicep               # AKS cluster
│   │   ├── acr.bicep               # Azure Container Registry
│   │   ├── keyvault.bicep          # Key Vault
│   │   ├── monitoring.bicep        # Log Analytics + Azure Monitor
│   │   ├── vm.bicep                # Jump / bastion VM
│   │   ├── storage.bicep           # Storage account
│   │   ├── main.json               # Compiled ARM template
│   │   └── parameters/
│   │       ├── dev.bicepparam      # Dev environment parameters
│   │       └── prod.bicepparam     # Prod environment parameters (empty)
│   │
│   └── aws/
│       ├── terraform/              # AWS Terraform scaffold (files empty)
│       │   ├── main.tf
│       │   ├── variables.tf
│       │   ├── outputs.tf
│       │   ├── vpc.tf
│       │   ├── eks.tf
│       │   ├── ecr.tf
│       │   ├── iam.tf
│       │   ├── cloudwatch.tf
│       │   └── security.tf
│       │
│       └── ansible/                # Ansible scaffold (empty)
│           ├── inventory
│           ├── playbooks/
│           └── roles/
│
├── kubernetes/
│   └── aks/                        # AKS manifests
│       ├── namespace.yaml          # aiops namespace
│       ├── deployment.yaml         # 2 replicas, ACR image
│       ├── service.yaml            # LoadBalancer on port 80 → 5000
│       ├── configmap.yaml
│       ├── ingress.yaml            # (empty)
│       └── aiops-servicemonitor.yaml  # Prometheus ServiceMonitor
│
├── kube-prometheus-stack/          # Helm chart for observability stack
│   ├── Chart.yaml
│   ├── Chart.lock
│   ├── values.yaml
│   ├── charts/                     # Sub-charts
│   │   ├── grafana/
│   │   ├── kube-state-metrics/
│   │   ├── prometheus-node-exporter/
│   │   ├── prometheus-windows-exporter/
│   │   └── crds/
│   └── templates/                  # Helm templates
│       ├── prometheus/
│       ├── grafana/
│       ├── alertmanager/
│       ├── prometheus-operator/
│       └── thanos-ruler/
│
├── monitoring/                     # Monitoring config stubs
│   ├── prometheus/
│   ├── grafana/
│   ├── loki/
│   └── tempo/
│
├── automation/
│   └── kubernetes_monitor.py       # Kubernetes API monitor (in-cluster/local)
│
├── .github/
│   └── workflows/
│       └── deploy.yml              # GitHub Actions CI/CD (lint → build → deploy)
│
├── github-actions/
│   └── deploy.yml                  # CI/CD workflow source copy
│
├── azure-devops/                   # Azure DevOps pipeline stubs
├── argocd/                         # ArgoCD app stubs
├── docs/
│
├── Dockerfile                      # Root Dockerfile (empty)
├── test_prediction.py              # Manual prediction test script
├── .gitignore
└── README.md
```

---

## ML Model

### Model: LSTM Autoencoder

The model learns the **normal behaviour** of Kubernetes pods and flags sequences that deviate significantly from that baseline.

| Property | Value |
|---|---|
| Architecture | LSTM Autoencoder |
| Sequence Length | 20 time steps |
| Input Features | 8 |
| Encoder | LSTM(64) → Dropout(0.2) → LSTM(32) |
| Decoder | LSTM(32) → Dropout(0.2) → LSTM(64) → Dense(8) |
| Loss Function | Mean Squared Error (MSE) |
| Anomaly Threshold | mean + 3 × std of reconstruction error |
| Saved as | `lstm_autoencoder.keras` + `scaler.pkl` + `threshold.pkl` |

### Input Features

| Feature | Description |
|---|---|
| `cpu_usage` | CPU utilisation (%) |
| `memory_usage` | Memory utilisation (%) |
| `disk_usage` | Disk utilisation (%) |
| `network_latency` | Network latency (ms) |
| `request_rate` | Requests per second |
| `pod_restarts` | Number of pod restarts |
| `error_rate` | Error rate (%) |
| `response_time` | API response time (ms) |

### Incident Types Detected

| Incident | Trigger Condition |
|---|---|
| CPU Saturation | `cpu_usage > 90%` |
| Memory Leak | `memory_usage > 90%` |
| Network Failure | `network_latency > 300ms` |
| Pod Crash | `pod_restarts >= 3` |
| Error Storm | `error_rate > 10%` |

### Training

```bash
# Generate synthetic dataset
python ai/data/generate_metrics.py

# Preprocess data
python ai/training/preprocess.py

# Train LSTM Autoencoder
python ai/training/train_model.py
```

---

## API Reference

Base URL: `http://localhost:5000`

### Web UI Routes (HTML)

| Route | Method | Description |
|---|---|---|
| `GET /` | GET | Home page |
| `GET /health` | GET | Health dashboard (HTML) |
| `GET /info` | GET | Model info page (HTML) |
| `GET /predict` | GET | Prediction form dashboard |
| `POST /predict` | POST | Submit metrics via form or JSON |

### JSON API Routes

#### `GET /api/health`
Returns API and model health status.

```json
{
  "status": "Healthy",
  "model_loaded": true,
  "model_name": "LSTM Autoencoder",
  "model_stage": "Production",
  "api_status": "Running"
}
```

#### `GET /api/info`
Returns model and application metadata.

```json
{
  "application": "AIOps Kubernetes Monitoring Platform",
  "model": "LSTM Autoencoder",
  "model_stage": "Production",
  "sequence_length": 20,
  "features": 8,
  "metrics": ["cpu_usage", "memory_usage", "disk_usage", "network_latency",
              "request_rate", "pod_restarts", "error_rate", "response_time"]
}
```

#### `POST /predict`
Submit a metrics snapshot for anomaly detection.

**Request body:**
```json
{
  "cpu_usage": 45.2,
  "memory_usage": 60.1,
  "disk_usage": 30.5,
  "network_latency": 12.3,
  "request_rate": 120.0,
  "pod_restarts": 0,
  "error_rate": 0.5,
  "response_time": 85.0
}
```

**Response — Normal:**
```json
{
  "status": "success",
  "prediction": "Normal",
  "incident_type": "None",
  "reconstruction_error": 0.00021,
  "threshold": 0.00189
}
```

**Response — Anomaly:**
```json
{
  "status": "success",
  "prediction": "Anomaly",
  "incident_type": "CPU Saturation",
  "reconstruction_error": 0.00412,
  "threshold": 0.00189
}
```

**Response — Collecting (first 20 samples):**
```json
{
  "status": "waiting",
  "samples_collected": 5,
  "samples_required": 20,
  "message": "Collecting metrics..."
}
```

#### `GET /api/predict-live`
Fetches live metrics from the connected Prometheus instance and runs a prediction automatically.

```json
{
  "status": "success",
  "metrics": {
    "cpu_usage": 42.1,
    "memory_usage": 55.3,
    "...": "..."
  },
  "prediction": {
    "status": "success",
    "prediction": "Normal",
    "incident_type": "None",
    "reconstruction_error": 0.00018,
    "threshold": 0.00189
  }
}
```

#### `POST /api/predict-reset`
Clears the internal LSTM sequence buffer (resets the 20-sample sliding window).

```json
{
  "status": "success",
  "message": "Prediction sequence reset",
  "samples_collected": 0,
  "samples_required": 20
}
```

#### `GET /metrics`
Exposes Prometheus-format metrics for scraping (via `prometheus-flask-exporter`).

---

## Infrastructure

### Azure (Bicep)

Deploys the full Azure environment using modular Bicep templates.

**Resources provisioned:**

| Module | Resources |
|---|---|
| `network.bicep` | VNet, subnets (AKS, AppGW, Bastion, Private Endpoints), NSGs |
| `aks.bicep` | AKS cluster with system + user node pools |
| `acr.bicep` | Azure Container Registry (`nikhilaiopsacr2026.azurecr.io`) |
| `keyvault.bicep` | Key Vault with RBAC, soft delete, purge protection |
| `monitoring.bicep` | Log Analytics Workspace, Azure Monitor |
| `vm.bicep` | Jump VM for cluster access |
| `storage.bicep` | Storage account for model artifacts |

**Deploy to Azure:**

```bash
# Deploy dev environment
az deployment group create \
  --resource-group rg-aiops-dev \
  --template-file infra/azure/main.bicep \
  --parameters infra/azure/parameters/dev.bicepparam

# Deploy prod environment
az deployment group create \
  --resource-group rg-aiops-prod \
  --template-file infra/azure/main.bicep \
  --parameters infra/azure/parameters/prod.bicepparam
```

### AWS (Terraform + Ansible)

The AWS Terraform and Ansible scaffolding is in place (all files created under `infra/aws/`) but the content has not yet been populated. The intended resources are:

| File | Resources |
|---|---|
| `vpc.tf` | VPC, public/private subnets, route tables, NAT Gateway |
| `eks.tf` | EKS cluster, managed node groups |
| `ecr.tf` | Elastic Container Registry |
| `iam.tf` | IAM roles for EKS, node groups, pod identities |
| `cloudwatch.tf` | Log groups, metric alarms |
| `security.tf` | Security groups for EKS, nodes, ALB |

---

## Kubernetes Deployment

### AKS

```bash
# Get AKS credentials
az aks get-credentials --resource-group rg-aiops-dev --name aiops-aks-dev

# Apply manifests
kubectl apply -f kubernetes/aks/namespace.yaml
kubectl apply -f kubernetes/aks/configmap.yaml
kubectl apply -f kubernetes/aks/deployment.yaml
kubectl apply -f kubernetes/aks/service.yaml
kubectl apply -f kubernetes/aks/aiops-servicemonitor.yaml

# Check pods
kubectl get pods -n aiops
```

The deployment runs **2 replicas** with:
- Image: `nikhilaiopsacr2026.azurecr.io/aiops-api:v4`
- CPU: 500m request / 1 core limit
- Memory: 1Gi request / 2Gi limit
- Readiness probe: `GET /health` after 60s, every 10s
- Liveness probe: `GET /health` after 90s, every 20s
- Service type: `LoadBalancer` (port 80 → container port 5000)

### ServiceMonitor

A `ServiceMonitor` resource (`kubernetes/aks/aiops-servicemonitor.yaml`) is included for the kube-prometheus-stack Prometheus operator. It scrapes the `/metrics` endpoint every 15 seconds from the `aiops` namespace.

---

## Monitoring Stack

The `kube-prometheus-stack` Helm chart (v88.2.0) is included in the repository and provides the full observability stack.

| Component | Purpose |
|---|---|
| **Prometheus** | Metrics collection, PromQL, alerting rules |
| **Grafana** | Dashboards and visualisation |
| **Alertmanager** | Alert routing and notifications |
| **kube-state-metrics** | Kubernetes object state metrics |
| **prometheus-node-exporter** | Node-level metrics (CPU, memory, disk) |
| **Prometheus Operator** | Manages Prometheus/Alertmanager via CRDs |

**Install with Helm:**

```bash
# Install the kube-prometheus-stack from the local chart
helm install prometheus-stack ./kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace

# Or upgrade an existing release
helm upgrade prometheus-stack ./kube-prometheus-stack \
  --namespace monitoring
```

Additional monitoring configs (Loki, Tempo, custom Prometheus rules) are stubbed under `monitoring/`.

---

## CI/CD Pipeline

The workflow lives at `.github/workflows/deploy.yml` (mirrored to `github-actions/deploy.yml`) and runs automatically on every push or pull request to `master`/`main` that touches `app/**` or `kubernetes/aks/**`.

### Jobs

| Job | Trigger | Steps |
|---|---|---|
| **Lint & Test** | push + PR | Python 3.11 setup, pip install, flake8 lint, pytest |
| **Build & Push** | push only | Docker build from `./app`, push to ACR with `sha-<commit>` and `latest` tags |
| **Deploy** | push only | Azure login, AKS credentials, `kubectl set image`, rollout wait, smoke test |

### Pipeline flow

```
push to master/main
        │
        ▼
  ┌─────────────┐
  │  Lint & Test │  (runs on push AND pull_request)
  └──────┬──────┘
         │ pass
         ▼
  ┌──────────────────┐
  │  Build & Push     │  docker build ./app → ACR
  │  sha-<commit>     │  nikhilaiopsacr2026.azurecr.io/aiops-api:sha-<commit>
  │  + latest tag     │
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────────────────────────┐
  │  Deploy to AKS                        │
  │  kubectl set image → rollout wait     │
  │  smoke test GET /api/health           │
  └──────┬───────────────────────────────┘
         │ failure at any step
         ▼
  kubectl rollout undo  (automatic rollback)
```

### Required GitHub Secrets

Add these under **Settings → Secrets and variables → Actions** in your GitHub repository:

| Secret | Value |
|---|---|
| `ACR_USERNAME` | Azure portal → ACR → Access keys → Username |
| `ACR_PASSWORD` | Azure portal → ACR → Access keys → Password |
| `AZURE_CREDENTIALS` | Output of `az ad sp create-for-rbac --name aiops-github --role contributor --scopes /subscriptions/<sub-id>/resourceGroups/rg-aiops-dev --sdk-auth` |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Docker
- kubectl
- Azure CLI
- Helm 3+
- Terraform >= 1.5 (for AWS, when populated)

### Run Locally

```bash
# Clone the repository
git clone https://github.com/<your-username>/aiops-platform.git
cd aiops-platform

# Install dependencies
pip install -r app/requirements.txt

# Copy model artifacts into app/models/
cp models/* app/models/

# Run the API
cd app
python app.py
```

The API will start at `http://localhost:5000`. It will attempt to connect to Prometheus at `http://localhost:9090` by default. Override with:

```bash
PROMETHEUS_URL=http://your-prometheus:9090 python app.py
```

### Run with Docker

```bash
# Build image from app/ directory
docker build -t aiops-api:latest ./app

# Run container
docker run -p 5000:5000 \
  -e PROMETHEUS_URL=http://your-prometheus:9090 \
  aiops-api:latest
```

### Test the API

```bash
# Run the manual test script
python test_prediction.py

# Or test with curl
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "cpu_usage": 95.0,
    "memory_usage": 60.0,
    "disk_usage": 30.0,
    "network_latency": 15.0,
    "request_rate": 100.0,
    "pod_restarts": 0,
    "error_rate": 0.5,
    "response_time": 80.0
  }'
```

---

## Tech Stack

| Category | Technology |
|---|---|
| ML Framework | TensorFlow 2.16 / Keras |
| API | Flask 3.0, Gunicorn |
| Containerisation | Docker (python:3.11-slim) |
| Orchestration | Kubernetes (AKS) |
| Azure IaC | Bicep |
| AWS IaC | Terraform (scaffold) |
| Configuration | Ansible (scaffold) |
| CI/CD | GitHub Actions (lint → build → deploy) |
| Monitoring | kube-prometheus-stack (Prometheus, Grafana, Alertmanager) |
| Metrics Export | prometheus-flask-exporter |
| Container Registry | Azure ACR |
| Secrets | Azure Key Vault |
| Data Processing | Pandas, NumPy, Scikit-learn 1.6 |
| Kubernetes Client | kubernetes-python |

---

## License

This project is licensed under the terms of the [LICENSE](LICENSE) file.
