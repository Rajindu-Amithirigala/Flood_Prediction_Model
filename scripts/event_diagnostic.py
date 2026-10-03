import pandas as pd


INPUT_FILE = "../data/intermediate/flood_labels.csv"


def main():

    df = pd.read_csv(INPUT_FILE)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    floods = (
        df[df["flood_now"] == 1]
        .sort_values("timestamp")
        .copy()
    )

    floods["gap_hours"] = (
        floods["timestamp"]
        .diff()
        .dt.total_seconds()
        .div(3600)
    )

    floods["event_id"] = (
        floods["gap_hours"].isna()
        | (floods["gap_hours"] > 24)
    ).cumsum()

    events = (
        floods.groupby("event_id")
        .agg(
            start=("timestamp", "min"),
            end=("timestamp", "max"),
            observations=("timestamp", "count"),
            duration_hours=(
                "timestamp",
                lambda x: (
                    x.max() - x.min()
                ).total_seconds() / 3600
            ),
        )
        .reset_index(drop=True)
    )

    print("\nFlood episodes:")
    print(events.to_string(index=False))

    print("\nNumber of episodes:")
    print(len(events))

    print("\nObservations per episode:")
    print(
        events["observations"]
        .describe()
    )

    print("\nLongest episodes:")
    print(
        events.sort_values(
            "duration_hours",
            ascending=False
        )
        .head(10)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()