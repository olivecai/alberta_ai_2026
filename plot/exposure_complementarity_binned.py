'''
Nov 20 2026 - Olivia Cai

Bin Alberta employment industries by AI exposure/complementarity and plot
monthly average employment and monthly employment shares.
'''

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "datasets" / "employment_alberta_oct2020_oct2026.csv"
OUTPUT_DIR = ROOT / "plot"

BINS = {
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


def monthly_by_bin(
    months: list[datetime],
    employment: dict[str, list[float | None]],
) -> tuple[dict[str, list[float]], list[float], dict[str, list[float]]]:
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

    by_month_bin: dict[str, list[float]] = {label: [] for label in BINS}
    total_employment: list[float] = []

    total_row = next(
        values for name, values in employment.items()
        if name.startswith("total, all industries")
    )

    for index in range(len(months)):
        for label, industries in normalized_bins.items():
            values = [employment[industry][index] for industry in industries]
            available = [value for value in values if value is not None]
            by_month_bin[label].append(
                sum(available) if len(available) == len(values) else 0.0
            )

        total = total_row[index]
        total_employment.append(total if total is not None else 0.0)

    shares = {
        label: [
            (employment_value / total) * 100 if total else 0.0
            for employment_value, total in zip(employment_values, total_employment)
        ]
        for label, employment_values in by_month_bin.items()
    }

    return by_month_bin, total_employment, shares


def write_monthly_csv(
    path: Path,
    months: list[datetime],
    by_month_bin: dict[str, list[float]],
    total_employment: list[float],
    shares: dict[str, list[float]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        header = ["Month", "Total employment (thousands)"]
        header.extend(f"{label} (thousands)" for label in BINS)
        header.extend(f"{label} share (%)" for label in BINS)
        writer.writerow(header)

        for index, month in enumerate(months):
            row = [month.strftime("%Y-%m"), round(total_employment[index], 1)]
            row.extend(round(by_month_bin[label][index], 1) for label in BINS)
            row.extend(round(shares[label][index], 2) for label in BINS)
            writer.writerow(row)


def plot_monthly_employment(
    months: list[datetime],
    by_month_bin: dict[str, list[float]],
) -> None:
    fig, ax = plt.subplots(figsize=(13, 6.5))
    colors = {
        "High exposure, low complementarity": "#C44E52",
        "High exposure, high complementarity": "#4C72B0",
        "Low exposure": "#55A868",
    }

    for label, values in by_month_bin.items():
        ax.plot(months, values, linewidth=1.8, marker=".", markersize=3, label=label, color=colors[label])

    ax.set_title("Alberta Monthly Employment by Exposure/Complementarity Bin")
    ax.set_xlabel("Month")
    ax.set_ylabel("Employment (thousands)")
    ax.grid(True, axis="both", linestyle="--", alpha=0.35)
    ax.legend(loc="best")
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "employment_exposure_complementarity_monthly.png", dpi=200)
    plt.close(fig)


def plot_monthly_shares(
    months: list[datetime],
    shares: dict[str, list[float]],
) -> None:
    fig, ax = plt.subplots(figsize=(13, 6.5))
    colors = {
        "High exposure, low complementarity": "#C44E52",
        "High exposure, high complementarity": "#4C72B0",
        "Low exposure": "#55A868",
    }

    for label, values in shares.items():
        ax.plot(months, values, linewidth=1.8, marker=".", markersize=3, label=label, color=colors[label])

    ax.set_title("Monthly Employment Share of Alberta Total by Bin")
    ax.set_xlabel("Month")
    ax.set_ylabel("Share of total employment (%)")
    ax.grid(True, axis="both", linestyle="--", alpha=0.35)
    ax.legend(loc="best")
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "employment_share_exposure_complementarity_monthly.png", dpi=200)
    plt.close(fig)


def main() -> None:
    months, employment = load_employment(CSV_PATH)
    by_month_bin, total_employment, shares = monthly_by_bin(months, employment)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_monthly_csv(
        OUTPUT_DIR / "employment_exposure_complementarity_monthly.csv",
        months,
        by_month_bin,
        total_employment,
        shares,
    )
    plot_monthly_employment(months, by_month_bin)
    plot_monthly_shares(months, shares)

    print("Monthly employment (thousands) and share of Alberta total:")
    print("Month | Total | " + " | ".join(BINS))
    for index, month in enumerate(months):
        bin_text = " | ".join(
            f"{by_month_bin[label][index]:.1f} ({shares[label][index]:.2f}%)"
            for label in BINS
        )
        print(f"{month.strftime('%Y-%m')} | {total_employment[index]:.1f} | {bin_text}")


if __name__ == "__main__":
    main()
