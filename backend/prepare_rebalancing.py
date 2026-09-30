import pandas as pd


INPUT_FILE = "data/lime_current_imbalance.csv"
OUTPUT_FILE = "data/rebalancing_candidates.csv"


df = pd.read_csv(INPUT_FILE)


required_columns = [
    "community",
    "predicted_demand_share",
    "supply_share",
    "share_gap",
    "available_scooters",
    "scooter_equivalent_gap",
    "need_score",
]

missing = [
    column
    for column in required_columns
    if column not in df.columns
]

if missing:
    raise RuntimeError(
        f"Missing required columns: {missing}"
    )


# Positive need_score = destination candidate
# Negative need_score = source candidate

df = df.sort_values(
    "need_score",
    ascending=False
)


destinations = df[
    df["need_score"] > 0
].copy()

sources = df[
    df["need_score"] < 0
].copy()


df.to_csv(
    OUTPUT_FILE,
    index=False
)


print("REBALANCING CANDIDATES")
print("----------------------")

print("\nDestination candidates:")

print(
    destinations[
        [
            "community",
            "predicted_demand_share_pct",
            "supply_share_pct",
            "share_gap_pct_points",
            "need_score",
        ]
    ].to_string(
        index=False,
        formatters={
            "predicted_demand_share_pct": "{:.2f}".format,
            "supply_share_pct": "{:.2f}".format,
            "share_gap_pct_points": "{:+.2f}".format,
            "need_score": "{:+.1f}".format,
        }
    )
)

print("\nSource candidates:")

print(
    sources[
        [
            "community",
            "predicted_demand_share_pct",
            "supply_share_pct",
            "share_gap_pct_points",
            "need_score",
        ]
    ].to_string(
        index=False,
        formatters={
            "predicted_demand_share_pct": "{:.2f}".format,
            "supply_share_pct": "{:.2f}".format,
            "share_gap_pct_points": "{:+.2f}".format,
            "need_score": "{:+.1f}".format,
        }
    )
)

print(
    "\nPositive need_score = relatively under-supplied"
)

print(
    "Negative need_score = relatively over-supplied"
)