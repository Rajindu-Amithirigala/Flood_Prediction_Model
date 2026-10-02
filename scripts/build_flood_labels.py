import pandas as pd


INPUT_FILE = "../data/intermediate/kelani_water_levels.csv"
OUTPUT_FILE = "../data/intermediate/flood_labels.csv"


def clean_numeric(series):
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.strip(),
        errors="coerce"
    )


def main():

    df = pd.read_csv(INPUT_FILE)

    # Basic cleanup

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    numeric_columns = [
        "water_level_prev",
        "water_level_curr",
        "alert_level",
        "minor_flood_level",
        "major_flood_level",
        "reported_rainfall_mm",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = clean_numeric(df[column])

    # Remove rows without the values needed for labeling
    df = df.dropna(
        subset=[
            "timestamp",
            "station",
            "water_level_curr",
            "minor_flood_level",
            "major_flood_level",
        ]
    )

    # Station-level flood status

    df["flood_now"] = (
        df["water_level_curr"]
        >= df["minor_flood_level"]
    ).astype(int)

    df["major_flood_now"] = (
        df["water_level_curr"]
        >= df["major_flood_level"]
    ).astype(int)


    basin_labels = (
        df.groupby("timestamp")
        .agg(
            flood_now=("flood_now", "max"),
            major_flood_now=("major_flood_now", "max"),
        )
        .reset_index()
    )

    # Save

    basin_labels = basin_labels.sort_values(
        "timestamp"
    )

    basin_labels.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("Done.")
    print(f"Rows: {len(basin_labels)}")
    print(f"Output: {OUTPUT_FILE}")

    print("\nFlood distribution:")
    print(
        basin_labels["flood_now"]
        .value_counts()
        .sort_index()
    )

    print("\nMajor flood distribution:")
    print(
        basin_labels["major_flood_now"]
        .value_counts()
        .sort_index()
    )

    print("\nTimestamp range:")
    print(
        basin_labels["timestamp"].min(),
        "to",
        basin_labels["timestamp"].max()
    )


if __name__ == "__main__":
    main()