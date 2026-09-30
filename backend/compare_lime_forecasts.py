import pandas as pd

df = pd.read_csv(r"data\lime_forecast_test.csv")
df["date"] = pd.to_datetime(df["date"])

full = pd.read_csv(r"data\chicago_scooter_july2024_full.csv")
full = full[full["vendor"] == "Lime"].copy()

full["start_time"] = pd.to_datetime(full["start_time"])
full["date"] = full["start_time"].dt.normalize()
full["hour"] = full["start_time"].dt.hour

top_areas = (
    full.groupby("start_community_area_name")
    .size()
    .nlargest(10)
    .index
)

full = full[full["start_community_area_name"].isin(top_areas)]

hourly = (
    full.groupby(
        ["start_community_area_name", "date", "hour"]
    )
    .size()
    .reset_index(name="trips")
)

previous = hourly.copy()
previous["date"] = previous["date"] + pd.Timedelta(days=7)
previous = previous.rename(columns={"trips": "naive_prediction"})

test = hourly[hourly["date"] > "2024-07-24"].merge(
    previous[
        ["start_community_area_name", "date", "hour", "naive_prediction"]
    ],
    on=["start_community_area_name", "date", "hour"],
    how="left"
)

test = test.dropna(subset=["naive_prediction"])

test["error"] = abs(
    test["trips"] - test["naive_prediction"]
)

wape = test["error"].sum() / test["trips"].sum() * 100

print("Lime 7-day naive WAPE:", round(wape, 2), "%")
print("Baseline WAPE: 25.18 %")