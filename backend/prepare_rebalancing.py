import pandas as pd

df = pd.read_csv("data/lime_current_imbalance.csv")

# Demand pressure
df["pressure"] = (
    df["predicted_demand"] /
    df["available_scooters"].replace(0, pd.NA)
)

# Fleet-wide pressure benchmark
overall_pressure = (
    df["predicted_demand"].sum() /
    df["available_scooters"].sum()
)

# Positive need = zone is under-supplied relative to fleet average
df["need_score"] = (
    df["predicted_demand"] -
    overall_pressure * df["available_scooters"]
)

df = df.sort_values("need_score", ascending=False)

print("Overall pressure:", round(overall_pressure, 4))
print(
    df[
        [
            "community",
            "predicted_demand",
            "available_scooters",
            "pressure",
            "need_score"
        ]
    ].to_string(index=False)
)

df.to_csv("data/rebalancing_candidates.csv", index=False)