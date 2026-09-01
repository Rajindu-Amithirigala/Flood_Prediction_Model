import pdfplumber
import re
import csv
import os
import pandas as pd
from datetime import datetime


STATION_ALIASES = {
    "n' street": "Nagalagam Street",
    "nagalagam street": "Nagalagam Street",
    "hanwella": "Hanwella",
    "glencourse": "Glencourse",
    "kitulgala": "Kithulgala",
    "kithulgala": "Kithulgala",
    "holombuwa": "Holombuwa",
    "deraniyagala": "Deraniyagala",
    "norwood": "Norwood",
}


FIELDS = [
    "timestamp",
    "date",
    "time",
    "river_basin",
    "tributary",
    "station",
    "unit",
    "alert_level",
    "minor_flood_level",
    "major_flood_level",
    "water_level_prev",
    "water_level_curr",
    "remarks",
    "rising_falling",
    "reported_rainfall_mm",
    "source_file",
]


def get_date_time(page_text):
    date_m = re.search(
        r"DATE\s*:\s*([\d]{1,2}-\w{3}-\d{4})",
        page_text
    )

    time_m = re.search(
        r"TIME\s*:\s*([\d]{1,2}[:.][\d]{2}\s*[AP]M)",
        page_text
    )

    return (
        date_m.group(1) if date_m else None,
        time_m.group(1).strip() if time_m else None
    )


def parse_timestamp(date_str, time_str):
    if not date_str or not time_str:
        return None

    time_str = time_str.replace(".", ":")

    for fmt in (
        "%d-%b-%Y %I:%M %p",
        "%d-%b-%Y %I:%M%p",
    ):
        try:
            dt = datetime.strptime(
                f"{date_str} {time_str}",
                fmt
            )

            return dt.isoformat()

        except ValueError:
            continue

    return None


def clean(value):
    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


def canonical_station(raw_name):
    key = clean(raw_name).lower()

    return STATION_ALIASES.get(key)


def normalize_header(value):
    value = clean(value).lower()
    value = value.replace("\n", " ")
    value = re.sub(r"\s+", " ", value)

    return value


def build_column_map(header_rows):

    if not header_rows:
        raise ValueError(
            "No header rows found"
        )

    max_columns = max(
        len(row)
        for row in header_rows
    )

    combined_headers = []

    for column_index in range(max_columns):

        parts = []

        for row in header_rows:

            if column_index >= len(row):
                continue

            value = normalize_header(
                row[column_index]
            )

            if value:
                parts.append(value)

        combined_headers.append(
            " ".join(parts)
        )

    column_map = {}

    for i, header in enumerate(
        combined_headers
    ):

        if "river basin" in header:
            column_map["river_basin"] = i

        elif (
            "tributory" in header
            or "tributary" in header
        ):
            column_map["tributary"] = i

        elif "station" in header:
            column_map["station"] = i

        elif header.strip() == "unit":
            column_map["unit"] = i

        elif "alert level" in header:
            column_map["alert_level"] = i

        elif (
            "minor" in header
            and "flood" in header
        ):
            column_map["minor_flood_level"] = i

        elif (
            "major" in header
            and "flood" in header
        ):
            column_map["major_flood_level"] = i

        elif (
            "previous" in header
            and "level" in header
        ):
            column_map["water_level_prev"] = i

        elif (
            "current" in header
            and "level" in header
        ):
            column_map["water_level_curr"] = i

        elif "remarks" in header:
            column_map["remarks"] = i

        elif (
            "rising" in header
            or "falling" in header
        ):
            column_map["rising_falling"] = i

        elif (
            "rf" in header
            or "rainfall" in header
        ):
            column_map["rainfall"] = i

    return column_map


def get_cell(row, column_map, field):

    index = column_map.get(field)

    if index is None:
        return ""

    if index >= len(row):
        return ""

    return clean(row[index])


