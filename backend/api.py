"""FastAPI boundary for the validated seasonal demand-share workflow."""

from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

import geopandas as gpd
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TOOL_NAMES = ("refresh_fleet_analysis", "optimize_rebalancing", "evaluate_plan")

app = FastAPI(title="ScooterOps Local API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def timestamp() -> str:
    return datetime.now(ZoneInfo("America/Chicago")).isoformat()


def normalized_zone_positions(communities: list[str]) -> dict[str, dict[str, float]]:
    """Convert real community-area centroids into the existing map coordinate space."""
    areas = gpd.read_file(DATA_DIR / "chicago_community_areas.geojson")
    areas["community"] = areas["community"].str.title()
    areas = areas[areas["community"].isin(communities)].to_crs("EPSG:26916")
    areas["centroid"] = areas.geometry.centroid

    xs = areas["centroid"].x
    ys = areas["centroid"].y
    x_span = max(xs.max() - xs.min(), 1)
    y_span = max(ys.max() - ys.min(), 1)

    return {
        row["community"]: {
            "x": round(10 + 80 * (row["centroid"].x - xs.min()) / x_span, 2),
            "y": round(8 + 82 * (ys.max() - row["centroid"].y) / y_span, 2),
        }
        for _, row in areas.iterrows()
    }


def parse_tool_outputs(agent_stdout: str) -> dict[str, dict]:
    decoder = json.JSONDecoder()
    outputs: dict[str, dict] = {}

    for tool_name in TOOL_NAMES:
        marker = f"AGENT TOOL CALL -> {tool_name}"
        marker_index = agent_stdout.find(marker)
        if marker_index < 0:
            raise RuntimeError(f"The agent did not run {tool_name}.")

        json_start = agent_stdout.find("{", marker_index + len(marker))
        if json_start < 0:
            raise RuntimeError(f"The agent did not return JSON for {tool_name}.")

        try:
            payload, _ = decoder.raw_decode(agent_stdout[json_start:])
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"The agent returned invalid JSON for {tool_name}.") from exc

        if not isinstance(payload, dict):
            raise RuntimeError(f"The agent returned an invalid result for {tool_name}.")
        outputs[tool_name] = payload

    return outputs


def run_agent_workflow() -> dict:
    """Run the unchanged agent process and retain its real tool outputs."""
    agent_environment = {**os.environ, "PYTHONUTF8": "1"}
    completed = subprocess.run(
        [sys.executable, "backend/scooterops_agent.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=agent_environment,
        check=True,
    )
    tool_outputs = parse_tool_outputs(completed.stdout)
    refresh = tool_outputs["refresh_fleet_analysis"]
    optimization = tool_outputs["optimize_rebalancing"]
    validation = tool_outputs["evaluate_plan"]
    completed_at = timestamp()

    return {
        "tool_outputs": tool_outputs,
        "trace": [
            {
                "id": "scan",
                "label": "Live Fleet Scanned",
                "detail": f"{refresh['available_scooters_in_analyzed_zones']} available scooters scanned",
                "status": "complete",
                "timestamp": completed_at,
            },
            {
                "id": "seasonal-share",
                "label": "Seasonal Demand Distribution Forecasted",
                "detail": refresh["forecast_method"],
                "status": "complete",
                "timestamp": completed_at,
            },
            {
                "id": "optimize",
                "label": "Optimizer Solved",
                "detail": f"{len(optimization['moves'])} centroid-distance routes, {optimization['total_scooters_moved']} scooters",
                "status": "complete",
                "timestamp": completed_at,
            },
            {
                "id": "validate",
                "label": "Plan Validated",
                "detail": validation["status"],
                "status": "complete" if validation["constraints_passed"] else "failed",
                "timestamp": completed_at,
            },
        ],
        "recommendation": "The validated plan is ready for operator review.",
    }


def build_response(workflow: dict) -> dict:
    state = pd.read_csv(DATA_DIR / "rebalancing_candidates.csv")
    validation = workflow["tool_outputs"]["evaluate_plan"]
    optimization = workflow["tool_outputs"]["optimize_rebalancing"]
    required_columns = {
        "community",
        "available_scooters",
        "predicted_demand_share_pct",
        "supply_share_pct",
        "share_gap_pct_points",
    }
    missing_columns = required_columns.difference(state.columns)
    if missing_columns:
        raise RuntimeError(f"Seasonal demand-share fields are missing: {', '.join(sorted(missing_columns))}")

    positions = normalized_zone_positions(state["community"].tolist())
    total_supply = int(state["available_scooters"].sum())
    zones = []
    for _, row in state.sort_values("community").iterrows():
        position = positions.get(row["community"])
        if position is None:
            continue
        zones.append({
            "id": row["community"].lower().replace(" ", "-"),
            "community": row["community"],
            "available_scooters": int(row["available_scooters"]),
            "predicted_demand_share_pct": round(float(row["predicted_demand_share_pct"]), 2),
            "supply_share_pct": round(float(row["supply_share_pct"]), 2),
            "share_gap_pct_points": round(float(row["share_gap_pct_points"]), 2),
            **position,
        })

    moves = [
        {
            "id": f"route-{index + 1}",
            "source": move["source"],
            "destination": move["destination"],
            "scooters": int(move["scooters"]),
            "centroid_distance_km": float(move["centroid_distance_km"]),
        }
        for index, move in enumerate(optimization["moves"])
    ]

    return {
        "freshness_timestamp": timestamp(),
        "fleet": {
            "current_lime_scooter_supply": total_supply,
            "analyzed_community_areas": len(zones),
            "forecast_method": "Fall seasonal Lime spatial demand share",
        },
        "zones": zones,
        "moves": moves,
        "summary": {
            "total_scooters_moved": optimization["total_scooters_moved"],
            "total_centroid_scooter_km": optimization["total_centroid_scooter_km"],
            "mean_absolute_share_gap_before_pp": validation["mean_absolute_share_gap_before_pp"],
            "mean_absolute_share_gap_after_pp": validation["mean_absolute_share_gap_after_pp"],
            "spatial_imbalance_improvement_pct": validation["spatial_imbalance_improvement_pct"],
        },
        "validation": validation,
        "agent": {
            "trace": workflow["trace"],
            "recommendation": workflow["recommendation"],
        },
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/analysis")
async def run_analysis() -> dict:
    """Run the real agent and return its validated seasonal share plan."""
    try:
        workflow = await run_in_threadpool(run_agent_workflow)
        return build_response(workflow)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
