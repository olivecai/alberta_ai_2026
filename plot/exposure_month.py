'''
Bin Alberta employment industries by AI exposure/complementarity and plot
n-month rolling average employment and rolling employment shares.

Usage:
    python employment_rolling_exposure.py                 # 12-month trailing window
    python employment_rolling_exposure.py -n 6            # 6-month window
    python employment_rolling_exposure.py -n 12 --center  # centered window
    python employment_rolling_exposure.py --csv path/to/file.csv --out path/to/plot_dir

Notes:
  * The data is unadjusted for seasonality. Any window that is a multiple of 12
    removes the seasonal pattern; shorter windows will still show it.
  * Rolling share = rolling mean of bin employment / rolling mean of total employment,
    the monthly analogue of the annual share in the original script.
  * A window only gets a value when all n months are available, so the first
    (n - 1) months of a trailing window are blank.
'''

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1] if len(Path(__file__).resolve().parents) > 1 else Path.cwd()
DEFAULT_CSV = ROOT / "datasets" / "employment_2018_2026.csv"
DEFAULT_OUT = ROOT / "plot"

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

COLORS = {
    "High exposure, low complementarity": "#C44E52",
    "High exposure, high complementarity": "#4C72B0",
    "Low exposure": "#55A868",
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

    months = [datetime.strptime(month.strip(), "%B %Y") for month in header_row[1:]]

    employment: dict[str, list[float | None]] = {}
    for row in rows:
        if not row:
            continue
        name = normalize_name(row[0])
        if name:
            employment[name] = [parse_number(value) for value in row[1 : 1 + len(months)]]

    return months, employment


def rolling_mean(
    values: list[float | None],
    n: int,
    center: bool = False,
) -> list[float | None]:
    '''n-month rolling mean. None unless all n months in the window are present.
    Trailing window by default: value at month t averages months t-n+1 ... t.
    With center=True the window is centered on t (for even n it leans one month back).'''
    out: list[float | None] = [None] * len(values)
    for t in range(len(values)):
        if center:
            start = t - n // 2
            end = start + n
        else:
            start = t - n + 1
            end = t + 1
        if start < 0 or end > len(values):
            continue
        window = values[start:end]
        if any(v is None for v in window):
            continue
        out[t] = sum(window) / n
    return out


def monthly_bin_totals(
    employment: dict[str, list[float | None]],
    n_months: int,
) -> tuple[dict[str, list[float | None]], list[float | None]]:
    '''Monthly sum of the industries in each bin (None if any industry that month is missing),
    plus the monthly all-industry total.'''
    normalized = {label: {normalize_name(x) for x in names} for label, names in BINS.items()}

    missing = {i for names in normalized.values() for i in names if i not in employment}
    if missing:
        raise RuntimeError(f"Missing requested industries in CSV: {sorted(missing)}")

    bin_totals: dict[str, list[float | None]] = {}
    for label, industries in normalized.items():
        series = []
        for t in range(n_months):
            vals = [employment[i][t] for i in industries]
            series.append(None if any(v is None for v in vals) else sum(vals))
        bin_totals[label] = series

    total_row = next(v for name, v in employment.items() if name.startswith("total, all industries"))
    return bin_totals, list(total_row)


def rolling_by_bin(
    months: list[datetime],
    employment: dict[str, list[float | None]],
    n: int,
    center: bool,
) -> tuple[dict[str, list[float | None]], list[float | None], dict[str, list[float | None]]]:
    bin_totals, total = monthly_bin_totals(employment, len(months))

    # rolling_bins = {label: rolling_mean(series, n, center) for label, series in bin_totals.items()}
    # rolling_total = rolling_mean(total, n, center)

    rolling_bins = bin_totals
    rolling_total = total

    shares = {
        label: [
            (b / t) * 100 if (b is not None and t) else None
            for b, t in zip(series, rolling_total)
        ]
        for label, series in rolling_bins.items()
    }
    return rolling_bins, rolling_total, shares


def write_csv(
    path: Path,
    months: list[datetime],
    n: int,
    rolling_bins: dict[str, list[float | None]],
    rolling_total: list[float | None],
    shares: dict[str, list[float | None]],
) -> None:
    def fmt(v: float | None, digits: int) -> str | float:
        return "" if v is None else round(v, digits)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        header = ["Month", f"Total employment, {n}-mo avg (thousands)"]
        header.extend(f"{label}, {n}-mo avg (thousands)" for label in BINS)
        header.extend(f"{label} share (%)" for label in BINS)
        writer.writerow(header)
        for t, month in enumerate(months):
            row = [month.strftime("%Y-%m"), fmt(rolling_total[t], 1)]
            row.extend(fmt(rolling_bins[label][t], 1) for label in BINS)
            row.extend(fmt(shares[label][t], 2) for label in BINS)
            writer.writerow(row)


def _style_time_axis(ax, months: list[datetime]) -> None:
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=(4, 7, 10)))
    ax.set_xlim(months[0], months[-1])
    ax.tick_params(axis="both", labelsize=12)
    ax.grid(True, axis="y", linestyle="--", alpha=0.35)


