import pandas as pd
import geopandas as gpd
import numpy as np

from scipy.optimize import milp, LinearConstraint, Bounds

MOVE_BUDGET = 50

df = pd.read_csv("data/rebalancing_candidates.csv")

# -----------------------------
# Split destination/source zones
# -----------------------------

destinations = df[df["need_score"] > 0].copy()
sources = df[df["need_score"] < 0].copy()

destinations["weight"] = destinations["need_score"]
sources["weight"] = -sources["need_score"]


def allocate_integer_budget(weights, budget):
    """
    Allocate an integer budget proportionally using
    the largest-remainder method.
    """
    raw = weights / weights.sum() * budget

    base = np.floor(raw).astype(int)

    remainder = budget - base.sum()

    fractions = raw - base

    if remainder > 0:
        indices = fractions.nlargest(remainder).index
        base.loc[indices] += 1

    return base


destinations["move_need"] = allocate_integer_budget(
    destinations["weight"],
    MOVE_BUDGET
)

sources["move_capacity"] = allocate_integer_budget(
    sources["weight"],
    MOVE_BUDGET
)

# -----------------------------
# Community-area centroids
# -----------------------------

areas = gpd.read_file(
    "data/chicago_community_areas.geojson"
)[["community", "geometry"]]

areas["community"] = areas["community"].str.title()

# UTM 16N, meters
areas = areas.to_crs("EPSG:26916")

areas["centroid"] = areas.geometry.centroid

centroids = dict(
    zip(
        areas["community"],
        areas["centroid"]
    )
)

# -----------------------------
# Create possible movements
# -----------------------------

pairs = []

for _, src in sources.iterrows():
    for _, dst in destinations.iterrows():

        source_name = src["community"]
        destination_name = dst["community"]

        if (
            source_name not in centroids
            or destination_name not in centroids
        ):
            continue

        distance_m = centroids[source_name].distance(
            centroids[destination_name]
        )

        pairs.append({
            "source": source_name,
            "destination": destination_name,
            "distance_km": distance_m / 1000
        })

pairs = pd.DataFrame(pairs)

# -----------------------------
# MILP
#
# Decision variable:
# x[source,destination]
# = number of scooters moved
#
# Objective:
# minimize scooter-kilometers
# -----------------------------

c = pairs["distance_km"].to_numpy()

n = len(pairs)

rows = []
targets = []

# Each source sends its assigned amount
for _, src in sources.iterrows():

    row = np.zeros(n)

    mask = pairs["source"] == src["community"]
    row[mask] = 1

    rows.append(row)
    targets.append(src["move_capacity"])

# Each destination receives its assigned amount
for _, dst in destinations.iterrows():

    row = np.zeros(n)

    mask = pairs["destination"] == dst["community"]
    row[mask] = 1

    rows.append(row)
    targets.append(dst["move_need"])

A = np.array(rows)
b = np.array(targets)

constraints = LinearConstraint(
    A,
    lb=b,
    ub=b
)

result = milp(
    c=c,
    integrality=np.ones(n),
    bounds=Bounds(
        np.zeros(n),
        np.full(n, np.inf)
    ),
    constraints=constraints
)

if not result.success:
    raise RuntimeError(result.message)

pairs["scooters"] = np.rint(result.x).astype(int)

plan = pairs[pairs["scooters"] > 0].copy()

plan["scooter_km"] = (
    plan["scooters"] *
    plan["distance_km"]
)

plan = plan.sort_values(
    "scooters",
    ascending=False
)

plan.to_csv(
    "data/rebalancing_plan.csv",
    index=False
)

# -----------------------------
# Evaluate before / after
# -----------------------------

before = df.set_index("community").copy()
after = before.copy()

for _, move in plan.iterrows():

    after.loc[
        move["source"],
        "available_scooters"
    ] -= move["scooters"]

    after.loc[
        move["destination"],
        "available_scooters"
    ] += move["scooters"]

before["pressure_after"] = (
    before["predicted_demand"]
    / before["available_scooters"]
)

after["pressure_after"] = (
    after["predicted_demand"]
    / after["available_scooters"]
)

target_pressure = (
    df["predicted_demand"].sum()
    / df["available_scooters"].sum()
)

before_gap = (
    before["pressure_after"] - target_pressure
).abs().mean()

after_gap = (
    after["pressure_after"] - target_pressure
).abs().mean()

improvement = (
    (before_gap - after_gap)
    / before_gap
    * 100
)

print("\nREBALANCING PLAN")
print("----------------")

print(
    plan[
        [
            "source",
            "destination",
            "scooters",
            "distance_km"
        ]
    ].to_string(
        index=False,
        formatters={
            "distance_km": "{:.2f}".format
        }
    )
)

print("\nTotal scooters moved:", plan["scooters"].sum())

print(
    "Total scooter-km:",
    round(plan["scooter_km"].sum(), 1)
)

print(
    "Pressure imbalance improvement:",
    round(improvement, 1),
    "%"
)