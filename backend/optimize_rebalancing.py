import pandas as pd
import geopandas as gpd
import numpy as np

from scipy.optimize import milp, LinearConstraint, Bounds


MOVE_BUDGET = 50

INPUT_FILE = "data/rebalancing_candidates.csv"
OUTPUT_FILE = "data/rebalancing_plan.csv"


df = pd.read_csv(INPUT_FILE)


# --------------------------------------------------
# Source / destination zones
# --------------------------------------------------

destinations = df[df["need_score"] > 0].copy()
sources = df[df["need_score"] < 0].copy()

destinations["weight"] = destinations["need_score"]
sources["weight"] = -sources["need_score"]


def allocate_integer_budget(weights, budget):
    raw = weights / weights.sum() * budget

    base = np.floor(raw).astype(int)

    remainder = budget - base.sum()

    fractions = raw - base

    if remainder > 0:
        indices = fractions.nlargest(remainder).index
        base.loc[indices] += 1

    return base


# Allocate the 50-scooter move budget according to
# relative under-supply / over-supply magnitude.

destinations["move_need"] = allocate_integer_budget(
    destinations["weight"],
    MOVE_BUDGET,
)

sources["move_capacity"] = allocate_integer_budget(
    sources["weight"],
    MOVE_BUDGET,
)


# --------------------------------------------------
# Chicago community-area centroids
# --------------------------------------------------

areas = gpd.read_file(
    "data/chicago_community_areas.geojson"
)[["community", "geometry"]]

areas["community"] = areas["community"].str.title()

# Chicago UTM, meters
areas = areas.to_crs("EPSG:26916")

areas["centroid"] = areas.geometry.centroid

centroids = dict(
    zip(
        areas["community"],
        areas["centroid"],
    )
)


# --------------------------------------------------
# Candidate movements
# --------------------------------------------------

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

        pairs.append(
            {
                "source": source_name,
                "destination": destination_name,
                "distance_km": distance_m / 1000,
            }
        )


pairs = pd.DataFrame(pairs)

if pairs.empty:
    raise RuntimeError(
        "No valid source-destination pairs were created."
    )


# --------------------------------------------------
# MILP
#
# x[source, destination]
# = scooters moved
#
# Objective:
# minimize centroid-distance movement
# --------------------------------------------------

c = pairs["distance_km"].to_numpy()

n = len(pairs)

rows = []
targets = []


# Every source sends its allocated amount
for _, src in sources.iterrows():

    row = np.zeros(n)

    mask = (
        pairs["source"]
        == src["community"]
    )

    row[mask] = 1

    rows.append(row)

    targets.append(
        src["move_capacity"]
    )


# Every destination receives its allocated amount
for _, dst in destinations.iterrows():

    row = np.zeros(n)

    mask = (
        pairs["destination"]
        == dst["community"]
    )

    row[mask] = 1

    rows.append(row)

    targets.append(
        dst["move_need"]
    )


A = np.array(rows)
b = np.array(targets)

constraints = LinearConstraint(
    A,
    lb=b,
    ub=b,
)


result = milp(
    c=c,
    integrality=np.ones(n),
    bounds=Bounds(
        np.zeros(n),
        np.full(n, np.inf),
    ),
    constraints=constraints,
)


if not result.success:
    raise RuntimeError(
        result.message
    )


pairs["scooters"] = (
    np.rint(result.x)
    .astype(int)
)

plan = pairs[
    pairs["scooters"] > 0
].copy()

plan["scooter_km"] = (
    plan["scooters"]
    * plan["distance_km"]
)

plan = plan.sort_values(
    "scooters",
    ascending=False,
)

plan.to_csv(
    OUTPUT_FILE,
    index=False,
)


# --------------------------------------------------
# Evaluate before / after spatial imbalance
#
# Demand share remains fixed.
# Scooter movements change supply share.
#
# Metric:
# mean absolute percentage-point gap between
# predicted demand share and supply share.
# --------------------------------------------------

before = (
    df.set_index("community")
    .copy()
)

after = before.copy()


for _, move in plan.iterrows():

    source = move["source"]
    destination = move["destination"]
    scooters = int(move["scooters"])

    after.loc[
        source,
        "available_scooters"
    ] -= scooters

    after.loc[
        destination,
        "available_scooters"
    ] += scooters


if (
    after["available_scooters"] < 0
).any():
    raise RuntimeError(
        "Optimizer produced negative supply."
    )


total_supply_before = (
    before["available_scooters"].sum()
)

total_supply_after = (
    after["available_scooters"].sum()
)


if total_supply_before != total_supply_after:
    raise RuntimeError(
        "Total fleet supply changed during rebalancing."
    )


before["evaluated_supply_share"] = (
    before["available_scooters"]
    / total_supply_before
)

after["evaluated_supply_share"] = (
    after["available_scooters"]
    / total_supply_after
)


before["evaluated_gap"] = (
    before["predicted_demand_share"]
    - before["evaluated_supply_share"]
)

after["evaluated_gap"] = (
    after["predicted_demand_share"]
    - after["evaluated_supply_share"]
)


before_gap_pp = (
    before["evaluated_gap"]
    .abs()
    .mean()
    * 100
)

after_gap_pp = (
    after["evaluated_gap"]
    .abs()
    .mean()
    * 100
)


if before_gap_pp > 0:

    improvement = (
        (before_gap_pp - after_gap_pp)
        / before_gap_pp
        * 100
    )

else:

    improvement = 0.0


# --------------------------------------------------
# Output
# --------------------------------------------------

print("\nREBALANCING PLAN")
print("----------------")

print(
    plan[
        [
            "source",
            "destination",
            "scooters",
            "distance_km",
        ]
    ].to_string(
        index=False,
        formatters={
            "distance_km": "{:.2f}".format
        },
    )
)


print(
    "\nTotal scooters moved:",
    int(plan["scooters"].sum()),
)

print(
    "Total centroid scooter-km:",
    round(
        plan["scooter_km"].sum(),
        1,
    ),
)

print(
    "Mean absolute share gap before:",
    round(before_gap_pp, 2),
    "pp",
)

print(
    "Mean absolute share gap after:",
    round(after_gap_pp, 2),
    "pp",
)

print(
    "Spatial imbalance improvement:",
    round(improvement, 1),
    "%",
)