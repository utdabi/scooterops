import pandas as pd

df = pd.read_csv(r"data\demand_by_area_hour.csv")
df["date"] = pd.to_datetime(df["date"])
df["weekday"] = df["date"].dt.dayofweek

top_areas = (
    df.groupby("start_community_area_name")["trips"]
    .sum()
    .nlargest(10)
    .index
)

df = df[df["start_community_area_name"].isin(top_areas)]

# Train on July 1-24
train = df[df["date"] <= "2024-07-24"]

# Test on July 25-31
test = df[df["date"] > "2024-07-24"]

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

print("MAE:", round(test["absolute_error"].mean(), 2))

test.to_csv(r"data\forecast_test.csv", index=False)
baseline.to_csv(r"data\demand_baseline.csv", index=False)

print(test.head())