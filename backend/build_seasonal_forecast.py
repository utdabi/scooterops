import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo


FORECAST_FILE = "data/lime_seasonal_demand_share.csv"
SUPPLY_FILE = "data/live_supply_by_area.csv"
OUTPUT_FILE = "data/lime_current_imbalance.csv"


# --------------------------------------------------
# Load seasonal demand-share forecast
# --------------------------------------------------

forecast = pd.read_csv(FORECAST_FILE)
supply = pd.read_csv(SUPPLY_FILE)

forecast = forecast.rename(
    columns={
        "start_community_area_name": "community"
    }
)


# --------------------------------------------------
# Current Chicago operating period
# --------------------------------------------------

now = datetime.now(
    ZoneInfo("America/Chicago")
)

weekday = now.weekday()
hour = now.hour

current = forecast[
    (forecast["weekday"] == weekday)
    & (forecast["hour"] == hour)
].copy()

if current.empty:
    raise RuntimeError(
        f"No seasonal forecast found for "
        f"weekday={weekday}, hour={hour}"
    )


# --------------------------------------------------
# Join live Lime supply
# --------------------------------------------------

current = current.merge(
    supply,
    on="community",
    how="left"
)

current["available_scooters"] = (
    current["available_scooters"]
    .fillna(0)
    .astype(int)
)


# --------------------------------------------------
# Normalize demand shares
#
# Defensive normalization ensures the analyzed
# zones sum exactly to 100%.
# --------------------------------------------------

demand_total = (
    current["predicted_demand_share"].sum()
)

if demand_total <= 0:
    raise RuntimeError(
        "Predicted demand shares sum to zero."
    )

current["predicted_demand_share"] = (
    current["predicted_demand_share"]
    / demand_total
)


# --------------------------------------------------
# Current supply share
# --------------------------------------------------

total_supply = (
    current["available_scooters"].sum()
)

if total_supply <= 0:
    raise RuntimeError(
        "No live scooters found in analyzed zones."
    )

current["supply_share"] = (
    current["available_scooters"]
    / total_supply
)


# --------------------------------------------------
# Spatial imbalance
#
# Positive share_gap:
# demand share > supply share
# destination candidate
#
# Negative share_gap:
# supply share > demand share
# source candidate
# --------------------------------------------------

current["share_gap"] = (
    current["predicted_demand_share"]
    - current["supply_share"]
)


# Convert the share gap into an intuitive
# fleet-equivalent quantity.
#
# Example:
# +0.05 share gap with 4,000 scooters
# = +200 scooter-equivalent gap
#
# This does NOT mean 200 scooters must be moved.
# The optimizer still has its separate move budget.
current["scooter_equivalent_gap"] = (
    current["share_gap"]
    * total_supply
)


# Keep a simple need score for downstream optimization.
#
# Positive = needs relative supply
# Negative = has relative surplus
current["need_score"] = (
    current["scooter_equivalent_gap"]
)


# --------------------------------------------------
# Human-readable percentages
# --------------------------------------------------

current["predicted_demand_share_pct"] = (
    current["predicted_demand_share"] * 100
)

current["supply_share_pct"] = (
    current["supply_share"] * 100
)

current["share_gap_pct_points"] = (
    current["share_gap"] * 100
)


# --------------------------------------------------
# Sort highest need first
# --------------------------------------------------

current = current.sort_values(
    "need_score",
    ascending=False
)


# --------------------------------------------------
# Save
# --------------------------------------------------

current.to_csv(
    OUTPUT_FILE,
    index=False
)


# --------------------------------------------------
# Console output
# --------------------------------------------------

print(
    "Chicago time:",
    now.strftime("%Y-%m-%d %H:%M")
)

print(
    "Forecast basis:",
    "Fall seasonal Lime demand share"
)

print(
    "Analyzed zones:",
    len(current)
)

print(
    "Live scooters in analyzed zones:",
    int(total_supply)
)

print()

print(
    current[
        [
            "community",
            "predicted_demand_share_pct",
            "supply_share_pct",
            "share_gap_pct_points",
            "available_scooters",
            "scooter_equivalent_gap",
        ]
    ].to_string(
        index=False,
        formatters={
            "predicted_demand_share_pct":
                "{:.2f}".format,
            "supply_share_pct":
                "{:.2f}".format,
            "share_gap_pct_points":
                "{:+.2f}".format,
            "scooter_equivalent_gap":
                "{:+.1f}".format,
        }
    )
)

print()

print(
    "Positive gap = relatively under-supplied"
)

print(
    "Negative gap = relatively over-supplied"
)