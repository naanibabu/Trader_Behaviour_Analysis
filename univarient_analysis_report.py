"""Create a one-page univariate analysis PDF from a prepared DataFrame."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.image import imread
from matplotlib.ticker import FuncFormatter


BG = "#F5FEFD"
TEAL = "#97FCE4"
DARK = "#0F3933"
GREEN = "#20b958"
TEXT = "#04060C"
SENTIMENT_ORDER = ["Fear", "Neutral", "Greed"]
REPORT_DIRECTORY = Path(__file__).resolve().parent / "reports"
LOGO_PATH = Path(__file__).resolve().parent / "hyperliquid_logo.webp"
REQUIRED_COLUMNS = {
    "classification",
    "Size USD",
    "Is Profitable",
    "Is Loss",
    "Closed PnL",
    "trade_type",
}


def _money(value: float, compact: bool = False) -> str:
    if pd.isna(value):
        return "N/A"

    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000:
        precision = 1 if compact else 2
        return f"{sign}${value / 1_000_000:.{precision}f}M"
    if value >= 1_000:
        precision = 1 if compact else 2
        return f"{sign}${value / 1_000:.{precision}f}K"
    precision = 0 if compact else 2
    return f"{sign}${value:,.{precision}f}"


def _pnl_tick(value: float, _position: int) -> str:
    if value == 0:
        return "$0"
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000:
        return f"{sign}${value / 1_000_000:.0f}M"
    if value >= 1_000:
        return f"{sign}${value / 1_000:.0f}K"
    return f"{sign}${value:.0f}"


def _hide_extra_spines(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def _add_logo_watermark(fig: plt.Figure) -> None:
    if not LOGO_PATH.exists():
        return

    logo = imread(LOGO_PATH)
    target_width = max(1, int(fig.bbox.width * 0.16))
    target_height = max(1, int(target_width * logo.shape[0] / logo.shape[1]))

    from PIL import Image

    logo_image = Image.fromarray((logo * 255).astype(np.uint8))
    logo_image = logo_image.resize((target_width, target_height), Image.Resampling.LANCZOS)
    fig.figimage(
        np.asarray(logo_image),
        xo=int(fig.bbox.width * 0.82),
        yo=int(fig.bbox.height * 0.025),
        alpha=0.07,
        zorder=-1,
    )


def create_univariate_analysis_report(
    df: pd.DataFrame,
    output_directory: str | Path = REPORT_DIRECTORY,
) -> Path:
    """Create the univariate analysis PDF and return its path."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    missing_columns = REQUIRED_COLUMNS.difference(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"DataFrame is missing required columns: {missing}")
    if df.empty:
        raise ValueError("Cannot create a report from an empty DataFrame")

    data = df.copy()
    data["classification"] = data["classification"].replace(
        {"Extreme Greed": "Greed", "Extreme Fear": "Fear"}
    )
    data["trade_type"] = data["trade_type"].replace({"Perptual": "Perpetual"})

    sentiment_counts = (
        data["classification"]
        .value_counts()
        .reindex(SENTIMENT_ORDER)
        .fillna(0)
    )
    sentiment_total = sentiment_counts.sum()
    sentiment_pct = (
        sentiment_counts.div(sentiment_total).mul(100)
        if sentiment_total
        else sentiment_counts
    )

    size_usd = data["Size USD"].dropna()
    size_positive = size_usd.loc[size_usd > 0]
    size_stats = {
        "Median": size_usd.median(),
        "Mean": size_usd.mean(),
        "P95": size_usd.quantile(0.95),
        "Maximum": size_usd.max(),
    }

    profitable = int(data["Is Profitable"].fillna(False).sum())
    losses = int(data["Is Loss"].fillna(False).sum())
    realized_count = profitable + losses
    win_rate = profitable / realized_count * 100 if realized_count else np.nan

    realized_pnl = data.loc[
        data["Closed PnL"].notna() & data["Closed PnL"].ne(0),
        "Closed PnL",
    ]
    pnl_stats = {
        "Median": realized_pnl.median(),
        "Mean": realized_pnl.mean(),
        "Std": realized_pnl.std(),
        "Min": realized_pnl.min(),
        "Max": realized_pnl.max(),
    }

    trade_type_counts = (
        data["trade_type"]
        .value_counts()
        .reindex(["Spot", "Perpetual"])
        .fillna(0)
    )

    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    report_path = output_directory / "univarient_analysis_report.pdf"

    with plt.rc_context({
        "font.family": "DejaVu Sans",
        "text.color": TEXT,
        "axes.labelcolor": TEXT,
        "axes.titlecolor": TEXT,
        "xtick.color": TEXT,
        "ytick.color": TEXT,
        "figure.facecolor": BG,
        "axes.facecolor": BG,
    }):
        fig = plt.figure(figsize=(11.69, 8.27), facecolor=BG)
        _add_logo_watermark(fig)

        fig.text(
            0.5, 0.965,
            "UNIVARIATE ANALYSIS - TRADER BEHAVIOUR",
            ha="center", fontsize=18, fontweight="bold", color=TEXT,
        )
        fig.text(
            0.5, 0.935,
            "Market sentiment, trade size, outcomes, trading type and realized PnL",
            ha="center", fontsize=9, color=DARK,
        )

        ax1 = fig.add_axes([0.04, 0.57, 0.27, 0.30])
        if sentiment_total:
            ax1.pie(
                sentiment_counts,
                labels=sentiment_counts.index,
                autopct="%1.1f%%",
                startangle=140,
                colors=[TEAL, DARK, GREEN],
                textprops={"color": TEXT, "fontsize": 8.5},
                wedgeprops={"edgecolor": BG, "linewidth": 2},
            )
        else:
            ax1.text(0.5, 0.5, "No sentiment data", ha="center", va="center")
        ax1.set_title("Market Sentiment Distribution", fontsize=11, fontweight="bold", pad=8)

        ax2 = fig.add_axes([0.36, 0.57, 0.27, 0.30])
        if not size_positive.empty:
            size_min = size_positive.min()
            size_max = size_positive.max()
            if size_min == size_max:
                size_bins = np.linspace(size_min * 0.9, size_max * 1.1, 3)
            else:
                size_bins = np.geomspace(size_min, size_max, 40)
            sns.histplot(
                size_positive, bins=size_bins, ax=ax2, color=TEAL, edgecolor="white"
            )
            ax2.set_xscale("log")
            ax2.set_xticks([10, 100, 1_000, 10_000, 100_000, 1_000_000])

            def format_usd(value: float, _position: int) -> str:
                if value >= 1_000_000:
                    return f"${value / 1_000_000:.0f}M"
                if value >= 1_000:
                    return f"${value / 1_000:.0f}K"
                return f"${value:.0f}"

            ax2.xaxis.set_major_formatter(FuncFormatter(format_usd))
        else:
            ax2.text(0.5, 0.5, "No positive trade sizes", ha="center", va="center")
        ax2.set_title("Trade Size (USD) Distribution", fontsize=11, fontweight="bold")
        ax2.set_xlabel("Trade Size (USD, log scale)", fontsize=8)
        ax2.set_ylabel("Number of Trades", fontsize=8)
        ax2.tick_params(labelsize=7)
        _hide_extra_spines(ax2)

        ax3 = fig.add_axes([0.68, 0.57, 0.28, 0.30])
        outcomes = pd.Series({"Profitable": profitable, "Loss": losses})
        bars = ax3.barh(
            outcomes.index, outcomes.values, color=[TEAL, DARK], height=0.55
        )
        for bar in bars:
            width = bar.get_width()
            ax3.text(
                width + max(outcomes.max(), 1) * 0.015,
                bar.get_y() + bar.get_height() / 2,
                f"{width:,.0f}",
                va="center", fontsize=8.5, fontweight="bold",
            )
        ax3.set_title("Profitable Trades vs. Loss Trades", fontsize=11, fontweight="bold")
        ax3.set_xlabel("Number of Trades", fontsize=8)
        ax3.tick_params(axis="x", labelsize=7)
        ax3.tick_params(axis="y", labelsize=8, length=0)
        ax3.set_xlim(0, max(outcomes.max(), 1) * 1.16)
        _hide_extra_spines(ax3)
        ax3.spines["left"].set_visible(False)

        ax4 = fig.add_axes([0.04, 0.11, 0.43, 0.30])
        bars = ax4.barh(
            trade_type_counts.index,
            trade_type_counts.values,
            color=[TEAL, DARK],
            height=0.55,
        )
        for bar in bars:
            width = bar.get_width()
            ax4.text(
                width + max(trade_type_counts.max(), 1) * 0.015,
                bar.get_y() + bar.get_height() / 2,
                f"{width:,.0f}",
                va="center", fontsize=9, fontweight="bold",
            )
        ax4.set_title("Number of Trades by Trading Type", fontsize=11, fontweight="bold")
        ax4.set_xlabel("Number of Trades", fontsize=8)
        ax4.tick_params(axis="x", labelsize=7)
        ax4.tick_params(axis="y", labelsize=8, length=0)
        ax4.set_xlim(0, max(trade_type_counts.max(), 1) * 1.16)
        _hide_extra_spines(ax4)
        ax4.spines["left"].set_visible(False)

        ax5 = fig.add_axes([0.52, 0.11, 0.44, 0.30])
        if not realized_pnl.empty:
            linthresh = 10
            max_abs_pnl = realized_pnl.abs().max()
            if max_abs_pnl > linthresh:
                log_edges = np.geomspace(linthresh, max_abs_pnl, 35)
                linear_edges = np.linspace(-linthresh, linthresh, 21)
                pnl_bins = np.unique(np.concatenate([
                    -log_edges[::-1], linear_edges[1:], log_edges[1:]
                ]))
            else:
                pnl_bins = np.linspace(-linthresh, linthresh, 21)
            sns.histplot(
                realized_pnl, bins=pnl_bins, ax=ax5, color=TEAL, edgecolor="white"
            )
            ax5.set_xscale("symlog", linthresh=linthresh)
            ax5.set_xticks([
                -100_000, -10_000, -1_000, -100, -10,
                0, 10, 100, 1_000, 10_000, 100_000,
            ])
            ax5.xaxis.set_major_formatter(FuncFormatter(_pnl_tick))
            ax5.axvline(0, color=DARK, linestyle="--", linewidth=1, label="Break-even")
            ax5.legend(fontsize=7, frameon=False)
        else:
            ax5.text(0.5, 0.5, "No realized PnL", ha="center", va="center")
        ax5.set_title("Realized PnL Distribution", fontsize=11, fontweight="bold")
        ax5.set_xlabel("Realized PnL (USD, symmetric log scale)", fontsize=8)
        ax5.set_ylabel("Number of Trades", fontsize=8)
        ax5.tick_params(labelsize=7)
        _hide_extra_spines(ax5)

        fig.text(
            0.365, 0.510,
            f"Median: {_money(size_stats['Median'])}   |   "
            f"Mean: {_money(size_stats['Mean'])}   |   "
            f"P95: {_money(size_stats['P95'])}   |   "
            f"Max: {_money(size_stats['Maximum'])}",
            fontsize=7.5, color=TEXT,
        )
        fig.text(
            0.685, 0.510,
            f"Win Rate: {win_rate:.1f}%" if pd.notna(win_rate) else "Win Rate: N/A",
            fontsize=7.5, color=TEXT,
        )
        fig.text(
            0.045, 0.510,
            f"Fear: {sentiment_pct['Fear']:.1f}%   |   "
            f"Neutral: {sentiment_pct['Neutral']:.1f}%   |   "
            f"Greed: {sentiment_pct['Greed']:.1f}%",
            fontsize=7.5, color=TEXT,
        )
        fig.text(
            0.525, 0.045,
            f"Median: {_money(pnl_stats['Median'])}   |   "
            f"Mean: {_money(pnl_stats['Mean'])}   |   "
            f"Std: {_money(pnl_stats['Std'])}   |   "
            f"Min: {_money(pnl_stats['Min'], compact=True)}   |   "
            f"Max: {_money(pnl_stats['Max'], compact=True)}",
            fontsize=7.5, color=TEXT,
        )
        fig.text(
            0.5, 0.018,
            "Note: Realized PnL statistics exclude trades with Closed PnL = 0.",
            ha="center", fontsize=7, color=DARK,
        )

        try:
            with PdfPages(report_path) as pdf:
                pdf.savefig(fig, facecolor=BG, bbox_inches=None)
        finally:
            plt.close(fig)

    return report_path


if __name__ == "__main__":
    from transforme_df import df

    print(f"Created report: {create_univariate_analysis_report(df)}")