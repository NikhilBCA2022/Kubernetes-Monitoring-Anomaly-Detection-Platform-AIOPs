# AIOps Kubernetes Monitoring Platform

An end-to-end AIOps platform that uses an **LSTM Autoencoder** deep learning model to detect anomalies in Kubernetes cluster metrics in real time. The platform is deployable on both **Azure (AKS)** and **AWS (EKS)** with full infrastructure-as-code, CI/CD pipelines, and observability stack.

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
- [Getting Started](#getting-started)
- [Tech Stack](#tech-stack)

---

## Overview

This platform continuously monitors Kubernetes pod metrics (CPU, memory, network, etc.), feeds them into a trained LSTM Autoencoder, and classifies each data point as **Normal** or **Anomaly**. When an anomaly is detected, the system also identifies the incident type (e.g., CPU Saturation, Memory Leak, Pod Crash).

---

## Architecture

```
Kubernetes Metrics
       │
       ▼
  Flask REST API  ──►  LSTM Autoencoder  ──►  Anomaly / Normal
       │                                            │
       ▼                                            ▼
  /predict endpoint                        Incident Classification
                                     (CPU Saturation / Memory Leak /
                                      Network Failure / Pod Crash /
                                      Error Storm)
```

**Infrastructure layers:**

```
Azure                          AWS
─────────────────────          ─────────────────────
AKS  ◄─── ACR                  EKS  ◄─── ECR
 │                              │
Key Vault                      Secrets Manager
 │                              │
Log Analytics                  CloudWatch
 │                              │
Azure Monitor                  IAM Roles
 │                              │
VNet / NSGs                    VPC / Security Groups
```

---

## Features

- **Real-time anomaly detection** using LSTM Autoencoder on 8 Kubernetes metrics
- **Incident type classification** — identifies the root cause category automatically
- **REST API** with Flask + Gunicorn, containerised with Docker
- **Azure infrastructure** provisioned via Bicep (AKS, ACR, Key Vault, VNet, Monitoring, VM)
- **AWS infrastructure** provisioned via Terraform (EKS, ECR, VPC, IAM, CloudWatch)
- **Ansible** playbooks for post-provisioning configuration
- **Kubernetes manifests** for AKS and EKS deployments
- **Observability** with Prometheus, Grafana, Loki, and Tempo
- **CI/CD** with GitHub Actions and Azure DevOps pipelines

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
│   │   ├── predict.py              # Inference logic
│   │   └── app.py                  # Inference Flask app
│   └── models/                     # Trained model artifacts (gitignored)
│
├── app/                            # Production API
│   ├── app.py                      # Flask application
│   ├── predict.py                  # AIOpsPredictor class
│   ├── requirements.txt            # Python dependencies
│   ├── Dockerfile                  # App container image
│   └── models/                     # Runtime model artifacts (gitignored)
│
├── datasets/
│   ├── raw/                        # Raw generated metrics CSV (gitignored)
│   └── processed/                  # Preprocessed dataset (gitignored)
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
│   │   └── parameters/
│   │       ├── dev.bicepparam      # Dev environment parameters
│   │       └── prod.bicepparam     # Prod environment parameters
│   │
│   └── aws/
│       ├── terraform/              # AWS Terraform IaC
│       │   ├── main.tf             # Provider config & backend
│       │   ├── variables.tf        # Input variables
│       │   ├── outputs.tf          # Output values
│       │   ├── vpc.tf              # VPC, subnets, routing
│       │   ├── eks.tf              # EKS cluster & node groups
│       │   ├── ecr.tf              # Elastic Container Registry
│       │   ├── iam.tf              # IAM roles & policies
│       │   ├── cloudwatch.tf       # CloudWatch log groups & alarms
│       │   └── security.tf         # Security groups
│       │
│       └── ansible/                # Post-provisioning config
│           ├── inventory           # Host inventory (gitignored)
│           ├── playbooks/          # Ansible playbooks
│           └── roles/              # Reusable Ansible roles
│
├── kubernetes/
│   ├── aks/                        # AKS manifests
│   │   ├── namespace.yaml
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── configmap.yaml
│   │   └── ingress.yaml
│   ├── eks/                        # EKS manifests
│   └── base/                       # Shared base manifests
│
├── monitoring/
│   ├── prometheus/                 # Prometheus config & rules
│   ├── grafana/                    # Grafana dashboards
│   ├── loki/                       # Loki log aggregation config
│   └── tempo/                      # Tempo distributed tracing config
│
├── github-actions/
│   └── deploy.yml                  # CI/CD workflow
│
├── azure-devops/                   # Azure DevOps pipeline definitions
├── argocd/                         # ArgoCD app definitions
├── automation/                     # Helper scripts
├── docs/                           # Documentation
│
├── Dockerfile                      # Root Dockerfile
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

### `GET /health`
Health check endpoint.

```json
{
  "status": "healthy",
  "model_loaded": true
}
```

### `GET /info`
Returns model and application metadata.

```json
{
  "application": "AIOps Kubernetes Monitoring Platform",
  "model": "LSTM Autoencoder",
  "sequence_length": 20,
  "features": 8,
  "purpose": "Kubernetes anomaly detection"
}
```

### `POST /predict`
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

---

## Infrastructure

### Azure (Bicep)

Deploys the full Azure environment using modular Bicep templates.

**Resources provisioned:**

| Module | Resources |
|---|---|
| `network.bicep` | VNet, 4 subnets (AKS, AppGW, Bastion, Private Endpoints), NSGs |
| `aks.bicep` | AKS cluster with system + user node pools |
| `acr.bicep` | Azure Container Registry with AcrPull role for AKS |
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

**Resources provisioned:**

| File | Resources |
|---|---|
| `vpc.tf` | VPC, public/private subnets, route tables, NAT Gateway |
| `eks.tf` | EKS cluster, managed node groups |
| `ecr.tf` | Elastic Container Registry |
| `iam.tf` | IAM roles for EKS, node groups, pod identities |
| `cloudwatch.tf` | Log groups, metric alarms |
| `security.tf` | Security groups for EKS, nodes, ALB |

**Deploy with Terraform:**

```bash
cd infra/aws/terraform

terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

**Configure with Ansible:**

```bash
cd infra/aws/ansible

# Update inventory with provisioned host IPs
ansible-playbook -i inventory playbooks/setup.yml
```

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
kubectl apply -f kubernetes/aks/ingress.yaml

# Check pods
kubectl get pods -n aiops
```

The deployment runs **2 replicas** with:
- CPU: 500m request / 1 core limit
- Memory: 1Gi request / 2Gi limit
- Readiness probe: `GET /health` after 60s
- Liveness probe: `GET /health` every 20s

---

## Monitoring Stack

| Tool | Purpose |
|---|---|
| **Prometheus** | Metrics collection and alerting |
| **Grafana** | Dashboards and visualisation |
| **Loki** | Log aggregation |
| **Tempo** | Distributed tracing |

Config files are located under `monitoring/`.

---

## Getting Started

### Prerequisites

- Python 3.11+
- Docker
- kubectl
- Azure CLI / AWS CLI
- Terraform >= 1.5
- Ansible >= 2.14

### Run Locally

```bash
# Clone the repository
git clone https://github.com/<your-username>/aiops-platform.git
cd aiops-platform

# Install dependencies
pip install -r app/requirements.txt

# Run the API
cd app
python app.py
```

### Run with Docker

```bash
# Build image
docker build -t aiops-platform-api:latest .

# Run container
docker run -p 5000:5000 aiops-platform-api:latest
```

### Test the API

```bash
python test_prediction.py
```

---

## Tech Stack

| Category | Technology |
|---|---|
| ML Framework | TensorFlow / Keras |
| API | Flask, Gunicorn |
| Containerisation | Docker |
| Orchestration | Kubernetes (AKS / EKS) |
| Azure IaC | Bicep |
| AWS IaC | Terraform |
| Configuration | Ansible |
| CI/CD | GitHub Actions, Azure DevOps |
| GitOps | ArgoCD |
| Monitoring | Prometheus, Grafana, Loki, Tempo |
| Container Registry | Azure ACR, AWS ECR |
| Secrets | Azure Key Vault |
| Data Processing | Pandas, NumPy, Scikit-learn |

---

## License

This project is licensed under the terms of the [LICENSE](LICENSE) file.
