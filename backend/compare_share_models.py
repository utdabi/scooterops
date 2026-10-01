import glob
import pandas as pd


# --------------------------------------------------
# Helper
# --------------------------------------------------

def prepare_share_data(df):
    df = df.copy()

    df["start_time"] = pd.to_datetime(df["start_time"])
    df["date"] = df["start_time"].dt.normalize()
    df["weekday"] = df["start_time"].dt.dayofweek
    df["hour"] = df["start_time"].dt.hour

    observed = (
        df.groupby(
            [
                "date",
                "weekday",
                "hour",
                "start_community_area_name",
            ]
        )
        .size()
        .reset_index(name="trips")
    )

    return observed


def build_model(df, areas):
    hourly = prepare_share_data(df)

    hourly = hourly[
        hourly["start_community_area_name"].isin(areas)
    ].copy()

    totals = (
        hourly.groupby(
            ["date", "hour"]
        )["trips"]
        .transform("sum")
    )

    hourly["share"] = hourly["trips"] / totals

    model = (
        hourly.groupby(
            [
                "start_community_area_name",
                "weekday",
                "hour",
            ]
        )["share"]
        .mean()
        .reset_index(name="predicted_share")
    )

    # normalize within weekday/hour
    model["total"] = (
        model.groupby(
            ["weekday", "hour"]
        )["predicted_share"]
        .transform("sum")
    )

    model["predicted_share"] /= model["total"]

    return model.drop(columns="total")


def evaluate(model, test):
    result = test.merge(
        model,
        on=[
            "start_community_area_name",
            "weekday",
            "hour",
        ],
        how="left",
    )

    result["predicted_share"] = (
        result["predicted_share"].fillna(0)
    )

    # normalize predictions for each actual hour
    result["prediction_total"] = (
        result.groupby(
            ["date", "hour"]
        )["predicted_share"]
        .transform("sum")
    )

    result["predicted_share"] = (
        result["predicted_share"]
        / result["prediction_total"]
    )

    result["error"] = (
        result["actual_share"]
        - result["predicted_share"]
    ).abs()

    return result["error"].mean() * 100


# --------------------------------------------------
# Load 2025 holdout
# --------------------------------------------------

test_files = glob.glob(
    r"data\seasonal\lime_fall_2025*.csv"
)

test_raw = pd.concat(
    [pd.read_csv(f) for f in test_files],
    ignore_index=True,
)

test_hourly = prepare_share_data(test_raw)


# Use same 10 areas as current seasonal model
seasonal_model = pd.read_csv(
    r"data\lime_seasonal_demand_share.csv"
)

areas = seasonal_model[
    "start_community_area_name"
].unique().tolist()

test_hourly = test_hourly[
    test_hourly["start_community_area_name"].isin(areas)
].copy()

test_hourly["hour_total"] = (
    test_hourly.groupby(
        ["date", "hour"]
    )["trips"]
    .transform("sum")
)

test_hourly["actual_share"] = (
    test_hourly["trips"]
    / test_hourly["hour_total"]
)


# --------------------------------------------------
# Model A: July 2024
# --------------------------------------------------

july = pd.read_csv(
    r"data\chicago_scooter_july2024_full.csv"
)

july = july[
    july["vendor"] == "Lime"
].copy()

july_model = build_model(
    july,
    areas,
)


# --------------------------------------------------
# Model B: Fall 2023 + 2024
# --------------------------------------------------

fall_train_files = (
    glob.glob(
        r"data\seasonal\lime_fall_2023*.csv"
    )
    +
    glob.glob(
        r"data\seasonal\lime_fall_2024*.csv"
    )
)

fall_train = pd.concat(
    [pd.read_csv(f) for f in fall_train_files],
    ignore_index=True,
)

fall_model = build_model(
    fall_train,
    areas,
)


# --------------------------------------------------
# Model C: Fall 2024 only
# --------------------------------------------------

fall_2024_files = glob.glob(
    r"data\seasonal\lime_fall_2024*.csv"
)

fall_2024 = pd.concat(
    [pd.read_csv(f) for f in fall_2024_files],
    ignore_index=True,
)

fall_2024_model = build_model(
    fall_2024,
    areas,
)


# --------------------------------------------------
# Evaluate all on same 2025 holdout
# --------------------------------------------------

july_error = evaluate(
    july_model,
    test_hourly,
)

seasonal_error = evaluate(
    fall_model,
    test_hourly,
)

fall_2024_error = evaluate(
    fall_2024_model,
    test_hourly,
)


print("\n2025 FALL HOLDOUT")
print("-----------------")

print(
    "July 2024 share model:",
    round(july_error, 2),
    "pp"
)

print(
    "Fall 2023+2024 seasonal model:",
    round(seasonal_error, 2),
    "pp"
)

print(
    "Fall 2024-only benchmark:",
    round(fall_2024_error, 2),
    "pp"
)