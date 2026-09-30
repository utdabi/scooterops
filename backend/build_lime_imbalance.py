import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

forecast = pd.read_csv("data/lime_demand_baseline.csv")
supply = pd.read_csv("data/live_supply_by_area.csv")

now = datetime.now(ZoneInfo("America/Chicago"))
weekday = now.weekday()
hour = now.hour

current = forecast[
    (forecast["weekday"] == weekday) &
    (forecast["hour"] == hour)
].copy()

current = current.rename(
    columns={
        "start_community_area_name": "community",
        "predicted_trips": "predicted_demand"
    }
)

current = current.merge(
    supply,
    on="community",
    how="left"
)

current["available_scooters"] = (
    current["available_scooters"].fillna(0)
)

# Allocate the existing fleet proportional to forecast demand
total_supply = current["available_scooters"].sum()
total_demand = current["predicted_demand"].sum()

current["demand_share"] = (
    current["predicted_demand"] / total_demand
)

current["target_scooters"] = (
    current["demand_share"] * total_supply
).round().astype(int)

# Positive = scooters available to move out
# Negative = scooters needed
current["imbalance"] = (
    current["available_scooters"] -
    current["target_scooters"]
)

current = current.sort_values("imbalance")

current.to_csv(
    "data/lime_current_imbalance.csv",
    index=False
)

print("Chicago time:", now.strftime("%Y-%m-%d %H:%M"))
print("Total scooters:", int(total_supply))
print("Forecast demand:", round(total_demand, 1))

print(
    current[
        [
            "community",
            "predicted_demand",
            "available_scooters",
            "target_scooters",
            "imbalance"
        ]
    ].to_string(index=False)
)