def _plot_lines(ax, months, series_by_label) -> None:
    for label, values in series_by_label.items():
        ax.plot(months, [float("nan") if v is None else v for v in values],
                linewidth=3.0, label=label, color=COLORS[label])


def window_label(n: int, center: bool) -> str:
    return f"{n}-month {'centered' if center else 'trailing'} rolling average"


def plot_employment(months, rolling_bins, n: int, center: bool, out_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(11, 6.5))
    _plot_lines(ax, months, rolling_bins)
    ax.set_title(f"Alberta Employment by Exposure/Complementarity Bin\n({window_label(n, center)})",
                 fontsize=18, pad=12)
    ax.set_xlabel("Month", fontsize=16, labelpad=8)
    ax.set_ylabel("Employment (thousands)", fontsize=16, labelpad=8)
    _style_time_axis(ax, months)
    ax.legend(loc="upper left", fontsize=13)
    fig.tight_layout()
    path = out_dir / f"employment_exposure_complementarity_rolling{n}.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def plot_shares(months, shares, n: int, center: bool, out_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(11, 6.5))
    _plot_lines(ax, months, shares)
    ax.set_title(f"Employment Share of Alberta Total by Bin\n({window_label(n, center)})",
                 fontsize=18, pad=12)
    ax.set_xlabel("Month", fontsize=16, labelpad=8)
    ax.set_ylabel("Share of total employment (%)", fontsize=16, labelpad=8)
    _style_time_axis(ax, months)
    ymin, ymax = ax.get_ylim()
    ax.set_ylim(ymin, ymax + (ymax - ymin) * 0.25)   # headroom for the legend
    ax.legend(loc="upper left", fontsize=13)
    fig.tight_layout()
    path = out_dir / f"employment_share_exposure_complementarity_rolling{n}.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-n", "--months", type=int, default=12, help="rolling window length in months (default 12)")
    parser.add_argument("--center", action="store_true", help="use a centered window instead of a trailing one")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Statistics Canada 14-10-0022-01 CSV")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output directory")
    args = parser.parse_args()
    if args.months < 1:
        parser.error("--months must be at least 1")

    months, employment = load_employment(args.csv)
    if args.months > len(months):
        parser.error(f"--months ({args.months}) is longer than the data ({len(months)} months)")

    rolling_bins, rolling_total, shares = rolling_by_bin(months, employment, args.months, args.center)

    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / f"employment_exposure_complementarity_rolling{args.months}.csv",
              months, args.months, rolling_bins, rolling_total, shares)
    p1 = plot_employment(months, rolling_bins, args.months, args.center, args.out)
    p2 = plot_shares(months, shares, args.months, args.center, args.out)

    print(f"{window_label(args.months, args.center)}; wrote:\n  {p1}\n  {p2}")
    last = max(t for t in range(len(months)) if rolling_total[t] is not None)
    print(f"Latest window ending {months[last]:%b %Y}: total {rolling_total[last]:.1f}k")
    for label in BINS:
        print(f"  {label}: {rolling_bins[label][last]:.1f}k ({shares[label][last]:.2f}%)")


if __name__ == "__main__":
    main()