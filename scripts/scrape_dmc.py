import os
import time
import requests
import pandas as pd

from bs4 import BeautifulSoup
from tqdm import tqdm
from urllib.parse import urljoin


BASE_URL = "https://www.dmc.gov.lk/index.php"

PARAMS = {
    "Itemid": 277,
    "lang": "en",
    "option": "com_dmcreports",
    "report_type_id": 6,
    "view": "reports",
    "limit": 100,
}

OUTPUT_FILE = "../data/intermediate/dmc_index.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/150.0 Safari/537.36"
    )
}


def get_page(limitstart: int) -> str:
    params = PARAMS.copy()
    params["limitstart"] = limitstart

    response = requests.get(
        BASE_URL,
        params=params,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()
    return response.text


def parse_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    records = []

    # Find all table rows.
    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"])

        if len(cells) < 3:
            continue

        title = cells[0].get_text(" ", strip=True)
        date = cells[1].get_text(" ", strip=True)
        time_value = cells[2].get_text(" ", strip=True)

        download_link = None

        for anchor in row.find_all("a"):
            text = anchor.get_text(" ", strip=True).lower()

            if "download" in text:
                href = anchor.get("href")

                if href:
                    download_link = urljoin(BASE_URL, href)

        if not title or not date:
            continue

        records.append({
            "title": title,
            "date": date,
            "time": time_value,
            "download_url": download_link,
        })

    return records


def main():
    os.makedirs("data/intermediate", exist_ok=True)

    all_records = []

    for offset in tqdm(range(0, 5000, 100)):
        try:
            html = get_page(offset)
            records = parse_page(html)

            if not records:
                break

            all_records.extend(records)
            time.sleep(1)

        except requests.RequestException as exc:
            print(f"Request failed at offset {offset}: {exc}")
            break

    df = pd.DataFrame(all_records)
    if not df.empty:
        df = df.drop_duplicates(
            subset=["title", "date", "time", "download_url"]
        )

    df.to_csv(OUTPUT_FILE, index=False)

    print(f"Saved {len(df)} records to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()