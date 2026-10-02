# ScooterOps

**Live fleet conditions → optimized scooter movements → independently validated plan**

ScooterOps is a live scooter fleet rebalancing system for Chicago.

It combines **Lime’s live scooter availability**, **seasonal demand forecasting**, mathematical optimization, independent validation, and **Amazon Bedrock** orchestration to answer a practical operations question:

> **What should we move, where should it go, and does the move actually improve the fleet?**

**Live app:**  
https://sc-a24edf9151b2402b82e78fb9aa06fd49.ecs.us-east-2.on.aws/

**Demo video:**  
https://www.youtube.com/watch?v=aTYBKz-0XVM

## What ScooterOps does

ScooterOps is not another fleet map.

When a plan is generated, it:

1. Reads the current Lime scooter fleet.
2. Forecasts demand share across 10 Chicago community areas.
3. Compares predicted demand with current supply.
4. Identifies relatively over- and under-supplied areas.
5. Optimizes exactly **50 scooter movements**.
6. Validates source inventory, fleet conservation, movement budget, and imbalance improvement.
7. Returns the validated plan for operator review.

The result changes as fleet conditions change.

## How it works

```text
Live Lime scooter availability
        +
Historical Fall trips
        ↓
Seasonal demand-share forecast
        ↓
Demand vs. supply gap
        ↓
50-scooter optimizer
        ↓
Independent validator
        ↓
Amazon Bedrock
        ↓
FastAPI backend
        ↓
Next.js command center
```

Amazon Bedrock coordinates the analytical workflow, while forecasting, optimization, and validation remain separate and inspectable components.

## Forecast validation

The production model uses Fall 2023 and Fall 2024 Lime trips and was evaluated on held-out Fall 2025 data.

| Model | Mean absolute demand-share error |
|---|---:|
| July 2024 baseline | 2.69 pp |
| Fall 2024 benchmark | 2.60 pp |
| **Fall 2023–2024 model** | **2.37 pp** |

On that holdout, the seasonal model reduced mean absolute spatial demand-share error by about **12% versus the July baseline**.

## Optimization and validation

ScooterOps uses `scipy.optimize.milp` to generate the rebalancing plan.

The optimizer enforces:

- exactly 50 scooters moved
- integer-valued movements
- source inventory limits
- fleet conservation

Movement distance is based on **Chicago community-area centroids**, not road-network driving distance.

The optimizer does not approve its own result. A separate validation step checks the plan and only returns **APPROVED** when the required constraints pass and spatial imbalance improves.

## AWS deployment

```text
GitHub
  ↓
AWS CodeBuild
  ↓
Amazon ECR
  ↓
Amazon ECS Express Mode
  ↓
Public HTTPS application
```

AWS services used:

- **Amazon Bedrock** — workflow orchestration
- **Amazon ECS Express Mode** — frontend and backend deployment
- **Amazon ECR** — container images
- **AWS CodeBuild** — builds from GitHub
- **AWS IAM** — runtime permissions
- **Amazon CloudWatch** — logs and observability

The frontend is built with **Next.js** and the backend with **FastAPI**.

## Built with Codex

Codex was used throughout development for implementation, debugging, testing, and AWS deployment.

The coding-agent environment was also connected to AWS through the AWS MCP setup during development.

The final production application uses standard ECS task-role credentials for AWS access.

## Run locally

### Backend

```powershell
.\.venv\Scripts\python.exe -m uvicorn api:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
cd frontend
pnpm install
pnpm dev -- --port 3000
```

## Hackathon

Built for **Zero to Shipped 2026**.

**Category:** Workplace Efficiency  
**Lane:** Startup

#workplace-efficiency #startup