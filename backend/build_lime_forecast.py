import pandas as pd

df = pd.read_csv(r"data\chicago_scooter_july2024_full.csv")
df = df[df["vendor"] == "Lime"].copy()

df["start_time"] = pd.to_datetime(df["start_time"])
df["date"] = df["start_time"].dt.normalize()
df["hour"] = df["start_time"].dt.hour
df["weekday"] = df["start_time"].dt.dayofweek

top_areas = (
    df.groupby("start_community_area_name")
    .size()
    .nlargest(10)
    .index
)

df = df[df["start_community_area_name"].isin(top_areas)]

demand = (
    df.groupby(
        ["start_community_area_name", "date", "weekday", "hour"]
    )
    .size()
    .reset_index(name="trips")
)

train = demand[demand["date"] <= "2024-07-24"]
test = demand[demand["date"] > "2024-07-24"]

baseline = (
    train.groupby(
        ["start_community_area_name", "weekday", "hour"]
    )["trips"]
    .mean()
    .reset_index(name="predicted_trips")
)

test = test.merge(
    baseline,
    on=["start_community_area_name", "weekday", "hour"],
    how="left"
)

test["predicted_trips"] = test["predicted_trips"].fillna(0)
test["absolute_error"] = abs(test["trips"] - test["predicted_trips"])

wape = test["absolute_error"].sum() / test["trips"].sum() * 100

print("Lime rows:", len(df))
print("Lime forecast WAPE:", round(wape, 2), "%")
print("\nTop Lime areas:")
print(
    df.groupby("start_community_area_name")
    .size()
    .sort_values(ascending=False)
)

baseline.to_csv(r"data\lime_demand_baseline.csv", index=False)
test.to_csv(r"data\lime_forecast_test.csv", index=False)