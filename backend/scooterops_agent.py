import boto3
import json
import re
import subprocess
import sys

from pathlib import Path

import pandas as pd

from botocore.config import Config


# --------------------------------------------------
# Paths / configuration
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent

MODEL_ID = (
    "us.anthropic.claude-haiku-4-5-20251001-v1:0"
)

AWS_PROFILE = "scooterops"
AWS_REGION = "us-east-1"


# --------------------------------------------------
# AWS session
#
# Local development uses the scooterops SSO profile.
# Production AWS deployment will later use an IAM
# execution role instead of this local profile.
# --------------------------------------------------

session = boto3.Session(
    profile_name=AWS_PROFILE,
    region_name=AWS_REGION,
)


# Prevent inherited local proxy settings from
# affecting AWS credential refresh or Bedrock.
proxy_free_config = Config(
    proxies={}
)

# Apply proxy-free config to clients created through
# the underlying botocore session.
try:
    session._session.set_default_client_config(
        proxy_free_config
    )
except AttributeError:
    pass


client = session.client(
    "bedrock-runtime",
    config=proxy_free_config,
)


# --------------------------------------------------
# Utility: execute deterministic backend scripts
# --------------------------------------------------

def run_script(script):

    result = subprocess.run(
        [
            sys.executable,
            script,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    return result.stdout


# ==================================================
# TOOL 1
# Refresh live fleet + seasonal demand-share analysis
# ==================================================

def refresh_fleet_analysis():

    run_script(
        "backend/live_supply.py"
    )

    run_script(
        "backend/build_lime_imbalance.py"
    )

    run_script(
        "backend/prepare_rebalancing.py"
    )

    df = pd.read_csv(
        ROOT
        / "data/rebalancing_candidates.csv"
    )


    destinations = (
        df[
            df["need_score"] > 0
        ]
        .sort_values(
            "need_score",
            ascending=False,
        )
        .head(5)
    )


    sources = (
        df[
            df["need_score"] < 0
        ]
        .sort_values(
            "need_score"
        )
        .head(5)
    )


    return {

        "available_scooters_in_analyzed_zones":
            int(
                df[
                    "available_scooters"
                ].sum()
            ),

        "forecast_method":
            (
                "Fall seasonal Lime "
                "spatial demand share"
            ),

        "highest_need_zones": [

            {
                "community":
                    row["community"],

                "predicted_demand_share_pct":
                    round(
                        float(
                            row[
                                "predicted_demand_share_pct"
                            ]
                        ),
                        2,
                    ),

                "supply_share_pct":
                    round(
                        float(
                            row[
                                "supply_share_pct"
                            ]
                        ),
                        2,
                    ),

                "share_gap_pct_points":
                    round(
                        float(
                            row[
                                "share_gap_pct_points"
                            ]
                        ),
                        2,
                    ),

                "available_scooters":
                    int(
                        row[
                            "available_scooters"
                        ]
                    ),
            }

            for _, row
            in destinations.iterrows()
        ],


        "strongest_source_zones": [

            {
                "community":
                    row["community"],

                "predicted_demand_share_pct":
                    round(
                        float(
                            row[
                                "predicted_demand_share_pct"
                            ]
                        ),
                        2,
                    ),

                "supply_share_pct":
                    round(
                        float(
                            row[
                                "supply_share_pct"
                            ]
                        ),
                        2,
                    ),

                "share_gap_pct_points":
                    round(
                        float(
                            row[
                                "share_gap_pct_points"
                            ]
                        ),
                        2,
                    ),

                "available_scooters":
                    int(
                        row[
                            "available_scooters"
                        ]
                    ),
            }

            for _, row
            in sources.iterrows()
        ],
    }


# ==================================================
# TOOL 2
# Run deterministic MILP optimizer
# ==================================================

def optimize_rebalancing():

    output = run_script(
        "backend/optimize_rebalancing.py"
    )


    plan = pd.read_csv(
        ROOT
        / "data/rebalancing_plan.csv"
    )


    moved_match = re.search(
        r"Total scooters moved:\s*([\d.]+)",
        output,
    )


    km_match = re.search(
        r"Total centroid scooter-km:\s*([\d.]+)",
        output,
    )


    before_gap_match = re.search(
        (
            r"Mean absolute share gap before:"
            r"\s*([\d.]+)"
        ),
        output,
    )


    after_gap_match = re.search(
        (
            r"Mean absolute share gap after:"
            r"\s*([\d.]+)"
        ),
        output,
    )


    improvement_match = re.search(
        (
            r"Spatial imbalance improvement:"
            r"\s*([\d.]+)"
        ),
        output,
    )


    return {

        "moves": [

            {
                "source":
                    row["source"],

                "destination":
                    row["destination"],

                "scooters":
                    int(
                        row["scooters"]
                    ),

                "centroid_distance_km":
                    round(
                        float(
                            row[
                                "distance_km"
                            ]
                        ),
                        2,
                    ),
            }

            for _, row
            in plan.iterrows()
        ],


        "total_scooters_moved":
            (
                int(
                    float(
                        moved_match.group(1)
                    )
                )
                if moved_match
                else None
            ),


        "total_centroid_scooter_km":
            (
                float(
                    km_match.group(1)
                )
                if km_match
                else None
            ),


        "mean_absolute_share_gap_before_pp":
            (
                float(
                    before_gap_match.group(1)
                )
                if before_gap_match
                else None
            ),


        "mean_absolute_share_gap_after_pp":
            (
                float(
                    after_gap_match.group(1)
                )
                if after_gap_match
                else None
            ),


        "spatial_imbalance_improvement_pct":
            (
                float(
                    improvement_match.group(1)
                )
                if improvement_match
                else None
            ),
    }


# ==================================================
# TOOL 3
# Independently validate optimizer result
# ==================================================

def evaluate_plan():

    state = pd.read_csv(
        ROOT
        / "data/rebalancing_candidates.csv"
    ).set_index(
        "community"
    )


    plan = pd.read_csv(
        ROOT
        / "data/rebalancing_plan.csv"
    )


    before = state.copy()
    after = state.copy()

    errors = []


    total_moved = int(
        plan["scooters"].sum()
    )


    # ----------------------------------------------
    # Check move budget
    # ----------------------------------------------

    if total_moved > 50:

        errors.append(
            "Rebalancing budget exceeded."
        )


    # ----------------------------------------------
    # Apply proposed movements
    # ----------------------------------------------

    for _, move in plan.iterrows():

        source = move["source"]

        destination = (
            move["destination"]
        )

        scooters = int(
            move["scooters"]
        )


        if source not in after.index:

            errors.append(
                f"Unknown source zone: {source}"
            )

            continue


        if destination not in after.index:

            errors.append(
                (
                    "Unknown destination zone: "
                    f"{destination}"
                )
            )

            continue


        after.loc[
            source,
            "available_scooters",
        ] -= scooters


        after.loc[
            destination,
            "available_scooters",
        ] += scooters


    # ----------------------------------------------
    # Prevent impossible negative inventory
    # ----------------------------------------------

    if (
        after[
            "available_scooters"
        ] < 0
    ).any():

        errors.append(
            (
                "A source zone would have "
                "negative supply."
            )
        )


    # ----------------------------------------------
    # Fleet conservation
    # ----------------------------------------------

    total_before = (
        before[
            "available_scooters"
        ].sum()
    )


    total_after = (
        after[
            "available_scooters"
        ].sum()
    )


    if total_before != total_after:

        errors.append(
            "Total fleet supply changed."
        )


    # ----------------------------------------------
    # Calculate supply shares before / after
    # ----------------------------------------------

    before_supply_share = (
        before[
            "available_scooters"
        ]
        / total_before
    )


    after_supply_share = (
        after[
            "available_scooters"
        ]
        / total_after
    )


    # ----------------------------------------------
    # Compare supply distribution against the
    # seasonal predicted demand distribution.
    #
    # Metric:
    # mean absolute percentage-point gap
    # ----------------------------------------------

    before_gap = (

        (
            before[
                "predicted_demand_share"
            ]
            - before_supply_share
        )
        .abs()
        .mean()
        * 100
    )


    after_gap = (

        (
            after[
                "predicted_demand_share"
            ]
            - after_supply_share
        )
        .abs()
        .mean()
        * 100
    )


    # ----------------------------------------------
    # Improvement
    # ----------------------------------------------

    if before_gap > 0:

        improvement = (

            (
                before_gap
                - after_gap
            )
            / before_gap
            * 100
        )

    else:

        improvement = 0.0


    if improvement <= 0:

        errors.append(
            (
                "Plan does not improve spatial "
                "supply-demand balance."
            )
        )


    return {

        "status":
            (
                "APPROVED"
                if not errors
                else "REJECTED"
            ),

        "constraints_passed":
            len(errors) == 0,

        "total_scooters_moved":
            total_moved,

        "move_budget":
            50,

        "mean_absolute_share_gap_before_pp":
            round(
                float(before_gap),
                2,
            ),

        "mean_absolute_share_gap_after_pp":
            round(
                float(after_gap),
                2,
            ),

        "spatial_imbalance_improvement_pct":
            round(
                float(improvement),
                2,
            ),

        "errors":
            errors,
    }


# ==================================================
# Tool registry
# ==================================================

TOOLS = {

    "refresh_fleet_analysis":
        refresh_fleet_analysis,

    "optimize_rebalancing":
        optimize_rebalancing,

    "evaluate_plan":
        evaluate_plan,
}


# ==================================================
# Bedrock tool definitions
# ==================================================

tool_config = {

    "tools": [

        {
            "toolSpec": {

                "name":
                    "refresh_fleet_analysis",

                "description":
                    (
                        "Refresh the real Lime scooter "
                        "fleet, compare current supply "
                        "share with the fall seasonal "
                        "demand-share forecast, and "
                        "identify relatively under- "
                        "and over-supplied zones."
                    ),

                "inputSchema": {

                    "json": {

                        "type":
                            "object",

                        "properties":
                            {},

                        "additionalProperties":
                            False,
                    }
                },
            }
        },


        {
            "toolSpec": {

                "name":
                    "optimize_rebalancing",

                "description":
                    (
                        "Run the deterministic "
                        "mixed-integer rebalancing "
                        "optimizer. It moves at most "
                        "50 scooters and minimizes "
                        "community-area centroid "
                        "distance while reallocating "
                        "supply toward relatively "
                        "under-supplied zones."
                    ),

                "inputSchema": {

                    "json": {

                        "type":
                            "object",

                        "properties":
                            {},

                        "additionalProperties":
                            False,
                    }
                },
            }
        },


        {
            "toolSpec": {

                "name":
                    "evaluate_plan",

                "description":
                    (
                        "Independently validate the "
                        "rebalancing plan. Check the "
                        "50-scooter move budget, "
                        "source inventory, fleet "
                        "conservation, and whether "
                        "the plan reduces the spatial "
                        "gap between predicted demand "
                        "share and scooter supply "
                        "share."
                    ),

                "inputSchema": {

                    "json": {

                        "type":
                            "object",

                        "properties":
                            {},

                        "additionalProperties":
                            False,
                    }
                },
            }
        },
    ]
}


# ==================================================
# Agent instructions
# ==================================================

system_prompt = """
You are ScooterOps, an autonomous fleet operations agent.

Your job is to analyze the current Lime scooter fleet in Chicago
and produce a validated rebalancing recommendation.

The demand model forecasts the spatial distribution of next-hour
Lime demand across analyzed Chicago community areas using
same-season fall historical Lime trip patterns.

The operational comparison is:

predicted demand share by zone
versus
current scooter supply share by zone.

Operational numbers must come only from tools.

Required workflow:

1. Refresh the live fleet analysis.
2. Identify relatively under-supplied and over-supplied zones.
3. Run the deterministic MILP optimizer.
4. Independently evaluate the generated plan.
5. Only recommend the plan if evaluation returns APPROVED.

Do not invent:

- scooter counts
- demand shares
- supply shares
- share gaps
- movement counts
- distances
- improvement percentages
- destinations
- validation results

Distance values are Chicago community-area centroid-distance
proxies. They are not road-route distances.

The optimizer has a maximum rebalancing budget of 50 scooters.

In the final answer, be concise.

State:

- the most under-supplied zones
- the recommended scooter movements
- total scooters moved
- centroid scooter-km
- mean absolute share gap before and after
- measured spatial supply-demand imbalance improvement
- validation status
"""


# ==================================================
# Initial user request
# ==================================================

messages = [

    {
        "role":
            "user",

        "content": [

            {
                "text":
                    (
                        "Analyze the current fleet "
                        "and produce a validated "
                        "rebalancing recommendation."
                    )
            }
        ],
    }
]


# ==================================================
# Bedrock agent loop
# ==================================================

while True:

    response = client.converse(

        modelId=MODEL_ID,

        system=[
            {
                "text":
                    system_prompt
            }
        ],

        messages=messages,

        toolConfig=tool_config,

        inferenceConfig={
            "maxTokens": 1000,
            "temperature": 0,
        },
    )


    message = (
        response[
            "output"
        ][
            "message"
        ]
    )


    messages.append(
        message
    )


    if (
        response[
            "stopReason"
        ]
        != "tool_use"
    ):

        break


    tool_results = []


    for content in message[
        "content"
    ]:

        if "toolUse" not in content:

            continue


        tool_use = (
            content[
                "toolUse"
            ]
        )


        name = (
            tool_use[
                "name"
            ]
        )


        tool_use_id = (
            tool_use[
                "toolUseId"
            ]
        )


        print(
            f"\nAGENT TOOL CALL -> {name}"
        )


        try:

            if name not in TOOLS:

                raise RuntimeError(
                    (
                        "Unknown tool requested: "
                        f"{name}"
                    )
                )


            result = (
                TOOLS[
                    name
                ]()
            )


            print(
                json.dumps(
                    result,
                    indent=2,
                )
            )


            tool_result = {

                "toolUseId":
                    tool_use_id,

                "content": [

                    {
                        "json":
                            result
                    }
                ],
            }


        except Exception as exc:

            print(
                f"TOOL ERROR: {exc}"
            )


            tool_result = {

                "toolUseId":
                    tool_use_id,

                "content": [

                    {
                        "text":
                            str(exc)
                    }
                ],

                "status":
                    "error",
            }


        tool_results.append(

            {
                "toolResult":
                    tool_result
            }
        )


    messages.append(

        {
            "role":
                "user",

            "content":
                tool_results,
        }
    )


# ==================================================
# Final recommendation
# ==================================================

print(
    "\n"
    + "=" * 60
)

print(
    "SCOOTEROPS AGENT RECOMMENDATION"
)

print(
    "=" * 60
)


for content in message[
    "content"
]:

    if "text" in content:

        print(
            content[
                "text"
            ]
        )