'''
Nov 20 2026 - Olivia Cai

Compare annual Alberta employment totals across three age groups.
'''

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "datasets"
OUTPUT_DIR = ROOT / "plot"

DATASETS = {
    "15–24": DATASET_DIR / "employment_alberta_oct2020_oct2026_15_24.csv",
    "24–54": DATASET_DIR / "employment_alberta_oct2020_oct2026_24_54.csv",
    "55+": DATASET_DIR / "employment_alberta_oct2020_oct2026_55_over.csv",
}


def parse_number(value: str) -> float | None:
    value = value.strip()
    if not value or value.lower() in {"x", "f", ".."}:
        return None
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None


def load_total_employment(path: Path) -> tuple[list[datetime], list[float | None]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.reader(file))

    header_row = next(
        row for row in rows
        if row and row[0].startswith("North American Industry Classification System")
    )
    months = [
        datetime.strptime(month.strip(), "%B %Y")
        for month in header_row[1:]
    ]

    total_row = next(
        row for row in rows
        if row and row[0].lower().startswith("total, all industries")
    )
    values = [parse_number(value) for value in total_row[1:1 + len(months)]]
    return months, values


def write_csv(months: list[datetime], employment: dict[str, list[float | None]]) -> None:
    path = OUTPUT_DIR / "age_group_employment_monthly.csv"
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Month", *(f"{age_group} employment (thousands)" for age_group in DATASETS)])

        for index, month in enumerate(months):
            writer.writerow([
                month.strftime("%Y-%m"),
                *[
                    "" if employment[age_group][index] is None
                    else round(employment[age_group][index], 1)
                    for age_group in DATASETS
                ],
            ])


def plot_employment(months: list[datetime], employment: dict[str, list[float | None]]) -> None:
    fig, ax = plt.subplots(figsize=(13, 6.5))
    colors = {
        "15–24": "#4C72B0",
        "24–54": "#C44E52",
        "55+": "#55A868",
    }

    for age_group, values in employment.items():
        valid = [
            (month, value)
            for month, value in zip(months, values)
            if value is not None
        ]
        ax.plot(
            [month for month, _ in valid],
            [value for _, value in valid],
            marker=".",
            markersize=3,
            linewidth=1.8,
            label=age_group,
            color=colors[age_group],
        )

    ax.set_title("Alberta Monthly Employment by Age Group", fontsize=20, pad=12)
    ax.set_xlabel("Month", fontsize=18, labelpad=8)
    ax.set_ylabel("Employment (thousands)", fontsize=18, labelpad=8)
    ax.tick_params(axis="both", labelsize=12)
    ax.grid(True, axis="both", linestyle="--", alpha=0.35)
    ax.legend(loc="best", fontsize=15)
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "age_group_employment_monthly.png", dpi=200)
    plt.close(fig)


def main() -> None:
    employment: dict[str, list[float | None]] = {}
    shared_months: list[datetime] | None = None

    for age_group, path in DATASETS.items():
        months, values = load_total_employment(path)
        if shared_months is None:
            shared_months = months
        elif months != shared_months:
            raise RuntimeError("The age-group CSV files do not cover the same months.")
        employment[age_group] = values

    if shared_months is None:
        raise RuntimeError("No employment data was loaded.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(shared_months, employment)
    plot_employment(shared_months, employment)

    print("Monthly Alberta employment by age group (thousands):")
    print("Month | " + " | ".join(DATASETS))
    for index, month in enumerate(shared_months):
        values = " | ".join(
            "N/A" if employment[age_group][index] is None
            else f"{employment[age_group][index]:.1f}"
            for age_group in DATASETS
        )
        print(f"{month.strftime('%Y-%m')} | {values}")


if __name__ == "__main__":
    main()
