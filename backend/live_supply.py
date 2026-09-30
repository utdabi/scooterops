import requests
import geopandas as gpd
import pandas as pd

LIVE_URL = "https://data.lime.bike/api/partners/v2/gbfs/chicago/free_bike_status"

payload = requests.get(LIVE_URL, timeout=30).json()
bikes = pd.DataFrame(payload["data"]["bikes"])

bikes = bikes[
    (bikes["is_reserved"] == False) &
    (bikes["is_disabled"] == False)
].copy()

scooters = gpd.GeoDataFrame(
    bikes,
    geometry=gpd.points_from_xy(bikes["lon"], bikes["lat"]),
    crs="EPSG:4326"
)

areas = gpd.read_file("data/chicago_community_areas.geojson")
areas = areas[["community", "geometry"]].to_crs("EPSG:4326")

joined = gpd.sjoin(
    scooters,
    areas,
    how="left",
    predicate="within"
)

supply = (
    joined.dropna(subset=["community"])
    .groupby("community")
    .size()
    .reset_index(name="available_scooters")
    .sort_values("available_scooters", ascending=False)
)

supply["community"] = supply["community"].str.title()

supply.to_csv("data/live_supply_by_area.csv", index=False)

print(supply.head(15).to_string(index=False))
print("\nMapped scooters:", supply["available_scooters"].sum())
print("Unmapped scooters:", joined["community"].isna().sum())