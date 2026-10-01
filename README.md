# ScooterOps

Live scooter fleet intelligence for Chicago.

ScooterOps combines **live Lime GBFS supply**, **historical seasonal demand**, a **50-scooter MILP rebalancing optimizer**, independent validation, and **Amazon Bedrock** orchestration to produce an operator-ready fleet movement plan.

**Live app:**  
https://sc-a24edf9151b2402b82e78fb9aa06fd49.ecs.us-east-2.on.aws/

## How it works

```text
Live Lime supply
      +
Historical Fall trips
      ↓
Seasonal demand-share forecast
      ↓
Demand vs supply gap
      ↓
50-scooter MILP optimizer
      ↓
Independent validator
      ↓
Amazon Bedrock
      ↓
Next.js command center
```

When **Refresh Plan** runs, ScooterOps:

1. Reads the current Lime fleet.
2. Forecasts demand share across 10 Chicago community areas.
3. Identifies relatively over- and under-supplied areas.
4. Optimizes exactly 50 scooter movements.
5. Validates inventory, fleet conservation, movement budget, and imbalance improvement.
6. Returns the plan for operator review.

## Forecast validation

The production model uses Fall 2023 and Fall 2024 Lime trips and was evaluated on held-out Fall 2025 data.

| Model | Mean absolute demand-share error |
|---|---:|
| July 2024 baseline | 2.69 pp |
| Fall 2024 benchmark | 2.60 pp |
| **Fall 2023–2024 model** | **2.37 pp** |

On that holdout, the seasonal model reduced error by about **12% versus the July baseline**.

## Optimization

ScooterOps uses `scipy.optimize.milp`.

Constraints include:

- exactly 50 scooters moved
- integer movements
- source inventory limits
- fleet conservation

Distance is based on **community-area centroids**, not road-network distance.

## AWS

```text
GitHub
  ↓
AWS CodeBuild
  ↓
Amazon ECR
  ↓
Amazon ECS Express Mode
```

AWS services used:

- Amazon Bedrock
- Amazon ECS Express Mode
- Amazon ECR
- AWS CodeBuild
- AWS IAM
- Amazon CloudWatch

The frontend is Next.js. The backend is FastAPI.

## Built with Codex

Codex was used during development for implementation, debugging, testing, and AWS deployment.

One important iteration was replacing an initial July-based demand model after questioning whether it was appropriate for a Fall deployment. The final version uses same-season historical data and held-out validation.

The production application uses ECS IAM task-role credentials. The development environment was also connected to AWS through the AWS MCP setup.

## Run locally

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

## Hackathon

Built for **Zero to Shipped 2026**.

**Category:** Workplace Efficiency  
**Lane:** Startup

#workplace-efficiency #startup