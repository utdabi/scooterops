import glob
import pandas as pd


print("Loading seasonal Lime files...", flush=True)

files = glob.glob(r"data\seasonal\lime_fall_*.csv")

if not files:
    raise FileNotFoundError(
        "No seasonal files found in data/seasonal/"
    )

df = pd.concat(
    [pd.read_csv(file) for file in files],
    ignore_index=True
)

print("Rows loaded:", len(df), flush=True)


# --------------------------------------------------
# Prepare time fields
# --------------------------------------------------

df["start_time"] = pd.to_datetime(df["start_time"])

df["year"] = df["start_time"].dt.year
df["date"] = df["start_time"].dt.normalize()
df["weekday"] = df["start_time"].dt.dayofweek
df["hour"] = df["start_time"].dt.hour


# --------------------------------------------------
# Use 10 highest-volume community areas
# --------------------------------------------------

top_areas = (
    df.groupby("start_community_area_name")
    .size()
    .nlargest(10)
    .index
    .tolist()
)

print("\nTop 10 areas:", flush=True)

for area in top_areas:
    print(" -", area, flush=True)

df = df[
    df["start_community_area_name"].isin(top_areas)
].copy()


# --------------------------------------------------
# Count observed trips by area/date/hour
# --------------------------------------------------

observed = (
    df.groupby(
        [
            "year",
            "date",
            "weekday",
            "hour",
            "start_community_area_name",
        ]
    )
    .size()
    .reset_index(name="trips")
)


# --------------------------------------------------
# Build a complete grid
#
# This is important:
# if an area had zero trips during an hour,
# it must appear as 0 rather than disappear.
# --------------------------------------------------

time_slots = (
    df[
        [
            "year",
            "date",
            "weekday",
            "hour",
        ]
    ]
    .drop_duplicates()
)

areas = pd.DataFrame(
    {
        "start_community_area_name": top_areas
    }
)

time_slots["_key"] = 1
areas["_key"] = 1

hourly = (
    time_slots
    .merge(areas, on="_key")
    .drop(columns="_key")
)

hourly = hourly.merge(
    observed,
    on=[
        "year",
        "date",
        "weekday",
        "hour",
        "start_community_area_name",
    ],
    how="left",
)

hourly["trips"] = hourly["trips"].fillna(0)

print(
    "\nComplete zone-hour rows:",
    len(hourly),
    flush=True
)


# --------------------------------------------------
# Convert absolute trips into spatial demand share
# --------------------------------------------------

hourly["hour_total"] = (
    hourly.groupby(
        [
            "year",
            "date",
            "hour",
        ]
    )["trips"]
    .transform("sum")
)

hourly = hourly[
    hourly["hour_total"] > 0
].copy()

hourly["demand_share"] = (
    hourly["trips"]
    / hourly["hour_total"]
)


# --------------------------------------------------
# Validation
#
# Train: Fall 2023 + Fall 2024
# Test:  Fall 2025
# --------------------------------------------------

train = hourly[
    hourly["year"].isin([2023, 2024])
].copy()

test = hourly[
    hourly["year"] == 2025
].copy()

print(
    "Training rows:",
    len(train),
    flush=True
)

print(
    "2025 test rows:",
    len(test),
    flush=True
)

print(
    "Validating seasonal demand shares...",
    flush=True
)


# --------------------------------------------------
# Forecast expected demand share
# by area + weekday + hour
# --------------------------------------------------

baseline = (
    train.groupby(
        [
            "start_community_area_name",
            "weekday",
            "hour",
        ]
    )["demand_share"]
    .mean()
    .reset_index(
        name="predicted_share"
    )
)

test = test.merge(
    baseline,
    on=[
        "start_community_area_name",
        "weekday",
        "hour",
    ],
    how="left",
)

test["predicted_share"] = (
    test["predicted_share"]
    .fillna(0)
)


# --------------------------------------------------
# Normalize predicted shares so every hour
# sums to 100% across analyzed zones
# --------------------------------------------------

test["predicted_share_total"] = (
    test.groupby(
        [
            "year",
            "date",
            "hour",
        ]
    )["predicted_share"]
    .transform("sum")
)

test["predicted_share"] = (
    test["predicted_share"]
    / test["predicted_share_total"]
)


# --------------------------------------------------
# Error metric
# --------------------------------------------------

test["share_error"] = (
    test["demand_share"]
    - test["predicted_share"]
).abs()

mean_absolute_share_error = (
    test["share_error"].mean() * 100
)

print(
    "\nMean absolute share error:",
    round(mean_absolute_share_error, 2),
    "percentage points",
    flush=True
)


# --------------------------------------------------
# Error by community area
# --------------------------------------------------

area_error = (
    test.groupby(
        "start_community_area_name"
    )["share_error"]
    .mean()
    .mul(100)
    .sort_values()
)

print(
    "\nMean absolute share error by area:",
    flush=True
)

print(
    area_error.round(2).to_string(),
    flush=True
)


# --------------------------------------------------
# Fit final model using all historical years
# --------------------------------------------------

final = (
    hourly.groupby(
        [
            "start_community_area_name",
            "weekday",
            "hour",
        ]
    )["demand_share"]
    .mean()
    .reset_index(
        name="predicted_demand_share"
    )
)


# Normalize final shares within each weekday/hour
final["share_total"] = (
    final.groupby(
        [
            "weekday",
            "hour",
        ]
    )["predicted_demand_share"]
    .transform("sum")
)

final["predicted_demand_share"] = (
    final["predicted_demand_share"]
    / final["share_total"]
)

final = final.drop(
    columns=["share_total"]
)


# --------------------------------------------------
# Save outputs
# --------------------------------------------------

final.to_csv(
    r"data\lime_seasonal_demand_share.csv",
    index=False
)

test.to_csv(
    r"data\seasonal_share_validation.csv",
    index=False
)

print(
    "\nSaved:",
    "data/lime_seasonal_demand_share.csv",
    flush=True
)

print(
    "Saved:",
    "data/seasonal_share_validation.csv",
    flush=True
)