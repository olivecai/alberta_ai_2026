'''
Nov 20 2026 - Olivia Cai

Bin Alberta employment industries by AI exposure/complementarity and plot
annual average employment and annual employment shares.
'''

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "datasets" / "employment_2018_2026.csv"
OUTPUT_DIR = ROOT / "plot"

BINS = {
    # all the categories:
    # "Total" : {
    #     "total, all industries",
    # },
    "High exposure, low complementarity": {
        "professional, scientific and technical services",
        "finance and insurance",
        "information, culture and recreation", 
    },
    "High exposure, high complementarity": {
        "educational services",
        "health care and social assistance",
    },
    "Low exposure": {
        "accommodation and food services",
        "manufacturing",
        "construction",
        "transportation and warehousing",
    },
}


def normalize_name(name: str) -> str:
    return " ".join(name.strip().lower().replace("&", " and ").split())


def parse_number(value: str) -> float | None:
    value = value.strip()
    if not value or value.lower() in {"x", "f", ".."}:
        return None
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None


def load_employment(path: Path) -> tuple[list[datetime], dict[str, list[float | None]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.reader(file))

    header_row = next(
        (row for row in rows if row and row[0].startswith("North American Industry Classification System")),
        None,
    )
    if header_row is None:
        raise RuntimeError("Could not find the month header row in the CSV.")

    month_headers = header_row[1:]
    months = [datetime.strptime(month.strip(), "%B %Y") for month in month_headers]

    employment: dict[str, list[float | None]] = {}
    for row in rows:
        if not row:
            continue
        name = normalize_name(row[0])
        if name:
            employment[name] = [parse_number(value) for value in row[1 : 1 + len(months)]]

    return months, employment


def annual_average_by_bin(
    months: list[datetime],
    employment: dict[str, list[float | None]],
) -> tuple[list[int], dict[str, list[float]], list[float], dict[str, list[float]]]:
    normalized_bins = {
        label: {normalize_name(name) for name in category}
        for label, category in BINS.items()
    }

    missing = {
        industry
        for category in normalized_bins.values()
        for industry in category
        if industry not in employment
    }
    if missing:
        raise RuntimeError(f"Missing requested industries in CSV: {sorted(missing)}")

    years = sorted({month.year for month in months})
    by_year_bin: dict[str, list[float]] = {label: [] for label in BINS}
    total_employment: list[float] = []

    total_row = next(
        values for name, values in employment.items()
        if name.startswith("total, all industries")
    )

    for year in years:
        month_indexes = [index for index, month in enumerate(months) if month.year == year]

        for label, industries in normalized_bins.items():
            monthly_totals = []
            for index in month_indexes:
                values = [employment[industry][index] for industry in industries]
                available = [value for value in values if value is not None]
                if len(available) == len(values):
                    monthly_totals.append(sum(available))

            by_year_bin[label].append(
                sum(monthly_totals) / len(monthly_totals) if monthly_totals else 0.0
            )

        available_totals = [
            total_row[index] for index in month_indexes
            if total_row[index] is not None
        ]
        total_employment.append(
            sum(available_totals) / len(available_totals) if available_totals else 0.0
        )

    shares = {
        label: [
            (employment_value / total) * 100 if total else 0.0
            for employment_value, total in zip(employment_values, total_employment)
        ]
        for label, employment_values in by_year_bin.items()
    }

    return years, by_year_bin, total_employment, shares


def write_annual_csv(
    path: Path,
    years: list[int],
    by_year_bin: dict[str, list[float]],
    total_employment: list[float],
    shares: dict[str, list[float]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        header = ["Year", "Total employment (thousands)"]
        header.extend(f"{label} (thousands)" for label in BINS)
        header.extend(f"{label} share (%)" for label in BINS)
        writer.writerow(header)

        for index, year in enumerate(years):
            row = [year, round(total_employment[index], 1)]
            row.extend(round(by_year_bin[label][index], 1) for label in BINS)
            row.extend(round(shares[label][index], 2) for label in BINS)
            writer.writerow(row)


def plot_annual_employment(
    years: list[int],
    by_year_bin: dict[str, list[float]],
) -> None:
    fig, ax = plt.subplots(figsize=(11, 6.5))
    colors = {
        "High exposure, low complementarity": "#C44E52",
        "High exposure, high complementarity": "#4C72B0",
        "Low exposure": "#55A868",
        # "Total": "#8172B2",
    }

    for label, values in by_year_bin.items():
        ax.plot(years, values, marker="o", linewidth=3.0, label=label, color=colors[label])

    ax.set_title("Alberta Employment by Exposure/Complementarity Bin", fontsize=20, pad=12)
    ax.set_xlabel("Year", fontsize=18, labelpad=8)
    ax.set_ylabel("Annual average employment (thousands)", fontsize=18, labelpad=8)
    ax.set_xticks(years)
    ax.tick_params(axis="both", labelsize=12)
    ax.grid(True, axis="y", linestyle="--", alpha=0.35)
    ax.legend(loc="upper left", fontsize=15)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "employment_exposure_complementarity_annual.png", dpi=200)
    plt.close(fig)


def plot_annual_shares(
    years: list[int],
    shares: dict[str, list[float]],
) -> None:
    fig, ax = plt.subplots(figsize=(11, 6.5))
    colors = {
        "High exposure, low complementarity": "#C44E52",
        "High exposure, high complementarity": "#4C72B0",
        "Low exposure": "#55A868",
        # "Total": "#8172B2",
    }

    for label, values in shares.items():
        ax.plot(years, values, marker="o", linewidth=3.0, label=label, color=colors[label])

    ax.set_title("Employment Share of Alberta Total by Bin", fontsize=20, pad=12)
    ax.set_xlabel("Year", fontsize=18, labelpad=8)
    ax.set_ylabel("Share of total employment (%)", fontsize=18, labelpad=8)
    ax.set_xticks(years)
    ax.tick_params(axis="both", labelsize=12)
    ax.grid(True, axis="y", linestyle="--", alpha=0.35)
    ax.legend(loc="upper left", fontsize=15)

    ymin, ymax = ax.get_ylim()
    ax.set_ylim(ymin, ymax + (ymax - ymin) * 0.25)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "employment_share_exposure_complementarity_annual.png", dpi=200)
    plt.close(fig)


def main() -> None:
    months, employment = load_employment(CSV_PATH)
    years, by_year_bin, total_employment, shares = annual_average_by_bin(months, employment)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_annual_csv(
        OUTPUT_DIR / "employment_exposure_complementarity_annual.csv",
        years,
        by_year_bin,
        total_employment,
        shares,
    )
    plot_annual_employment(years, by_year_bin)
    plot_annual_shares(years, shares)

    print("Annual average employment (thousands) and share of Alberta total:")
    print("Year | Total | " + " | ".join(BINS))
    for index, year in enumerate(years):
        bin_text = " | ".join(
            f"{by_year_bin[label][index]:.1f} ({shares[label][index]:.2f}%)"
            for label in BINS
        )
        print(f"{year} | {total_employment[index]:.1f} | {bin_text}")


if __name__ == "__main__":
    main()