def parse_file(fpath):

    rows_out = []
    warnings = []

    fname = os.path.basename(fpath)

    with pdfplumber.open(fpath) as pdf:

        if len(pdf.pages) == 0:
            raise ValueError(
                "PDF has no pages"
            )

        timestamp = None
        date = None
        time = None

        for page in pdf.pages:

            page_text = (
                page.extract_text() or ""
            )

            if timestamp is None:

                page_date, page_time = (
                    get_date_time(page_text)
                )

                if page_date:
                    date = page_date

                if page_time:
                    time = page_time

                timestamp = parse_timestamp(
                    date,
                    time
                )

            tables = page.extract_tables()

            if not tables:
                continue

            for table in tables:

                if not table or len(table) < 3:
                    continue

                header_rows = table[:2]

                try:
                    column_map = (
                        build_column_map(
                            header_rows
                        )
                    )

                except ValueError:
                    continue

                required_columns = {
                    "station",
                    "unit",
                    "alert_level",
                    "minor_flood_level",
                    "major_flood_level",
                    "water_level_prev",
                    "water_level_curr",
                }

                missing_columns = (
                    required_columns
                    - set(column_map.keys())
                )

                if missing_columns:

                    warnings.append(
                        "Missing expected columns: "
                        + ", ".join(
                            sorted(
                                missing_columns
                            )
                        )
                    )

                    continue

                for row in table[2:]:

                    if not row:
                        continue

                    raw_station = get_cell(
                        row,
                        column_map,
                        "station"
                    )

                    if not raw_station:
                        continue

                    station = canonical_station(
                        raw_station
                    )

                    if station is None:
                        continue

                    rows_out.append({

                        "timestamp": timestamp,

                        "date": date,

                        "time": time,

                        "river_basin": get_cell(
                            row,
                            column_map,
                            "river_basin"
                        ),

                        "tributary": get_cell(
                            row,
                            column_map,
                            "tributary"
                        ),

                        "station": station,

                        "unit": get_cell(
                            row,
                            column_map,
                            "unit"
                        ),

                        "alert_level": get_cell(
                            row,
                            column_map,
                            "alert_level"
                        ),

                        "minor_flood_level": get_cell(
                            row,
                            column_map,
                            "minor_flood_level"
                        ),

                        "major_flood_level": get_cell(
                            row,
                            column_map,
                            "major_flood_level"
                        ),

                        "water_level_prev": get_cell(
                            row,
                            column_map,
                            "water_level_prev"
                        ),

                        "water_level_curr": get_cell(
                            row,
                            column_map,
                            "water_level_curr"
                        ),

                        "remarks": get_cell(
                            row,
                            column_map,
                            "remarks"
                        ),

                        "rising_falling": get_cell(
                            row,
                            column_map,
                            "rising_falling"
                        ),

                        "reported_rainfall_mm": get_cell(
                            row,
                            column_map,
                            "rainfall"
                        ),

                        "source_file": fname,
                    })

    if not date:
        warnings.append(
            "no date found"
        )

    if not time:
        warnings.append(
            "no time found"
        )

    if date and time and not timestamp:
        warnings.append(
            "date/time found but could not "
            f"be parsed: '{date}' '{time}'"
        )

    return rows_out, warnings


def main(
    input_dir,
    water_level_csv,
    output_csv,
    log_csv
):

    os.makedirs(
        os.path.dirname(output_csv),
        exist_ok=True
    )

    os.makedirs(
        os.path.dirname(log_csv),
        exist_ok=True
    )

    # -----------------------------------------------------
    # Load the water-level PDF inventory
    # -----------------------------------------------------

    water_level_df = pd.read_csv(
        water_level_csv
    )

    water_level_files = set(
        water_level_df["filename"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    print(
        f"Found {len(water_level_files)} "
        "PDFs in water-level CSV"
    )

    # -----------------------------------------------------
    # Find matching PDFs in the raw directory
    # -----------------------------------------------------

    pdf_files = [
        f
        for f in os.listdir(input_dir)
        if (
            f.lower().endswith(".pdf")
            and f in water_level_files
        )
    ]

    print(
        f"Found {len(pdf_files)} matching PDFs "
        f"in {input_dir}"
    )

    # -----------------------------------------------------
    # Check for inventory files that are missing
    # -----------------------------------------------------

    available_files = set(
        os.listdir(input_dir)
    )

    missing_files = (
        water_level_files
        - available_files
    )

    if missing_files:

        print(
            f"WARNING: "
            f"{len(missing_files)} files "
            "listed in CSV were not found."
        )

    # -----------------------------------------------------
    # Parse PDFs
    # -----------------------------------------------------

    all_rows = []
    log_entries = []

    ok_count = 0
    warn_count = 0
    fail_count = 0

    for i, fname in enumerate(
        pdf_files,
        1
    ):

        fpath = os.path.join(
            input_dir,
            fname
        )

        try:

            rows, warnings = parse_file(
                fpath
            )

            all_rows.extend(rows)

            if warnings:

                warn_count += 1

                for warning in warnings:

                    log_entries.append({
                        "file": fname,
                        "level": "WARNING",
                        "message": warning,
                    })

            else:

                ok_count += 1

            if not rows:

                log_entries.append({
                    "file": fname,
                    "level": "WARNING",
                    "message": (
                        "parsed successfully but "
                        "produced zero Kelani rows"
                    ),
                })

        except Exception as exc:

            fail_count += 1

            log_entries.append({
                "file": fname,
                "level": "ERROR",
                "message": (
                    f"{type(exc).__name__}: {exc}"
                ),
            })

        if i % 200 == 0:

            print(
                f"  ...{i}/{len(pdf_files)} "
                f"processed "
                f"({fail_count} failures so far)"
            )

    # -----------------------------------------------------
    # Write observations
    # -----------------------------------------------------

    with open(
        output_csv,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=FIELDS
        )

        writer.writeheader()
        writer.writerows(all_rows)

    # -----------------------------------------------------
    # Write parse log
    # -----------------------------------------------------

    with open(
        log_csv,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "file",
                "level",
                "message"
            ]
        )

        writer.writeheader()
        writer.writerows(log_entries)

    print(
        f"\nDone. "
        f"{ok_count} clean, "
        f"{warn_count} with warnings, "
        f"{fail_count} failed outright."
    )

    print(
        f"Total Kelani station rows extracted: "
        f"{len(all_rows)}"
    )

    print(
        f"Output: {output_csv}"
    )

    print(
        f"Log: {log_csv}"
    )


if __name__ == "__main__":

    main(
        "../data/raw/dmc_reports",
        "../data/intermediate/water_level_files.csv",
        "../data/intermediate/kelani_water_levels.csv",
        "../data/intermediate/parse_log.csv"
    )