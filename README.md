# ScooterOps

**Autonomous scooter fleet rebalancing for Chicago**

ScooterOps continuously combines live Lime fleet supply with historical seasonal demand patterns, identifies where relative demand is likely to outpace supply, generates an optimized 50-scooter rebalancing plan, and independently validates that the plan improves fleet balance.

## Live Demo

**Production app:**  
https://sc-a24edf9151b2402b82e78fb9aa06fd49.ecs.us-east-2.on.aws/

The application is deployed on AWS using Amazon ECS Express Mode.

## What It Does

ScooterOps runs an end-to-end fleet operations workflow:

1. Scans the live Lime GBFS feed for currently available scooters.
2. Forecasts spatial demand share across selected Chicago community areas using historical Fall Lime trip data.
3. Compares forecast demand share with current live supply share.
4. Identifies relatively over-supplied and under-supplied areas.
5. Solves a mixed-integer optimization problem for a fixed 50-scooter movement budget.
6. Independently validates fleet conservation, source inventory, movement budget, and improvement in spatial imbalance.
7. Uses Amazon Bedrock to orchestrate the workflow and return a validated operator-ready plan.

Live results change as fleet supply and time-of-day demand patterns change.

## Architecture

```text
Live Lime GBFS supply
        +
Historical Fall Lime trips
        ↓
Seasonal spatial demand-share forecast
        ↓
Demand share vs live supply share
        ↓
50-scooter MILP optimizer
        ↓
Independent validator
        ↓
Amazon Bedrock agent orchestration
        ↓
FastAPI backend
        ↓
Next.js command center
        ↓
Amazon ECS Express Mode
```

## Demand Forecast

ScooterOps forecasts **where demand is distributed**, rather than attempting to predict an absolute number of trips.

For each analyzed community area it estimates:

```text
predicted demand share
vs
current live supply share
```

The difference is the spatial supply-demand gap.

A positive gap indicates that an area has less relative scooter supply than its predicted share of demand.

A negative gap indicates relatively excess supply.

### Historical validation

The seasonal model was trained using Fall 2023 and Fall 2024 Lime trips and evaluated on a held-out Fall 2025 period.

Mean absolute spatial demand-share error:

```text
July 2024 baseline:          2.69 percentage points
Fall 2023-2024 model:       2.37 percentage points
Fall 2024-only benchmark:   2.60 percentage points
```

On that Fall 2025 holdout, the same-season model reduced mean absolute spatial demand-share error by about **12% versus the July baseline**.

## Optimization

The optimizer uses `scipy.optimize.milp` to determine scooter movements between relatively over-supplied and under-supplied areas.

Constraints include:

- exactly 50 scooters moved
- no source can provide more scooters than are available
- fleet inventory is conserved
- movements are integer-valued

The objective minimizes movement distance while satisfying the rebalancing allocation.

Distances are based on **Chicago community-area centroid distance**, not road-network driving distance.

## Independent Validation

A proposed plan is approved only when it passes checks for:

- movement budget
- source inventory
- fleet conservation
- spatial supply-demand gap improvement

The validator compares mean absolute demand-share versus supply-share gap before and after the proposed movements.

The UI labels the plan `APPROVED` only when all checks pass.

## Amazon Bedrock

Amazon Bedrock orchestrates three application tools:

```text
refresh_fleet_analysis
optimize_rebalancing
evaluate_plan
```

The agent coordinates live fleet analysis, optimization, and independent validation before returning the final recommendation.

The application does **not** physically dispatch scooters. The generated plan is presented for operator review.

## AWS Deployment

ScooterOps uses:

- **Amazon ECR** for backend and frontend container images
- **AWS CodeBuild** to build container images from GitHub
- **Amazon ECS Express Mode** for public container deployment
- **AWS IAM task roles** for runtime Bedrock access
- **Amazon Bedrock** for agent orchestration
- **CloudWatch** for AWS service logging and observability

Production flow:

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

## Technology

### Backend

- Python
- FastAPI
- SciPy MILP
- pandas
- GeoPandas / Shapely
- boto3
- Amazon Bedrock

### Frontend

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS
- driver.js

### Data

- Lime GBFS live fleet feed
- City of Chicago historical scooter trip data
- Chicago community-area boundaries

## Local Development

Backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
pnpm install
pnpm dev -- --port 3000
```

The frontend proxy uses:

```text
SCOOTEROPS_API_URL
```

to reach the production backend.

## Hackathon

Built for **Zero to Shipped 2026**.

**Category:** Workplace Efficiency  
**Lane:** Startup

ScooterOps demonstrates how live operational data, optimization, independent validation, and an AI agent can be combined into a deployable fleet-operations decision system.

#workplace-efficiency #startup