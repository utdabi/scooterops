import pandas as pd

df = pd.read_csv(r"data\demand_by_area_hour.csv")
df["date"] = pd.to_datetime(df["date"])

top = (
    df.groupby("start_community_area_name")["trips"]
    .sum()
    .nlargest(10)
    .index
)

df = df[df["start_community_area_name"].isin(top)].copy()

previous = df[["start_community_area_name", "date", "hour", "trips"]].copy()
previous["date"] = previous["date"] + pd.Timedelta(days=7)
previous = previous.rename(columns={"trips": "naive_prediction"})

test = df[df["date"] > "2024-07-24"].merge(
    previous,
    on=["start_community_area_name", "date", "hour"],
    how="left"
)

test = test.dropna(subset=["naive_prediction"])
test["error"] = abs(test["trips"] - test["naive_prediction"])

wape = test["error"].sum() / test["trips"].sum() * 100

print("7-day naive WAPE:", round(wape, 2), "%")