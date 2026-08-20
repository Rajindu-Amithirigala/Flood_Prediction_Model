import os
import time
import pandas as pd
import requests

from pathlib import Path
from tqdm import tqdm


INPUT_FILE = "../data/intermediate/dmc_index.csv"
OUTPUT_DIR = Path("data/raw/dmc_reports")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/150.0 Safari/537.36"
    )
}


def safe_filename(value: str) -> str:
    return "".join(
        char if char.isalnum() or char in "-_." else "_"
        for char in value
    )


def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    df = pd.read_csv(INPUT_FILE)

    df = df[
        df["download_url"].notna()
    ].copy()

    for _, row in tqdm(
        df.iterrows(),
        total=len(df)
    ):
        date = str(row["date"])
        time_value = str(row["time"]).replace(":", "-")
        title = safe_filename(str(row["title"]))

        filename = (
            f"{date}_{time_value}_{title}.pdf"
        )

        output_path = OUTPUT_DIR / filename

        if output_path.exists():
            continue

        try:
            response = requests.get(
                row["download_url"],
                headers=HEADERS,
                timeout=60
            )

            response.raise_for_status()

            output_path.write_bytes(
                response.content
            )

            time.sleep(1)

        except requests.RequestException as exc:
            print(
                f"Failed: {row['download_url']}\n"
                f"{exc}"
            )


if __name__ == "__main__":
    main()