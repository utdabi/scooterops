import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

supply = pd.read_csv("data/live_supply_by_area.csv")
forecast = pd.read_csv("data/demand_baseline.csv")

# Current Chicago time
now = datetime.now(ZoneInfo("America/Chicago"))
weekday = now.weekday()
hour = now.hour

# Forecast for this weekday/hour
current_forecast = forecast[
    (forecast["weekday"] == weekday) &
    (forecast["hour"] == hour)
].copy()

current_forecast = current_forecast.rename(
    columns={
        "start_community_area_name": "community",
        "predicted_trips": "predicted_hourly_trips"
    }
)

result = current_forecast.merge(
    supply,
    on="community",
    how="left"
)

result["available_scooters"] = result["available_scooters"].fillna(0)

# Demand pressure, not literal shortage
result["trips_per_available_scooter"] = (
    result["predicted_hourly_trips"] /
    result["available_scooters"].replace(0, pd.NA)
)

result = result.sort_values(
    "trips_per_available_scooter",
    ascending=False
)

result.to_csv("data/current_demand_pressure.csv", index=False)

print("Chicago time:", now.strftime("%Y-%m-%d %H:%M"))
print(result[
    [
        "community",
        "predicted_hourly_trips",
        "available_scooters",
        "trips_per_available_scooter"
    ]
].to_string(index=False))