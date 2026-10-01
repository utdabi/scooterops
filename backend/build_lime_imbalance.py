import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo


FORECAST_FILE = "data/lime_seasonal_demand_share.csv"
SUPPLY_FILE = "data/live_supply_by_area.csv"
OUTPUT_FILE = "data/lime_current_imbalance.csv"


# Load seasonal demand-share forecast and live supply
forecast = pd.read_csv(FORECAST_FILE)
supply = pd.read_csv(SUPPLY_FILE)

forecast = forecast.rename(
    columns={
        "start_community_area_name": "community"
    }
)


# Current Chicago time
now = datetime.now(
    ZoneInfo("America/Chicago")
)

weekday = now.weekday()
hour = now.hour


# Get forecast for current weekday/hour
current = forecast[
    (forecast["weekday"] == weekday)
    & (forecast["hour"] == hour)
].copy()

if current.empty:
    weekday_forecast = forecast[
        forecast["weekday"] == weekday
    ]

    if weekday_forecast.empty:
        raise RuntimeError(
            f"No seasonal forecast found for "
            f"weekday={weekday}; no fallback hour is available"
        )

    nearest_hour = min(
        weekday_forecast["hour"].unique(),
        key=lambda forecast_hour: (
            abs(int(forecast_hour) - hour),
            int(forecast_hour),
        ),
    )

    print(
        f"No forecast for weekday={weekday}, hour={hour}; "
        f"using nearest available hour={nearest_hour}"
    )

    current = weekday_forecast[
        weekday_forecast["hour"] == nearest_hour
    ].copy()


# Join live Lime supply
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


# Normalize demand shares
demand_total = current[
    "predicted_demand_share"
].sum()

if demand_total <= 0:
    raise RuntimeError(
        "Predicted demand shares sum to zero."
    )

current["predicted_demand_share"] = (
    current["predicted_demand_share"]
    / demand_total
)


# Current supply share
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


# Positive gap = relatively under-supplied
# Negative gap = relatively over-supplied
current["share_gap"] = (
    current["predicted_demand_share"]
    - current["supply_share"]
)


# Convert share gap into fleet-equivalent units.
# This is NOT a literal move requirement.
current["scooter_equivalent_gap"] = (
    current["share_gap"]
    * total_supply
)


# Downstream optimizer score
current["need_score"] = (
    current["scooter_equivalent_gap"]
)


# Human-readable percentages
current["predicted_demand_share_pct"] = (
    current["predicted_demand_share"] * 100
)

current["supply_share_pct"] = (
    current["supply_share"] * 100
)

current["share_gap_pct_points"] = (
    current["share_gap"] * 100
)


# Highest need first
current = current.sort_values(
    "need_score",
    ascending=False
)


# Save output
current.to_csv(
    OUTPUT_FILE,
    index=False
)


# Display
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
