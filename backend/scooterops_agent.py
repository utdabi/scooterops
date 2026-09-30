import boto3
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

session = boto3.Session(
    profile_name="scooterops",
    region_name="us-east-1"
)

client = session.client("bedrock-runtime")


def run_script(script):
    result = subprocess.run(
        [sys.executable, script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True
    )

    return result.stdout


# --------------------------------------------------
# TOOL 1
# Refresh live fleet + demand-pressure analysis
# --------------------------------------------------

def refresh_fleet_analysis():

    run_script("backend/live_supply.py")
    run_script("backend/build_lime_imbalance.py")
    run_script("backend/prepare_rebalancing.py")

    df = pd.read_csv(
        ROOT / "data/rebalancing_candidates.csv"
    )

    destinations = (
        df[df["need_score"] > 0]
        .sort_values("need_score", ascending=False)
        .head(5)
    )

    sources = (
        df[df["need_score"] < 0]
        .sort_values("need_score")
        .head(5)
    )

    return {
        "available_scooters_in_analyzed_zones":
            int(df["available_scooters"].sum()),

        "predicted_hourly_demand":
            round(float(df["predicted_demand"].sum()), 2),

        "highest_need_zones": [
            {
                "community": row["community"],
                "predicted_demand":
                    round(float(row["predicted_demand"]), 2),
                "available_scooters":
                    int(row["available_scooters"]),
                "need_score":
                    round(float(row["need_score"]), 3)
            }
            for _, row in destinations.iterrows()
        ],

        "strongest_source_zones": [
            {
                "community": row["community"],
                "available_scooters":
                    int(row["available_scooters"]),
                "need_score":
                    round(float(row["need_score"]), 3)
            }
            for _, row in sources.iterrows()
        ]
    }


# --------------------------------------------------
# TOOL 2
# Run deterministic MILP optimizer
# --------------------------------------------------

def optimize_rebalancing():

    output = run_script(
        "backend/optimize_rebalancing.py"
    )

    plan = pd.read_csv(
        ROOT / "data/rebalancing_plan.csv"
    )

    moved_match = re.search(
        r"Total scooters moved:\s*([\d.]+)",
        output
    )

    km_match = re.search(
        r"Total scooter-km:\s*([\d.]+)",
        output
    )

    improvement_match = re.search(
        r"Pressure imbalance improvement:\s*([\d.]+)",
        output
    )

    return {
        "moves": [
            {
                "source": row["source"],
                "destination": row["destination"],
                "scooters": int(row["scooters"]),
                "centroid_distance_km":
                    round(float(row["distance_km"]), 2)
            }
            for _, row in plan.iterrows()
        ],

        "total_scooters_moved":
            int(float(moved_match.group(1)))
            if moved_match else None,

        "total_centroid_scooter_km":
            float(km_match.group(1))
            if km_match else None,

        "pressure_imbalance_improvement_pct":
            float(improvement_match.group(1))
            if improvement_match else None
    }


# --------------------------------------------------
# TOOL 3
# Independently validate optimizer result
# --------------------------------------------------

def evaluate_plan():

    state = pd.read_csv(
        ROOT / "data/rebalancing_candidates.csv"
    ).set_index("community")

    plan = pd.read_csv(
        ROOT / "data/rebalancing_plan.csv"
    )

    before = state.copy()
    after = state.copy()

    errors = []

    total_moved = int(plan["scooters"].sum())

    if total_moved > 50:
        errors.append(
            "Rebalancing budget exceeded."
        )

    for _, move in plan.iterrows():

        source = move["source"]
        destination = move["destination"]
        scooters = int(move["scooters"])

        if source not in after.index:
            errors.append(
                f"Unknown source zone: {source}"
            )
            continue

        if destination not in after.index:
            errors.append(
                f"Unknown destination zone: {destination}"
            )
            continue

        after.loc[
            source,
            "available_scooters"
        ] -= scooters

        after.loc[
            destination,
            "available_scooters"
        ] += scooters

    if (
        after["available_scooters"] < 0
    ).any():
        errors.append(
            "A source zone would have negative supply."
        )

    target_pressure = (
        before["predicted_demand"].sum()
        /
        before["available_scooters"].sum()
    )

    before_pressure = (
        before["predicted_demand"]
        /
        before["available_scooters"]
    )

    after_pressure = (
        after["predicted_demand"]
        /
        after["available_scooters"]
    )

    before_gap = (
        before_pressure - target_pressure
    ).abs().mean()

    after_gap = (
        after_pressure - target_pressure
    ).abs().mean()

    improvement = (
        (before_gap - after_gap)
        / before_gap
        * 100
    )

    if improvement <= 0:
        errors.append(
            "Plan does not improve demand-pressure balance."
        )

    return {
        "status":
            "APPROVED" if not errors else "REJECTED",

        "constraints_passed":
            len(errors) == 0,

        "total_scooters_moved":
            total_moved,

        "move_budget":
            50,

        "pressure_imbalance_improvement_pct":
            round(float(improvement), 2),

        "errors":
            errors
    }


TOOLS = {
    "refresh_fleet_analysis":
        refresh_fleet_analysis,

    "optimize_rebalancing":
        optimize_rebalancing,

    "evaluate_plan":
        evaluate_plan
}


tool_config = {
    "tools": [
        {
            "toolSpec": {
                "name": "refresh_fleet_analysis",
                "description": (
                    "Refresh the real Lime scooter fleet, "
                    "combine it with the demand forecast, "
                    "and identify high-need and surplus zones."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "optimize_rebalancing",
                "description": (
                    "Run the deterministic mixed-integer "
                    "rebalancing optimizer. It chooses how "
                    "to move at most 50 scooters while "
                    "minimizing centroid-distance movement."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "evaluate_plan",
                "description": (
                    "Independently validate the proposed "
                    "rebalancing plan against movement "
                    "constraints and measure whether demand "
                    "pressure improves."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                }
            }
        }
    ]
}


system_prompt = """
You are ScooterOps, an autonomous fleet operations agent.

Your job is to analyze the current Lime scooter fleet in Chicago
and produce a validated rebalancing recommendation.

Operational numbers must come only from tools.

Required workflow:
1. Refresh the live fleet analysis.
2. Run the deterministic optimizer.
3. Evaluate the generated plan.
4. Only recommend the plan if evaluation returns APPROVED.

Do not invent scooter counts, distances, demand, improvements,
or destinations.

Distance values are community-area centroid-distance proxies,
not road-route distances.

In the final answer be concise.
State:
- the highest-pressure zones
- the recommended scooter movements
- total scooters moved
- centroid scooter-km
- measured pressure-imbalance improvement
- validation status
"""


messages = [
    {
        "role": "user",
        "content": [
            {
                "text":
                    "Analyze the current fleet and produce "
                    "a validated rebalancing recommendation."
            }
        ]
    }
]


while True:

    response = client.converse(
        modelId=MODEL_ID,
        system=[
            {
                "text": system_prompt
            }
        ],
        messages=messages,
        toolConfig=tool_config,
        inferenceConfig={
            "maxTokens": 800,
            "temperature": 0
        }
    )

    message = response["output"]["message"]
    messages.append(message)

    if response["stopReason"] != "tool_use":
        break

    tool_results = []

    for content in message["content"]:

        if "toolUse" not in content:
            continue

        tool_use = content["toolUse"]

        name = tool_use["name"]
        tool_use_id = tool_use["toolUseId"]

        print(f"\nAGENT TOOL CALL -> {name}")

        try:
            result = TOOLS[name]()

            print(
                json.dumps(
                    result,
                    indent=2
                )
            )

            tool_result = {
                "toolUseId": tool_use_id,
                "content": [
                    {
                        "json": result
                    }
                ]
            }

        except Exception as exc:

            tool_result = {
                "toolUseId": tool_use_id,
                "content": [
                    {
                        "text": str(exc)
                    }
                ],
                "status": "error"
            }

        tool_results.append(
            {
                "toolResult": tool_result
            }
        )

    messages.append(
        {
            "role": "user",
            "content": tool_results
        }
    )


print("\n" + "=" * 60)
print("SCOOTEROPS AGENT RECOMMENDATION")
print("=" * 60)

for content in message["content"]:
    if "text" in content:
        print(content["text"])